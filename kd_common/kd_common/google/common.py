import pickle
import os.path
from typing import Any
from os.path import join

from google_auth_oauthlib.flow import InstalledAppFlow 
from google.auth.transport.requests import Request 

from kd_common import pathutil


_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
_FILE_TOKEN = join(pathutil.FOLDER_GOOGLE, "token.pickle")
_FILE_CREDENTIALS = join(pathutil.FOLDER_GOOGLE, "credentials.json")


def get_credentials() -> Any:
    creds = None
    if os.path.exists(_FILE_TOKEN):
        with open(_FILE_TOKEN, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                _FILE_CREDENTIALS, _SCOPES)
            creds = flow.run_console()
        # Save the credentials for the next run
        with open(_FILE_TOKEN, 'wb') as token:
            pickle.dump(creds, token)
    return creds
