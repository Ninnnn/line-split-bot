import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 從 Render 環境變數讀取 JSON 字串
json_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(json_str)

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)

# 開啟 Google Sheet，名稱請改為你自己的試算表名稱
spreadsheet = client.open("SplitBotData")

def append_group_record(who, amount, members, note, date):
    sheet = spreadsheet.worksheet("group_records")
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        who, str(amount),
        ",".join(members),
        note, date
    ])

def append_personal_record(user_id, name, amount, note, date):
    sheet = spreadsheet.worksheet("personal_records")
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id, name, str(amount),
        note, date
    ])

def get_personal_records_by_user(name):
    sheet = spreadsheet.worksheet("personal_records")
    all_records = sheet.get_all_records()
    return [r for r in all_records if r["name"] == name]

def reset_personal_record_by_name(name):
    sheet = spreadsheet.worksheet("personal_records")
    all_records = sheet.get_all_values()
    headers = all_records[0]
    name_index = headers.index("name")
    
    rows_to_keep = [row for row in all_records if row[name_index] != name]
    
    # 清空原本資料並重寫
    sheet.clear()
    sheet.append_row(headers)
    for row in rows_to_keep[1:]:
        sheet.append_row(row)
