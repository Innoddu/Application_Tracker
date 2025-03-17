import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime
import json
from auth import USERNAME, creds, oauth2_login 

keywords_apply = [
        "carefully review", 'thank you for submitting your resume', 
        'thanks for completing your application','thank you for your interest', 
        'thank you from', 'application received', 'thank you for your application', 
        'application submitted to', 'thank you for applying', 'thanks for applying', 
        'thank you for applying with', 'submitting your application', 
        'reviewing your resume', 'received your application'
    ]
keywords_reject = [
    'regret to inform', 'moving forward with other candidates', 
    "not consider you", 'will not be moving forward', 'not consider you',
    'decided not to move forward', 'regret to inform you', 
    'other candidates', 'unable to move you  forward'
    ]



def connect_to_email():
    mail = oauth2_login(USERNAME, creds)
    mail.select("inbox")
    return mail

def search_all_emails(mail):
    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()
    return email_ids

def auto_label(email_text):
    text = email_text.lower()
    if any(keyword in text for keyword in keywords_apply):
        return 'apply'
    elif any(keyword in text for keyword in keywords_reject):
        return 'reject'
    return 'other'

def fetch_email(mail, email_id):
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    return email.message_from_bytes(msg_data[0][1])

def decode_email_header(header_value):
    value, encoding = email.header.decode_header(header_value=header_value)[0]
    if isinstance(value, bytes):
        return value.decode(encoding if encoding else "utf-8")
    return value

def extract_email_body(msg):
    from bs4 import BeautifulSoup
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body += part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                soup = BeautifulSoup(html_body, 'html.parser')
                body += soup.get_text()
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
    return body.strip()

def parse_email_date(date_str):
    from datetime import datetime
    try:
        parsed_date = datetime.strptime(date_str.split(' (')[0], '%a, %d %b %Y %H:%M:%S %z')
        return parsed_date.strftime('%Y-%m-%d')
    except:
        return "Unknown"

def fetch_all_emails():
    mail = connect_to_email()
    email_ids = search_all_emails(mail)
    results = []

    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg["Subject"]
        from_ = msg.get("From")
        date_ = msg.get("Date")

        body = extract_email_body(msg)
        full_text = f"{subject} {body}"

        email_data = {
            "subject": subject,
            "from": from_,
            "date": parse_email_date(date_),
            "body": body,
            "label": auto_label(full_text)
        }

        print(f"Fetched email: {subject}")

        results.append(email_data)

    mail.logout()

    return results

if __name__ == "__main__":
    mail = connect_to_email()
    email_ids = search_all_emails(mail)

    all_emails = []

    for email_id in email_ids:
        try:
            msg = fetch_email(mail, email_id)
            email_info = {
                "subject": msg["Subject"],
                "from": msg.get("From"),
                "date": parse_email_date(msg.get("Date")),
                "body": extract_email_body(msg)
            }
            all_emails.append(email_info)
            print(f"Fetched email: {email_info['subject']}")
        except Exception as e:
            print(f"Error fetching email {email_id}: {e}")
    
    mail.logout()

    import json
    with open('all_emails.json', 'w', encoding='utf-8') as f:
        json.dump(all_emails, f, ensure_ascii=False, indent=4)

    print(f"Total fetched emails: {len(all_emails)}")
