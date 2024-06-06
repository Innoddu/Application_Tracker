import email, csv
from email.header import decode_header
from datetime import datetime
from auth import USERNAME, creds, oauth2_login

def decode_payload(payload):
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return payload.decode('latin-1')
        except UnicodeDecodeError:
            return None

def connect_to_mailbox(username, creds):
    print("Connecting to mailbox...")
    mail = oauth2_login(username, creds)
    mail.select("inbox")
    return mail

def search_emails(mail, start_date, end_date):
    print(f"Searching emails from {start_date} to {end_date}...")
    status, messages = mail.search(None, f'SINCE {start_date} BEFORE {end_date}')
    if status != "OK":
        print("Failed to search emails")
        return []
    return messages[0].split()

def fetch_email(mail, email_id):
    print(f"Fetching email with ID: {email_id}...")
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    if status != "OK":
        print(f"Failed to fetch email with ID: {email_id}")
        return None
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            return email.message_from_bytes(response_part[1])
    return None

def decode_email_subject(subject):
    subject, encoding = decode_header(subject)[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")
    return subject

def decode_email_date(date_str):
    date_str, encoding = decode_header(date_str)[0]
    if isinstance(date_str, bytes):
        date_str = date_str.decode(encoding if encoding else "utf-8")
    date_str = date_str.split(' (')[0]
    try:
        temp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return temp.strftime('%m-%d, %Y')
    except ValueError as e:
        print(f"Error parsing date: {date_str} -> {e}")
        return "Unknown"

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type in ["text/plain", "text/html"] and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    decoded_payload = decode_payload(payload)
                    if decoded_payload:
                        body += decoded_payload
    else:
        content_type = msg.get_content_type()
        if content_type in ["text/plain", "text/html"]:
            payload = msg.get_payload(decode=True)
            if payload:
                decoded_payload = decode_payload(payload)
                if decoded_payload:
                    body = decoded_payload
    return body

def process_emails(mail, email_ids, writer):
    for i, email_id in enumerate(email_ids):
        msg = fetch_email(mail, email_id)
        if msg is None:
            continue
        
        subject = decode_email_subject(msg["Subject"])
        formatted_date = decode_email_date(msg["Date"])
        from_ = msg.get("From")
        body = extract_body(msg)
        keywords = any(keyword in body.lower() for keyword in ["application", "resume", "cv", "job", "position", "apply"]) if body else False
        length = len(body) if body else 0
        domain = from_.split('@')[-1]

        # Print the email details
        print(f"Subject: {subject}")
        print(f"Date: {formatted_date}")
        print(f"From: {from_}")
        print(f"Body Length: {length}")
        print("="*100)
        writer.writerow([i+1, formatted_date, from_, subject, body, domain, keywords, length])

def check_emails():
    f = open('berkeleyEmail.csv', 'w', newline='')
    write = csv.writer(f)
    write.writerow(['#', 'Date', 'From', 'Title', 'Body', 'Domain', 'Keywords', 'Length'])

    try:
        mail = connect_to_mailbox(USERNAME, creds)

        start_date = datetime(2023, 1, 1).strftime('%d-%b-%Y')
        end_date = datetime.now().strftime('%d-%b-%Y')

        email_ids = search_emails(mail, start_date, end_date)
        process_emails(mail, email_ids, write)

        mail.logout()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        f.close()

check_emails()
