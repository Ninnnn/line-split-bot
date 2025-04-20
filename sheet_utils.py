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
    """
    新增團體記錄至 Google Sheets
    """
    try:
        sheet = spreadsheet.worksheet("group_records")
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            who, str(amount),
            ",".join(members),  # 成員列表
            note, date
        ])
    except Exception as e:
        print(f"寫入 Google Sheet 失敗（團體記錄）: {e}")

def append_personal_record(user_id, amount, note, date):
    """
    新增個人記錄至 Google Sheets
    """
    try:
        sheet = spreadsheet.worksheet("personal_records")
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id, str(amount),
            note, date
        ])
    except Exception as e:
        print(f"寫入 Google Sheet 失敗（個人記錄）: {e}")

def get_personal_records_by_user(user_id):
    """
    根據 user_id 獲取特定使用者的個人記錄
    """
    try:
        sheet = spreadsheet.worksheet("personal_records")
        all_records = sheet.get_all_records()
        return [r for r in all_records if str(r["user_id"]) == str(user_id)]
    except Exception as e:
        print(f"讀取 Google Sheet 失敗（查詢個人記錄）: {e}")
        return []
