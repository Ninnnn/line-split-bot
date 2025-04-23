import gspread
from oauth2client.service_account import ServiceAccountCredentials

def authenticate_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('path_to_credentials.json', scope)
    client = gspread.authorize(creds)
    return client

def append_record(sheet_name, record_data):
    client = authenticate_google_sheets()
    sheet = client.open('Expense Records').worksheet(sheet_name)
    sheet.append_row(record_data)

def get_personal_records(user_name):
    client = authenticate_google_sheets()
    sheet = client.open('Expense Records').worksheet('personal_records')
    records = sheet.get_all_records()
    return [record for record in records if record['name'] == user_name]

def delete_record(sheet_name, record_id):
    client = authenticate_google_sheets()
    sheet = client.open('Expense Records').worksheet(sheet_name)
    sheet.delete_rows(record_id)
