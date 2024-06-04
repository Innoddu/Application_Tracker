from datetime import datetime
import imaplib,csv, email, re, os, time, schedule
from email.header import decode_header
from dotenv import load_dotenv

# load .env
load_dotenv()

# Create CSV file
f = open('Linkedin_applications.csv', 'w', newline='')
write = csv.writer(f)
write.writerow(['#', 'Date', 'Company', 'Status'])



# User information
username = os.getenv("EMAIL")
password = os.getenv("PASSWORD")


IMAP_SERVER = "imap.gmail.com"

# Pattern for Apply job
pattern = r'\bto\b\s(.+?)(?:\.\s|$)'



# Negative Kewords
keywords = ["Unfortunately", "unfortunately", "not be moving forward"]
keyword_found = {keyword: False for keyword in keywords}

# Index


def check_emails():
    # index
    index = 0
    # Status
    application_status = "Apply"

    try:
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(username, password)
        mail.select("inbox")

        # Search date
        start_date = datetime(2024, 3, 1).strftime('%d-%b-%Y')
        end_date = datetime.now().strftime('%d-%b-%Y')

        # Search Email
        # status, messages_1 = mail.search(None, '(HEADER Subject "Your application to")')
        # status, messages_2 = mail.search(None, '(HEADER Subject "your application was sent to")')
        # status, messages = mail.search(None, '(OR (HEADER Subject "Your application to") (HEADER Subject "your application was sent to"))')
        # 추가 조건 설정
        additional_condition = '(OR (HEADER Subject "Your application to") (HEADER Subject "your application was sent to"))'

        # 날짜 범위와 추가 조건으로 이메일 검색
        status, messages = mail.search(None, f'(SINCE "{start_date}" BEFORE "{end_date}" {additional_condition})')


        # Email's id
        # email_ids_1 = messages_1[0].split()
        # email_ids_2 = messages_2[0].split()
        # email_ids = list(set(email_ids_1).union(set(email_ids_2)))
        email_ids = messages[0].split()

        for email_id in email_ids[:]:
            # Get email data
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            # Decode email subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            if "Your application was viewed" in subject:
                continue

            # Decode date
            date_str, encoding = decode_header(msg["Date"])[0]
            if isinstance(date_str, bytes):
                date_str = date_str.decode(encoding if encoding else "utf-8")

            # Remove "(UTC)" keyword in Data
            date_str = date_str.split(' (')[0]

            # Change format in Date
            try:
                temp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                formatted_date = temp.strftime('%m-%d-%Y')
            except ValueError as e:
                print(f"Error parsing date: {date_str} -> {e}")
                formatted_date = "Unknown"

            # Sender
            from_ = msg.get("From")
            # Get email body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == 'text/html':
                        body = part.get_payload(decode=True).decode()
                        match = re.findall(r'Unfortunately', body, re.DOTALL)
                
                        if match:
                            application_status = "Reject"
                        else:
                            application_status = "Apply"
                        company = re.findall(r'\bto\b\s(.+?)(?:\.\s|$)', subject, re.DOTALL)[0]
                        if not company:
                            company = None

                        print(f"Subject: {subject}")
                        print(f'Company: {company}')
                        print(f'Date: {formatted_date}')
                        print(f'index: {index}')
                        print(f'Status: {application_status}')
                        print(f'match: {match}')
                        print("="*100)

  
                        write.writerow([index, formatted_date, company, application_status])
            else:
                print("NOT MULTI PART HERE!!!!")
                content_type = msg.get_content_type()
                body = msg.get_payload(decode=True).decode()
                if content_type == "text/html":
                    body = part.get_payload(decode=True).decode()
                    match = re.findall(r'Unfortunately', body, re.DOTALL)
            
                    if match:
                        application_status = "Reject"
                    company = re.findall(r'\bto\b\s(.+?)(?:\.\s|$)', subject, re.DOTALL)[0]
                    if not company:
                        company = None
                    print(f"Subject: {subject}")
                    print(f'Company: {company}')
                    print(f'Date: {formatted_date}')
                    print(f'index: {index}')
                    print(f'Status: {application_status}')
                    print("="*100)
            index += 1


        # End IMAP server
        mail.logout()

    except Exception as e:
        print(f"An error occurred: {e}")


check_emails()
# Check email every 10 minutes
# schedule.every(10).minutes.do(check_emails)

# while True:
#     schedule.run_pending()
#     time.sleep(1)
