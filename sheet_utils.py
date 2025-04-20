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

# 開啟 Google Sheet，名稱請改為你自己建立的試算表名稱
spreadsheet = client.open("SplitBotData")

def append_group_record(who, amount, members, note, date):
    sheet = spreadsheet.worksheet("group_records")
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        who, str(amount),
        ",".join(members),  # 成員列表
        note, date
    ])

def append_personal_record(user_id, amount, note, date):
    sheet = spreadsheet.worksheet("personal_records")
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id, str(amount),
        note, date
    ])

def get_personal_records_by_name(user_id):
    sheet = spreadsheet.worksheet("personal_records")
    all_records = sheet.get_all_records()
    return [r for r in all_records if str(r["User ID"]) == str(user_id)]  # 假設 "User ID" 是記錄的欄位名稱

def reset_personal_record_by_name(user_id):
    sheet = spreadsheet.worksheet("personal_records")
    all_records = sheet.get_all_records()
    # 查找並刪除對應 user_id 的所有記錄
    for i, record in enumerate(all_records, start=2):  # 假設資料從第二行開始
        if str(record["User ID"]) == str(user_id):  # 假設 "User ID" 是記錄的欄位名稱
            sheet.delete_row(i)  # 刪除該行
