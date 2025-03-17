from flask import Flask, render_template, request, jsonify
import imaplib
import email, re
from email.header import decode_header
from datetime import datetime
from bs4 import BeautifulSoup
from auth import USERNAME, creds, oauth2_login
import spacy

app = Flask(__name__)

# Load spaCy's pre-trained NER model
nlp = spacy.load("en_core_web_trf")

def extract_company_names(subject, from_, body):
    doc_subject = nlp(remove_punctuation(subject))
    doc_from = nlp(from_)
    doc_body = nlp(remove_punctuation(body))
    
    company_names_subject = [ent.text for ent in doc_subject.ents if ent.label_ == "ORG"]
    if company_names_subject:
        return company_names_subject
    
    company_names_from = [ent.text for ent in doc_from.ents if ent.label_ == "ORG"]
    if company_names_from:
        return company_names_from
    
    company_names_body = [ent.text for ent in doc_body.ents if ent.label_ == "ORG"]
    return company_names_body

def connect_to_email():
    mail = oauth2_login(USERNAME, creds)
    mail.select("inbox")
    return mail

def search_emails(mail, start_date, end_date):
    status, messages = mail.search(None, f'(SINCE "{start_date}" BEFORE "{end_date}")')
    return messages[0].split()

def fetch_email(mail, email_id):
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    return email.message_from_bytes(msg_data[0][1])

def decode_header_value(header_value):
    value, encoding = decode_header(header_value)[0]
    if isinstance(value, bytes):
        value = value.decode(encoding if encoding else "utf-8")
    return value.lower()

def remove_punctuation(text):
    return re.sub(r'[^a-zA-Z\s]', '', text).replace('\n', '')

def parse_email_date(date_str):
    date_str = date_str.split(' (')[0]
    try:
        temp = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return temp.strftime('%m/%d/%Y')
    except ValueError as e:
        print(f"Error parsing date: {date_str} -> {e}")
        return "Unknown"

def extract_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                soup = BeautifulSoup(html_body, 'html.parser')
                body = soup.get_text()
    else:
        else_body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        soup = BeautifulSoup(else_body, 'html.parser')
        body = soup.get_text()
    return body.lower()

def determine_email_category(subject, body):
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    application_keywords = [
        "carefully review", 'thank you for submitting your resume', 
        'thanks for completing your application','thank you for your interest', 
        'thank you from', 'application received', 'thank you for your application', 
        'application submitted to', 'thank you for applying', 'thanks for applying', 
        'thank you for applying with', 'submitting your application', 
        'reviewing your resume', 'received your application'
    ]
    rejection_keywords = [
        'will not be moving forward', 'not consider you','decided not to move forward', 
        'regret to inform you', 'other candidates', 'unable to move you  forward'
    ]
    further_keywords = ["next steps", "take the assessments"]

    is_application = any(keyword in subject_lower for keyword in application_keywords) 
    is_rejection = any(keyword in body_lower for keyword in rejection_keywords)
    is_positive = any(keyword in body_lower for keyword in further_keywords) or any(keyword in subject_lower for keyword in further_keywords)

    if is_rejection:
        return "reject"
    elif is_application:
        return "apply"
    else:
        return "other"

def filter_handshake(subject):
    if "Application submitted to" in subject:
        return 'apply'  
    return 'other'

# 수정: start_date와 end_date 파라미터를 받도록 변경
def check_emails(start_date, end_date):
    results = []
    try:
        mail = connect_to_email()
        email_ids = search_emails(mail, start_date, end_date)

        for idx, email_id in enumerate(email_ids):
            msg = fetch_email(mail, email_id)
            subject = decode_header_value(msg["Subject"])
            body = extract_email_body(msg)
            from_ = msg.get("From")
            
            if "Handshake" in from_ and not filter_handshake(subject):
                category = filter_handshake(subject)
            else:
                category = determine_email_category(subject, body)
            
            date_str = decode_header_value(msg["Date"])
            formatted_date = parse_email_date(date_str)
            company = extract_company_names(subject, from_, body)
            
            result = {
                "id": idx,
                "date": formatted_date,
                "from": from_,
                "company": company if company else ["N/A"],
                "subject": subject,
                "body": body,
                "category": category
            }
            results.append(result)
        mail.logout()
    except Exception as e:
        print(f"An error occurred: {e}")
    return results

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["GET"])
def start_classification():
    # 사용자 입력 받은 날짜 값 (형식: YYYY-MM-DD)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    
    # 기본값 설정 (사용자가 입력하지 않을 경우)
    if start_date_str:
        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
            start_date = start_date_obj.strftime("%d-%b-%Y")
        except Exception as e:
            start_date = datetime(2025, 3, 1).strftime("%d-%b-%Y")
    else:
        start_date = datetime(2025, 3, 1).strftime("%d-%b-%Y")
    
    if end_date_str:
        try:
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
            end_date = end_date_obj.strftime("%d-%b-%Y")
        except Exception as e:
            end_date = datetime.now().strftime("%d-%b-%Y")
    else:
        end_date = datetime.now().strftime("%d-%b-%Y")
    
    emails = check_emails(start_date, end_date)
    return jsonify(emails)

if __name__ == "__main__":
    app.run(debug=True)
