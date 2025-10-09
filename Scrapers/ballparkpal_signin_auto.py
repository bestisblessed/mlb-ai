from playwright.async_api import async_playwright
import asyncio
import os
import re
import time
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

os.makedirs("data", exist_ok=True)
user_data_dir = "playwright_user_data"

# Get credentials from .env
email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")

async def get_verification_code():
    try:
        print(f"Connecting to Gmail for {email_address}...")
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, email_password)
        mail.select("inbox")
        
        # Search for emails from DubClub (try multiple patterns)
        search_patterns = [
            '(FROM "info@dubclub.win" SUBJECT "DubClub Email Verification")',
            '(FROM "info@dubclub.win")',
            '(SUBJECT "verification")',
            '(SUBJECT "security code")'
        ]
        
        verification_code = None
        for pattern in search_patterns:
            print(f"Searching with pattern: {pattern}")
            status, messages = mail.search(None, pattern)
            
            if status == 'OK' and messages[0]:
                print(f"Found {len(messages[0].split())} emails matching pattern")
                
                # Get the latest email
                latest_email_id = messages[0].split()[-1]
                status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                
                if status == 'OK':
                    # Parse the email
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Get the body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain" or content_type == "text/html":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    continue
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    print(f"Email body preview: {body[:200]}...")
                    
                    # Try multiple regex patterns for verification code
                    patterns = [
                        r'Your one-time security code is (\d+)',
                        r'verification code is (\d+)',
                        r'security code is (\d+)',
                        r'code: (\d+)',
                        r'(\d{6})',  # Any 6-digit number
                        r'(\d{4,8})'  # Any 4-8 digit number
                    ]
                    
                    for regex_pattern in patterns:
                        match = re.search(regex_pattern, body, re.IGNORECASE)
                        if match:
                            verification_code = match.group(1)
                            print(f"🔑 Found verification code: {verification_code}")
                            break
                    
                    if verification_code:
                        break
        
        mail.close()
        mail.logout()
        
        if not verification_code:
            print("⚠️ Could not find verification code in any emails")
            
        return verification_code
        
    except Exception as e:
        print(f"❌ Error retrieving verification code: {e}")
        return None

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False
        )
        page = await context.new_page()
        
        # Go to main page and click on Log In
        print("Navigating to BallparkPal...")
        await page.goto('https://www.ballparkpal.com/Game-Simulations.php')
        await page.wait_for_timeout(1000)
        
        # Check if we need to login
        if await page.get_by_text("Log In").count() > 0:
            print("Login required. Clicking 'Log In' button...")
            await page.get_by_text("Log In").click()
            
            # Wait for login form and enter email
            print(f"Entering email address: {email_address}")
            await page.wait_for_selector('input[placeholder="Your email..."]')
            await page.fill('input[placeholder="Your email..."]', email_address)
            
            # Click the Continue with Email button
            print("Clicking 'Continue with Email' button...")
            await page.get_by_text("Continue with Email").click()
            
            # Wait for navigation with timeout and fallback
            print("Waiting for navigation after clicking continue...")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"Network idle timeout, continuing anyway: {e}")
                await page.wait_for_timeout(3000)  # Fallback wait
            
            # Critical change - explicitly wait and check HTML content for OTP input
            print("Waiting 5 seconds to check page content...")
            await page.wait_for_timeout(5000)
            
            # Get the page HTML and check for OTP indicators
            html_content = await page.content()
            if "verification" in html_content.lower() or "security code" in html_content.lower():
                print("Verification page detected. Waiting 30 seconds for email to arrive...")
                time.sleep(40)
                
                print("Checking email for verification code...")
                verification_code = await get_verification_code()
                
                if verification_code:
                    print(f"Entering verification code: {verification_code}")
                    
                    # Try multiple selectors for OTP input field
                    otp_selectors = [
                        "input.invisible-input.svelte-1r6x64s",
                        "input[type='text']",
                        "input[placeholder*='code']",
                        "input[placeholder*='digit']",
                        ".otp-input",
                        "[data-testid='otp-input']"
                    ]
                    
                    otp_input = None
                    for selector in otp_selectors:
                        try:
                            await page.wait_for_selector(selector, timeout=3000)
                            otp_input = page.locator(selector)
                            print(f"Found OTP input with selector: {selector}")
                            break
                        except:
                            continue
                    
                    if otp_input:
                        # Clear any existing text and type the verification code
                        print(f"Typing verification code into input field...")
                        await otp_input.clear()
                        await otp_input.type(verification_code, delay=100)
                        
                        # Wait a moment for any validations
                        await page.wait_for_timeout(2000)
                        
                        # Try multiple ways to find and click the verify button
                        verify_selectors = [
                            'button:has-text("Verify Email")',
                            'button:has-text("Verify")',
                            '[type="submit"]',
                            '.verify-button',
                            '[data-testid="verify-button"]'
                        ]
                        
                        verify_button = None
                        for selector in verify_selectors:
                            try:
                                verify_button = page.locator(selector)
                                if await verify_button.count() > 0:
                                    print(f"Found verify button with selector: {selector}")
                                    break
                            except:
                                continue
                        
                        if verify_button and await verify_button.count() > 0:
                            print("Clicking verify button...")
                            await verify_button.click()
                            
                            # Wait for navigation with timeout
                            try:
                                await page.wait_for_load_state("networkidle", timeout=15000)
                                print("✅ Logged in successfully!")
                            except Exception as e:
                                print(f"Navigation timeout, but verification may have succeeded: {e}")
                                # Check if we're still on verification page
                                current_url = page.url
                                if "verify" not in current_url.lower():
                                    print("✅ Successfully navigated away from verification page!")
                                else:
                                    print("Still on verification page, may need manual intervention")
                        else:
                            print("Could not find verify button")
                    else:
                        print("Could not find OTP input field")
                else:
                    print("❌ Couldn't retrieve verification code")
            else:
                print("No verification code required - page did not show verification form")
        else:
            print("Already logged in")
            
        # Continue with scraping or other actions
        print("Ready to proceed with scraping")
        
        # Ensure the browser stays open for inspection
        print("Press Enter to close the browser...")
        await asyncio.to_thread(input)
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
