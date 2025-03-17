import imaplib
import email
import csv
import re
from email.header import decode_header
from datetime import datetime
from unicodedata import category
from bs4 import BeautifulSoup
import joblib
import pandas as pd
from OtherEmail.auth import USERNAME, creds, oauth2_login
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def words_in_texts(words, texts):
    texts = texts.astype(str)
    indicator_array = np.array([[1 if word in text else 0 for word in words] for text in texts])
    return indicator_array

def keyword_subject(data):
    df_keyword = data.copy()
    df_keyword['subject'] = df_keyword['subject'].astype(str)
    application_keywords = ["carefully review", 'thank you for submitting your resume', 'thanks for completing your application','thank you for your interest', 'thank you from', 'application received', 'thank you for your application', 'application submitted to', 'thank you for applying', 'thanks for applying', 'thank you for applying with', 'submitting your application', 'reviewing your resume', 'received your application']
    
    df_keyword['has_subject_keyword'] = df_keyword['subject'].apply(lambda x: 1 if any(keyword in x.lower() for keyword in application_keywords) else 0)
    return df_keyword

def normalization(data):
    data = (data - np.mean(data)) / np.std(data)
    return data

def process_data_fm(data):
    data = keyword_subject(data)
    data = create_is_application_feature(data)
    data['has_subject_keyword'] = normalization(data['has_subject_keyword'])
    return data

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
        return temp.strftime('%m-%d, %y')
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

def create_is_application_feature(df):
    """
    Create 'isApplication' feature based on the 'category' column.
    """
    df['isApplication'] = np.where((df['category'] == "reject") | (df['category'] == "apply"), 1, 0)
    return df

def filter_handshake(subject):
    if "Application submitted to" in subject:
        return 'apply'  
    return 'other'

def determine_email_category(subject, body):
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    application_keywords = ["carefully review", 'thank you for submitting your resume', 'thanks for completing your application','thank you for your interest', 'thank you from', 'application received', 'thank you for your application', 'application submitted to', 'thank you for applying', 'thanks for applying', 'thank you for applying with', 'submitting your application', 'reviewing your resume', 'received your application']
    rejection_keywords = ['will not be moving forward', 'not consider you','decided not to move forward', 'regret to inform you', 'other candidates', 'unable to move you  forward']
    further_keywords = ["next steps", "take the assessments"]

    is_application = any(keyword in subject_lower for keyword in application_keywords) 
    is_rejection = any(keyword in body_lower for keyword in rejection_keywords)
    is_postive = any(keyword in body_lower for keyword in further_keywords) or any(keyword in subject_lower for keyword in further_keywords)

    if is_rejection:
        return "reject"
    elif is_application:
        return "apply"
    else:
        return "other"

def classify_and_update_emails():
    try:
        mail = connect_to_email()
        start_date = datetime(2024, 6, 1).strftime('%d-%b-%Y')
        end_date = datetime.now().strftime('%d-%b-%Y')

        email_ids = search_emails(mail, start_date, end_date)

        # 저장된 로지스틱 회귀 모델 로드
        model = joblib.load('logistic_regression_model.pkl')

        with open('classified_emails.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'from', 'subject', 'body', 'category' 'isApplication'])

            for idx, email_id in enumerate(email_ids):
                msg = fetch_email(mail, email_id)
                subject = decode_header_value(msg["Subject"])
                body = extract_email_body(msg)
                
                from_ = msg.get("From")
                clean_subject = remove_punctuation(subject)
                date_str = decode_header_value(msg["Date"])
                formatted_date = parse_email_date(date_str)
                if "Handshake" in from_ and not filter_handshake(subject):
                    category = filter_handshake(subject)
                else:
                    category = determine_email_category(subject, body)
                
                new_data = pd.DataFrame({"id": [idx], "date":[formatted_date], 'from': [from_], 'subject': [clean_subject], 'body': [body], 'category': [category]})
                new_data = process_data_fm(new_data)
                new_data_features = pd.DataFrame({
                    'has_subject_keyword': new_data['has_subject_keyword'],
                    'applying': words_in_texts(['applying'], new_data['body']).flatten(),
                    'application': words_in_texts(['application'], new_data['body']).flatten(),
                    'reviewing': words_in_texts(['reviewing'], new_data['body']).flatten(),
                    'decided': words_in_texts(['decided'], new_data['body']).flatten(),
                    'interest': words_in_texts(['interest'], new_data['body']).flatten(),
                    'received': words_in_texts(['received'], new_data['body']).flatten(),
                    'moving forward': words_in_texts(['moving forward'], new_data['body']).flatten(),
                    'regret': words_in_texts(['regret'], new_data['body']).flatten(),
                    'resume': words_in_texts(['resume'], new_data['body']).flatten(),
                    
                })
                print(new_data_features)
                # 분류 예측
                predicted_class = model.predict(new_data_features)
                
                # 이메일 세부 사항 출력
                print(f"Date: {formatted_date}")
                print(f"From: {from_}")
                print(f"Subject: {subject}")
                print(f"Predicted Category: {predicted_class[0]}")
                print("="*100)

                writer.writerow([idx, formatted_date, from_, subject, body, category, predicted_class[0]])


        mail.logout()
    except Exception as e:
        print(f"An error occurred: {e}")

classify_and_update_emails()

