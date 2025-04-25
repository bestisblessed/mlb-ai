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
    # Connect to Gmail
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_address, email_password)
    mail.select("inbox")
    
    # Search for emails from DubClub
    status, messages = mail.search(None, '(FROM "info@dubclub.win" SUBJECT "DubClub Email Verification")')
    
    if status != 'OK' or not messages[0]:
        print("No verification email found")
        return None
    
    # Get the latest email
    latest_email_id = messages[0].split()[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    if status != 'OK':
        print("Failed to fetch email")
        return None
    
    # Parse the email
    msg = email.message_from_bytes(msg_data[0][1])
    
    # Get the body
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
    
    # Extract the verification code using regex
    match = re.search(r'Your one-time security code is (\d+)', body)
    if match:
        verification_code = match.group(1)
        print(f"🔑 Found verification code: {verification_code}")
        return verification_code
    
    print("⚠️ Could not find verification code in email")
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
            
            # Wait for any navigation to complete
            print("Waiting for navigation after clicking continue...")
            await page.wait_for_load_state("networkidle")
            
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
                    
                    # Wait for the specific OTP input field to be visible
                    await page.wait_for_selector("input.invisible-input.svelte-1r6x64s", timeout=10000)
                    
                    # Get the OTP input field
                    otp_input = page.locator("input.invisible-input.svelte-1r6x64s")
                    
                    # Type the verification code
                    print(f"Typing verification code into input field...")
                    await otp_input.type(verification_code, delay=100)
                    
                    # Wait a moment for any validations
                    await page.wait_for_timeout(1000)
                    
                    # Click the verify button
                    print("Looking for verify button...")
                    verify_button = page.get_by_role("button", name="Verify Email")
                    
                    if await verify_button.count() > 0:
                        print("Clicking 'Verify Email' button...")
                        await verify_button.click()
                        await page.wait_for_load_state("networkidle")
                        print("✅ Logged in successfully!")
                    else:
                        print("Could not find verify button")
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
