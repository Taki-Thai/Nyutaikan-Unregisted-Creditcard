import os, json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import gspread
from gspread_dataframe import set_with_dataframe

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_drive_service():
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_sheets_client():
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return gspread.authorize(creds)


def list_files_in_folder(service, folder_id: str) -> dict:
    query = (
        f"'{folder_id}' in parents"
        " and mimeType != 'application/vnd.google-apps.folder'"
        " and trashed = false"
    )
    all_files = {}
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        all_files.update({f["name"]: f["id"] for f in results.get("files", [])})
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return all_files


def download_file(service, file_id: str, dest_path: str):
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def write_to_sheet(gc, sheet_id: str, sheet_name: str, df, clear=True):
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="50")
    if clear:
        ws.clear()
    set_with_dataframe(ws, df, resize=True)
