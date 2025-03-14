# google_drive_utils.py
import io
import os
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    # Parse the service account info from the secrets (convert string to dict)
    service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    return drive_service

def download_file(file_id, destination):
    drive_service = get_drive_service()
    request = drive_service.files().get_media(fileId=file_id)
    with io.FileIO(destination, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            st.write(f"Downloading... {int(status.progress() * 100)}% complete.")
    st.write(f"Downloaded to {destination}")

def upload_file(file_id, source):
    drive_service = get_drive_service()
    media = MediaFileUpload(source, resumable=True)
    updated_file = drive_service.files().update(fileId=file_id, media_body=media).execute()
    st.write("Uploaded file with ID:", updated_file.get('id'))
