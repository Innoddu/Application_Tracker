import imaplib, os, json, pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# load .env
load_dotenv()

# User setting
USERNAME = os.getenv("BEMAIL")


# Google OAuth2.0 settings
SCOPES = ['https://mail.google.com/']
creds = None

# Check if the token exists and load it
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = Credentials.from_authorized_user_info(json.loads(pickle.load(token)), SCOPES)

# If there are no (valid) credentials available, let the user log in
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)

    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds.to_json(), token)

# Function to log in to the IMAP server using OAuth2.0 credentials
def oauth2_login(email, creds):
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (email, creds.token)
    imap_conn = imaplib.IMAP4_SSL("imap.gmail.com")
    imap_conn.authenticate('XOAUTH2', lambda x: auth_string)
    return imap_conn
