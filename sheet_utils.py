import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from google.cloud import vision
import io
import pandas as pd

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

# Append records
def append_group_record(record):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("group_records")
    sheet.append_row(record)

def append_personal_record(record):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    sheet.append_row(record)

# Get personal records by user
def get_personal_records_by_user(name):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    records = sheet.get_all_records()
    return [record for record in records if record.get("name") == name]

# Get all records by user
def get_all_personal_records_by_user(name):
    return get_personal_records_by_user(name)

# Reset records
def reset_personal_record_by_name(name):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet("personal_records")
    all_records = sheet.get_all_records()
    rows_to_keep = [i+2 for i, r in enumerate(all_records) if r.get("name") != name]
    all_rows = list(range(2, len(all_records)+2))
    rows_to_delete = sorted(set(all_rows) - set(rows_to_keep), reverse=True)
    for row in rows_to_delete:
        sheet.delete_rows(row)

# Delete record by index
def delete_record(sheet_name, index_list):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet(sheet_name)
    for index in sorted(index_list, reverse=True):
        sheet.delete_rows(index)

# Export to Excel
def export_records_to_excel(sheet_name, filename):
    client = authenticate_google_sheets()
    sheet = client.open("Expense Records").worksheet(sheet_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    return filename

# 發票中獎對獎功能
def check_invoice_lottery(invoice_numbers, winning_numbers):
    result = []
    for inv in invoice_numbers:
        matched = any(inv.endswith(w) for w in winning_numbers)
        result.append((inv, "中獎" if matched else "未中獎"))
    return result
