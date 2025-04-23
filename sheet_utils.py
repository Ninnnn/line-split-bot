import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from google.cloud import vision
import io

# Google Sheets Authentication
def authenticate_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('path_to_credentials.json', scope)
    client = gspread.authorize(creds)
    return client

# Google Vision API OCR
def extract_text_from_image(image_path):
    client = vision.ImageAnnotatorClient()
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""

def append_group_record(record):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("group_records")
    sheet.append_row(record)

def append_personal_record(record):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    sheet.append_row(record)

def get_personal_records_by_user(name):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    records = sheet.get_all_records()
    return [record for record in records if record.get("name") == name]

def reset_personal_record_by_name(name):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    all_records = sheet.get_all_records()
    rows_to_keep = [i+2 for i, r in enumerate(all_records) if r.get("name") != name]
    all_rows = list(range(2, len(all_records)+2))
    rows_to_delete = sorted(set(all_rows) - set(rows_to_keep), reverse=True)
    for row in rows_to_delete:
        sheet.delete_rows(row)
