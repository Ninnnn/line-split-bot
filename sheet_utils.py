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

# ===== 個人記帳功能 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    """新增一筆個人記帳記錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, amount, date, invoice_number])

def get_personal_records_by_user(name):
    """取得指定使用者的所有個人記帳紀錄與總金額"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    user_records = df[df["姓名"] == name]
    total_amount = user_records["金額"].sum() if not user_records.empty else 0
    return user_records.to_string(index=False), total_amount

def get_all_personal_records_by_user():
    """取得所有個人記帳紀錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_records()
    return records

def reset_personal_record_by_name(name):
    """刪除指定使用者的所有個人記帳紀錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_values()
    headers = records[0]
    filtered = [row for row in records[1:] if row[0] != name]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

def delete_personal_record_by_index(name, index):
    """刪除指定使用者在個人記帳中的某一筆紀錄（根據index）"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_records()

    personal_records = [r for r in records if r.get('姓名') == name]

    if index < 0 or index >= len(personal_records):
        return False  # 索引超出範圍

    target_row = None
    count = 0
    for i, record in enumerate(records):
        if record.get('姓名') == name:
            if count == index:
                target_row = i + 2  # Google Sheets第1行是標題
                break
            count += 1

    if target_row:
        sheet.delete_rows(target_row)
        return True
    else:
        return False

# ===== 群組記帳功能 =====
def append_group_record(payer, participants, item, amount, date, invoice_number=""):
    """新增一筆群組記帳記錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row([payer, participants, item, amount, date, invoice_number])

def get_all_group_records():
    """取得所有群組記帳紀錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    records = sheet.get_all_records()
    return records

def delete_group_record_by_index(index):
    """刪除群組記帳的某一筆紀錄（根據index）"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    records = sheet.get_all_records()

    if index < 0 or index >= len(records):
        return False  # 索引超出範圍

    target_row = index + 2  # Google Sheets第1行是標題
    sheet.delete_rows(target_row)
    return True
