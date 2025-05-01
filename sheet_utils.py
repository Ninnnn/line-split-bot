import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import requests
import re

# ===== Google Sheets 設定 =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94"  # ✅ 你的 Sheet ID

# ===== 個人記帳 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, amount, date, invoice_number])

def get_personal_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    user_records = df[df["Name"] == name]
    total_amount = user_records["Amount"].sum() if not user_records.empty else 0
    return user_records.to_string(index=False), total_amount

def get_all_personal_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    return df[df["Name"] == name]

def reset_personal_record_by_name(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    records = sheet.get_all_values()
    headers = records[0]
    filtered = [row for row in records[1:] if row[0] != name]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

def delete_personal_record_by_index(name, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    personal_records = df[df["Name"] == name]

    if index < 0 or index >= len(personal_records):
        return False

    row_number = personal_records.index[index] + 2
    sheet.delete_rows(row_number)
    return True

# ===== 團體記帳 =====
def append_group_record(group, date, meal, item, payer, member_string, amount, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row([group, date, meal, item, payer, member_string, amount, invoice_number])

def get_group_records_by_group(group):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    return df[df["Group"] == group]

def reset_group_record_by_group(group):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    records = sheet.get_all_values()
    headers = records[0]
    filtered = [row for row in records[1:] if row[0] != group]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

def delete_group_record_by_index(group, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    group_records = df[df["Group"] == group]

    if index < 0 or index >= len(group_records):
        return False

    row_number = group_records.index[index] + 2
    sheet.delete_rows(row_number)
    return True

# ===== 補發票用 =====
def append_invoice_record(name, invoice_number, date, amount):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row(["Manual補發票", date, "補發票", "補發票", name, f"{name}:{amount}", amount, invoice_number])

# ===== 查詢使用者發票紀錄（用於對獎）=====
def get_invoice_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    return df[(df["Payer"] == name) & (df["Invoice"] != "")]

# ===== 中獎號碼對獎查詢（最新一期）=====
def get_invoice_lottery_results(name):
    url = "https://invoice.etax.nat.gov.tw/invoice.xml"
    try:
        response = requests.get(url)
        response.encoding = "utf-8"
        xml = response.text

        title_match = re.search(r"<title>(\d+年\d+月\-?\d+月)</title>", xml)
        period = title_match.group(1) if title_match else "未知期別"

        sp = re.search(r"特別獎號碼：(\w{10})", xml)
        sp1 = re.search(r"特獎號碼：(\w{10})", xml)
        firsts = re.findall(r"頭獎號碼：(\w{10})", xml)

        sp = sp.group(1) if sp else ""
        sp1 = sp1.group(1) if sp1 else ""
        firsts = firsts if firsts else []

        df = get_invoice_records_by_user(name)
        if df.empty:
            return f"⚠️ {name} 沒有發票紀錄可查詢"

        result = f"📬 {name} 的中獎查詢（{period}）：\n"
        for _, row in df.iterrows():
            inv = row["Invoice"]
            date = row["Date"]
            prize = "未中獎"
            if inv == sp:
                prize = "🏆 特別獎 1000萬"
            elif inv == sp1:
                prize = "🎯 特獎 200萬"
            elif inv in firsts:
                prize = "🥇 頭獎 20萬"
            elif any(inv[2:] == f[2:] for f in firsts):
                prize = "🎁 六獎 200元"
            result += f"{date} - {inv} ➜ {prize}\n"

        return result
    except Exception as e:
        return f"❌ 對獎失敗：{e}"
