import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import requests

# ===== Google Sheets 授權設定 =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94"  # ✅ 你的 Google Sheet ID

# ===== 個人記帳功能 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, amount, date, invoice_number])

def get_personal_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Name"] == name]

    if df.empty:
        return "⚠️ 查無記錄", 0

    total = df["Amount"].sum()

    formatted = df[["Name", "Item", "Amount", "Date", "Invoice"]].to_string(
        index=False,
        justify="left",
        col_space=10
    )
    return formatted, total

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
    records = df[df["Name"] == name]

    if index < 0 or index >= len(records):
        return False

    row_number = records.index[index] + 2  # +2 for header and 0-index
    sheet.delete_rows(row_number)
    return True

# ===== 團體記帳功能 =====
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
    records = df[df["Group"] == group]

    if index < 0 or index >= len(records):
        return False

    row_number = records.index[index] + 2
    sheet.delete_rows(row_number)
    return True

def delete_group_record_by_date_meal(group, date, meal):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    df_filtered = df[(df["Group"] == group) & (df["Date"] == date) & (df["Meal"] == meal)]

    if df_filtered.empty:
        return False

    sheet_data = sheet.get_all_values()
    headers = sheet_data[0]
    body = sheet_data[1:]
    kept = [row for row in body if not (row[0] == group and row[1] == date and row[2] == meal)]

    sheet.clear()
    sheet.append_row(headers)
    for row in kept:
        sheet.append_row(row)
    return True

# ===== 發票功能 =====
def append_invoice_record(name, invoice_number, date, amount):
    append_personal_record(name, "發票補登", int(amount), date, invoice_number)

def get_invoice_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[(df["Name"] == name) & (df["Invoice"] != "")]
    return df

def get_invoice_lottery_results(name):
    df = get_invoice_records_by_user(name)
    if df.empty:
        return f"⚠️ {name} 沒有發票紀錄"

    # 擷取所有發票號碼與日期
    invoice_list = df[["Date", "Invoice"]].dropna().to_dict(orient="records")

    # 財政部開獎號碼
    try:
        url = "https://invoice.etax.nat.gov.tw/invoice.json"
        res = requests.get(url)
        award_data = res.json()[0]  # 只取最新一期
        year_month = f"{award_data['year']}/{award_data['month']}"

        # 對獎邏輯
        special = award_data["superPrizeNo"]  # 特別獎
        grand = award_data["spcPrizeNo"]      # 特獎
        first = award_data["firstPrize"]      # 頭獎（3 組）
        additional = award_data["sixPrize"]   # 增開六獎

        results = f"📬 {name} 的中獎查詢（{year_month}）：\n"

        for entry in invoice_list:
            num = entry["Invoice"]
            date = entry["Date"]
            matched = ""

            if num == special:
                matched = "特別獎 💰"
            elif num == grand:
                matched = "特獎 💰"
            elif any(num[:8] == f[:8] for f in first):
                matched = "頭獎 💰"
            elif any(num[-3:] == f[-3:] for f in first):
                matched = "六獎"
            elif any(num[-3:] == a for a in additional):
                matched = "六獎（增開）"
            else:
                matched = "未中獎"

            results += f"{date} - {num} ➜ {matched}\n"

        return results

    except Exception as e:
        return f"❌ 發票查詢失敗：{e}"
