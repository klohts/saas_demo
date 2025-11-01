from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

flow = InstalledAppFlow.from_client_secrets_file(
    'keys/credentials.json', SCOPES)

creds = flow.run_local_server(port=0)

service = build('gmail', 'v1', credentials=creds)
profile = service.users().getProfile(userId='me').execute()

print("✅ Gmail connected as:", profile['emailAddress'])
