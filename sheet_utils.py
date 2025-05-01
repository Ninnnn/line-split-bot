import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import requests

# ===== Google Sheets 設定 =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94"

# ===== 個人記帳 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, float(amount), date, invoice_number])

def get_personal_records_by_user(name):
    df = pd.DataFrame(client.open_by_key(SPREADSHEET_ID).worksheet("personal_records").get_all_records())
    user_records = df[df["Name"] == name]
    total_amount = user_records["Amount"].sum() if not user_records.empty else 0
    return user_records.to_string(index=False), total_amount

def get_all_personal_records_by_user(name):
    df = pd.DataFrame(client.open_by_key(SPREADSHEET_ID).worksheet("personal_records").get_all_records())
    return df[df["Name"] == name]

def reset_personal_record_by_name(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    rows = sheet.get_all_values()
    headers = rows[0]
    filtered = [r for r in rows[1:] if r[0] != name]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

def delete_personal_record_by_index(name, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Name"] == name]
    if index < 0 or index >= len(df):
        return False
    row_num = df.index[index] + 2
    sheet.delete_rows(row_num)
    return True

# ===== 團體記帳 =====
def append_group_record(group, date, meal, item, payer, member_string, amount, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row([group, date, meal, item, payer, member_string, float(amount), invoice_number])

def get_group_records_by_group(group):
    df = pd.DataFrame(client.open_by_key(SPREADSHEET_ID).worksheet("group_records").get_all_records())
    return df[df["Group"] == group]

def reset_group_record_by_group(group):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    rows = sheet.get_all_values()
    headers = rows[0]
    filtered = [r for r in rows[1:] if r[0] != group]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered:
        sheet.append_row(row)

def delete_group_record_by_index(group, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Group"] == group]
    if index < 0 or index >= len(df):
        return False
    row_num = df.index[index] + 2
    sheet.delete_rows(row_num)
    return True

# ===== 中獎查詢用 =====
def append_invoice_record(name, invoice, date, amount):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, "補發票", float(amount), date, invoice])

def get_invoice_records_by_user(name):
    df = pd.DataFrame(client.open_by_key(SPREADSHEET_ID).worksheet("personal_records").get_all_records())
    df = df[(df["Name"] == name) & (df["Invoice"] != "")]
    return df

def get_invoice_lottery_results(name):
    try:
        df = get_invoice_records_by_user(name)
        if df.empty:
            return f"⚠️ {name} 沒有發票紀錄"

        # 下載對獎號碼
        url = "https://invoice.etax.nat.gov.tw/invoice.xml"
        xml = requests.get(url).content.decode("utf-8")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        items = root.findall(".//item")

        all_prizes = {}
        for item in items:
            title = item.find("title").text
            ptext = item.find("description").text.replace("<br>", "\n")
            lines = ptext.split("\n")
            prizes = [l.strip() for l in lines if l.strip()]
            all_prizes[title] = prizes

        results = [f"📬 {name} 的中獎查詢："]
        for _, row in df.iterrows():
            date_str = str(row["Date"])
            invoice = row["Invoice"].replace("-", "").upper()
            try:
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
                m = date_obj.month
                y = date_obj.year - 1911
                period = f"{y}/{(m-1)//2*2+1:02d}-{(m-1)//2*2+2:02d}"
            except:
                period = "未知期別"
            prize_list = "\n".join(all_prizes.get(period, []))
            result = "未中獎"
            for p in prize_list.split("\n"):
                if len(p) < 3: continue
                if invoice[-3:] in p:
                    result = "✅ 可能中獎"
                    break
            results.append(f"{date_str} - {invoice} ➜ {result}")
        return "\n".join(results)

    except Exception as e:
        return f"❌ 發票對獎錯誤：{e}"
