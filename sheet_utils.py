import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets 認證與初始化
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "你的 Google Sheet ID"

def add_group_fund(group_name, member, amount, date=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    if date is None:
        date = datetime.now().strftime("%Y/%m/%d")
    sheet.append_row([group_name, member, float(amount), "topup", date])

def deduct_group_fund(group_name, member, amount, date=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    if date is None:
        date = datetime.now().strftime("%Y/%m/%d")
    sheet.append_row([group_name, member, -float(amount), "deduct", date])

def get_group_fund_balance(group_name, member):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    balance = sum(
        r["Amount"] for r in records
        if r["Group"] == group_name and r["Member"] == member
    )
    return balance

def get_group_fund_summary(group_name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    summary = {}
    for r in records:
        if r["Group"] == group_name:
            member = r["Member"]
            summary.setdefault(member, 0)
            summary[member] += r["Amount"]
    return summary

def get_group_fund_history(group_name, member=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    filtered = [
        r for r in records
        if r["Group"] == group_name and (member is None or r["Member"] == member)
    ]
    return filtered

def delete_group_record_by_index(group_name, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    count = 0
    for i, r in enumerate(records, start=2):  # row index in sheet (headers at row 1)
        if r["Group"] == group_name:
            if count == index:
                sheet.delete_rows(i)
                return True
            count += 1
    return False

def get_group_list():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    return sorted(list(set(r["Group"] for r in records)))

