import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# Google Sheets 授權
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = '1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94'

# ===== 個人記帳功能 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    """新增一筆個人記帳記錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, amount, date, invoice_number])

def get_personal_records_by_user(name):
    """取得指定使用者的個人記帳紀錄"""
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_records()
    user_records = [r for r in records if r.get("姓名") == name]
    return user_records

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
        return False

    target_row = None
    count = 0
    for i, record in enumerate(records):
        if record.get('姓名') == name:
            if count == index:
                target_row = i + 2
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
        return False

    target_row = index + 2
    sheet.delete_rows(target_row)
    return True

# ===== 發票中獎功能 =====
def get_invoice_lottery_results(user_records, winning_numbers):
    """
    根據使用者的發票記錄，查詢是否有中獎
    user_records: List of dicts
    winning_numbers: Dict，例如 {"特別獎": "12345678", "特獎": "87654321", "頭獎": ["11112222"]}
    """
    results = []
    for record in user_records:
        invoice = record.get("發票號碼") or record.get("發票")
        date = record.get("消費日期") or record.get("日期")
        if not invoice:
            continue
        for prize_name, numbers in winning_numbers.items():
            if isinstance(numbers, list):
                if any(invoice[-len(num):] == num for num in numbers):
                    results.append(f"{date} 發票 {invoice} 中了 {prize_name}")
            else:
                if invoice == numbers:
                    results.append(f"{date} 發票 {invoice} 中了 {prize_name}")
    return results
