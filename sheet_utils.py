import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# Google Sheets 授權
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = '你的 Google Sheet ID'

# ===== 個人記帳 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, amount, date, invoice_number])

def get_personal_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    user_records = df[df["姓名"] == name]
    total_amount = user_records["金額"].sum() if not user_records.empty else 0
    return user_records.to_string(index=False), total_amount

def get_all_personal_records_by_user():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_records()
    return records

def reset_personal_record_by_name(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_values()
    headers = records[0]
    filtered = [row for row in records[1:] if row[0] != name]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

# ===== 群組記帳 =====
def append_group_record(payer, participants, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row([payer, participants, item, amount, date, invoice_number])

def get_all_group_records():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    records = sheet.get_all_records()
    return records

# ===== 其他功能例如：刪除記錄、查詢中獎等可依需求擴充 =====
