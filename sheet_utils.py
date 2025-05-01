import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import re
import requests

# ===== Google Sheets 設定 =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94"  # ⚠️請填入你的試算表 ID（僅此一處需自填）

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
    row_number = int(personal_records.index[index]) + 2
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
    row_number = int(group_records.index[index]) + 2
    sheet.delete_rows(row_number)
    return True

def delete_group_record_by_meal(group, date, meal):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    target = df[(df["Group"] == group) & (df["Date"] == date) & (df["Meal"] == meal)]
    if target.empty:
        return False
    for idx in sorted(target.index, reverse=True):
        sheet.delete_rows(int(idx) + 2)
    return True

# ===== 發票功能與對獎 =====
def append_invoice_record(name, invoice, date, amount):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row(["補發票", date, "", "補登", name, f"{name}:{amount}", amount, invoice])

def get_invoice_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    return df[(df["Payer"] == name) & (df["Invoice"] != "")]

def get_invoice_lottery_results(name):
    records = get_invoice_records_by_user(name)
    if records.empty:
        return f"⚠️ {name} 沒有發票紀錄"

    res = f"📬 {name} 的中獎查詢：\n"
    for _, row in records.iterrows():
        date = row["Date"]
        inv = row["Invoice"]
        amt = row["Amount"]

        try:
            y, m, d = map(int, date.split("/"))
            period_month = (m - 1) // 2 * 2 + 1
            period = f"{y}/{period_month:02d}-{period_month+1:02d}"
        except:
            period = "未知期別"

        is_win = check_lottery_winning(inv, period)
        status = "✅ 中獎" if is_win else "➜ 未中獎"
        res += f"{date} - {inv} ➜ {status}\n"
    return res

def check_lottery_winning(invoice_number, period):
    url = "https://invoice.etax.nat.gov.tw/invoiceService"
    payload = {
        "action": "QryWinningList",
        "invTerm": period.replace("/", "")
    }
    try:
        r = requests.get(url, params=payload, timeout=5)
        data = r.json()
        if "superPrizeNo" not in data:
            return False

        inv_head = invoice_number[:2]
        inv_tail = invoice_number[2:]

        if inv_tail == data["superPrizeNo"] or inv_tail == data["spcPrizeNo"]:
            return True

        for n in data.get("firstPrizeNo", "").split(","):
            if inv_tail == n or inv_tail[-7:] == n[-7:] or inv_tail[-6:] == n[-6:] or inv_tail[-5:] == n[-5:]:
                return True
        return False
    except:
        return False
