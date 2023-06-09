from __future__ import print_function
import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
import oauth2client
from oauth2client import client, tools, file
import httplib2
from apiclient import discovery

SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'backup\client_secret.json'
APPLICATION_NAME = 'db backup'

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def upload_basic(file_path):
    file_name = os.path.basename(file_path)

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    file_metadata = {
        'name': file_name,
        'parents': ['13ZBu0Id4Ef6CohnV2idlI478xYHUWIb5'],
        'mimeType': '*/*',
    }

    media = MediaFileUpload(file_path)

    file = service.files().create(
        supportsTeamDrives=True,
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    print('File uploaded with ID:', file.get('id'))
    return file.get('id')





