import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("SplitBotData")

def append_group_record(who, amount, members, note, date):
    sheet = spreadsheet.worksheet("group_records")
    sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), who, str(amount), ",".join(members), note, date])

def append_personal_record(name, amount, note, date):
    sheet = spreadsheet.worksheet("personal_records")
    sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, str(amount), note, date])

def get_personal_records_by_user(name):
    sheet = spreadsheet.worksheet("personal_records")
    records = sheet.get_all_records()
    return [r for r in records if r["user_id"] == name]

def reset_personal_record_by_name(name):
    sheet = spreadsheet.worksheet("personal_records")
    all_data = sheet.get_all_values()
    headers = all_data[0]
    filtered_data = [row for row in all_data[1:] if row[1] != name]
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered_data:
        sheet.append_row(row)
