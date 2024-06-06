import email, csv
from email.header import decode_header
from datetime import datetime
from auth import USERNAME, creds, oauth2_login


f = open('email.csv', 'w', newline='')
write = csv.writer(f)
write.writerow(['#', 'Date', 'from', 'title', 'body'])

def check_emails():

    try:
        # Connect to the IMAP server
        mail = oauth2_login(USERNAME, creds)
        mail.select("inbox")

        start_date = datetime(2024, 6, 1).strftime('%d-%b-%Y')
        end_date = datetime.now().strftime('%d-%b-%Y')

        # Search for all emails
        status, messages = mail.search(None, f'SINCE {start_date} BEFORE {end_date}')
        email_ids = messages[0].split()

        # Process the first 10 emails
        for i, email_id in enumerate(email_ids):
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    date = msg['date']
                    sender = msg['from']
                    subject = msg['subject']
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if "attachment" in content_disposition:
                                attachment = "Yes"
                            else:
                                attachment = "No"
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body += part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()
                        attachment = "No"
                    
                    recipient = msg['to']
                    domain = sender.split('@')[-1]
                    keywords = any(keyword in body.lower() for keyword in ["application", "resume", "cv", "job", "position", "apply"])
                    length = len(body)

                    write.writerow([i+1, date, sender, subject, body, attachment, recipient, domain, keywords, length])

        # 이메일 연결 종료
        mail.logout()
        f.close()
    except Exception as e:
        print(f"An error occurred: {e}")

