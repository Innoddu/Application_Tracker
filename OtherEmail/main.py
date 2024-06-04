import imaplib, os, email, json, pickle
from email.header import decode_header
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from auth import USERNAME, creds, oauth2_login

# Connect to the IMAP server
mail = oauth2_login(USERNAME, creds)
mail.select("inbox")

# Search for all emails
status, messages = mail.search(None, "ALL")
email_ids = messages[0].split()

# Process the first 10 emails
for email_id in email_ids[:10]:
    # Fetch the email data
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    # Decode the email subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")

    # Decode and format the email date
    date_str, encoding = decode_header(msg["Date"])[0]
    if isinstance(date_str, bytes):
        date_str = date_str.decode(encoding if encoding else "utf-8")
    
    # Remove unnecessary parts such as " (UTC)"
    date_str = date_str.split(' (')[0]

    # Parse and format the date
    try:
        temp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        formatted_date = temp.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        print(f"Error parsing date: {date_str} -> {e}")
        formatted_date = "Unknown"

    # Get the email sender
    from_ = msg.get("From")

    # Extract the email body
    body = None
    content_type = msg.get_content_type()
    if content_type == "text/plain":
        try:
            body = msg.get_payload(decode=True).decode()
        except Exception as e:
            print(f"Error decoding body: {e}")
            body = "Error decoding body"

        print(f"Body: {body}")
        print("="*100)

    # Print the email details
    print(f"Subject: {subject}")
    print(f"Date: {formatted_date}")
    print(f"From: {from_}")

# Logout from the IMAP server
mail.logout()