from datetime import datetime
import imaplib,csv, email, re, os, time, schedule
from email.header import decode_header
from dotenv import load_dotenv

# load .env
load_dotenv()

# Create CSV file
f = open('application_tracker.csv', 'w', newline='')
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
    # count
    count = 0

    try:
        # IMAP 서버에 연결
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(username, password)
        mail.select("inbox")

        # 이메일 검색 - 특정 제목으로 시작하는 이메일 검색
        status, messages_1 = mail.search(None, '(HEADER Subject "Your application to")')
        status, messages_2 = mail.search(None, '(HEADER Subject "your application was sent to")')
        # status, messages = mail.search(None, '(OR (HEADER Subject "Your application to") (HEADER Subject "your application was sent to"))')


        # 이메일 ID 병합
        email_ids_1 = messages_1[0].split()
        email_ids_2 = messages_2[0].split()
        email_ids = list(set(email_ids_1).union(set(email_ids_2)))
        # email_ids = messages[0].split()

        for email_id in email_ids[-5:]:
            # 이메일 데이터 가져오기
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            # 이메일 제목 디코딩
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            if "Your application was viewed" in subject:
                continue
            # 이메일 날짜 디코딩 및 형식 변환
            date_str, encoding = decode_header(msg["Date"])[0]
            if isinstance(date_str, bytes):
                date_str = date_str.decode(encoding if encoding else "utf-8")

            # " (UTC)"와 같은 불필요한 부분 제거
            date_str = date_str.split(' (')[0]

            # 날짜 파싱 및 형식 변환
            try:
                temp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                formatted_date = temp.strftime('%m-%d-%Y')
            except ValueError as e:
                print(f"Error parsing date: {date_str} -> {e}")
                formatted_date = "Unknown"

            # 이메일 발신자
            from_ = msg.get("From")

            # 키워드 리스트 정의
            keywords = ["Unfortunately", "unfortunately", "not be moving forward"]

    
            # 이메일 본문 추출
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        print("Body Error")

                    if content_type == "text/plain" and "attachment" not in content_disposition:        
                        for keyword in keywords:
                            if keyword in body:
                                count += 1

                        if count > 0:
                            application_status = "Reject"
                            count = 0

                        company = re.findall(r'\bto\b\s(.+?)(?:\.\s|$)', subject, re.DOTALL)[0]
                        if not company:
                            company = None

                        print(f"Subject: {subject}")
                        print(f'Company: {company}')
                        print(f'Date: {formatted_date}')
                        print(f'Status: {application_status}')
                        print(f"Body: {body}")
                        print("="*100)
                        write.writerow([index, formatted_date, company, application_status])
            else:
                content_type = msg.get_content_type()
                body = msg.get_payload(decode=True).decode()
                if content_type == "text/plain":
                    print(f"herererererer: {body}")
                    print("="*100)
            index += 1


        # IMAP 서버 연결 종료
        mail.logout()

    except Exception as e:
        print(f"An error occurred: {e}")

# 주기적으로 이메일을 확인 (예: 10분마다)
check_emails()
# schedule.every(10).minutes.do(check_emails)

# while True:
#     schedule.run_pending()
#     time.sleep(1)
