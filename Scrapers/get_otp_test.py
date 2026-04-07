import imaplib
import email
import re
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from .env
email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_PASSWORD")

def get_verification_code():
    print(f"Connecting to Gmail using {email_address}...")
    
    # Connect to Gmail
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_address, email_password)
    mail.select("inbox")
    
    print("Connected to inbox. Searching for verification emails...")
    
    # Search for emails from DubClub
    status, messages = mail.search(None, '(FROM "info@dubclub.win" SUBJECT "DubClub Email Verification")')
    
    if status != 'OK':
        print("Search failed with status:", status)
        return None
        
    if not messages[0]:
        print("No matching messages found")
        return None
    
    email_ids = messages[0].split()
    print(f"Found {len(email_ids)} matching messages")
    
    # Get the latest email
    latest_email_id = email_ids[-1]
    print(f"Getting latest email (ID: {latest_email_id.decode() if isinstance(latest_email_id, bytes) else latest_email_id})")
    
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    if status != 'OK':
        print("Failed to fetch email with status:", status)
        return None
    
    # Parse the email
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"Email received: {msg['Subject']} from {msg['From']} at {msg['Date']}")
    
    # Get the body
    body = ""
    if msg.is_multipart():
        print("Parsing multipart email...")
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
                
            if content_type == "text/plain" or content_type == "text/html":
                try:
                    body_part = part.get_payload(decode=True).decode()
                    print(f"Found {content_type} part, length: {len(body_part)} chars")
                    body += body_part
                except Exception as e:
                    print(f"Error decoding part: {str(e)}")
    else:
        try:
            body = msg.get_payload(decode=True).decode()
            print(f"Email body length: {len(body)} chars")
        except Exception as e:
            print(f"Error decoding email body: {str(e)}")
    
    # Extract the verification code using regex
    match = re.search(r'Your one-time security code is (\d+)', body)
    if match:
        verification_code = match.group(1)
        print(f"🔑 Found verification code: {verification_code}")
        return verification_code
    else:
        # If code not found, print part of the body for debugging
        print("⚠️ Could not find verification code in email")
        preview = body[:500] + ("..." if len(body) > 500 else "")
        print(f"Email preview: {preview}")
        return None

if __name__ == "__main__":
    print("OTP Email Retrieval Test")
    print("=" * 50)
    
    try:
        # Check if credentials are available
        if not email_address or not email_password:
            print("❌ Email credentials not found in .env file")
            print("Please create a .env file with EMAIL_ADDRESS and EMAIL_PASSWORD")
            exit(1)
            
        print(f"Using email: {email_address}")
        print("Checking for verification code...")
        
        code = get_verification_code()
        
        if code:
            print("\n✅ Success! Found verification code:", code)
        else:
            print("\n❌ Failed to find verification code")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}") 