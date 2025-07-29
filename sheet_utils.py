import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# ==== Google Sheets 認證與初始化 ====
SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE'  # 請替換為實際 Spreadsheet ID
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

def get_worksheet(name):
    return client.open_by_key(SPREADSHEET_ID).worksheet(name)

# ==== 團體記帳功能 ====

def create_group(group_name, members):
    group_sheet = get_worksheet("groups")
    existing = group_sheet.col_values(1)
    if group_name in existing:
        return False
    group_sheet.append_row([group_name, ",".join(members)])
    sheet = client.open_by_key(SPREADSHEET_ID)
    sheet.add_worksheet(title=group_name, rows="1000", cols="10")
    return True

def get_group_members(group_name):
    group_sheet = get_worksheet("groups")
    records = group_sheet.get_all_records()
    for r in records:
        if r['group_name'] == group_name:
            return r['members'].split(',')
    return []

def split_group_expense(group, meal, total_amount, adjustments_list):
    members = get_group_members(group)
    if not members:
        return f"⚠️ 查無團體 {group} 的成員"

    adjustments = {}
    for adj in adjustments_list:
        name, offset = re.match(r'(\D+)([+-]\d+)', adj).groups()
        if name not in members:
            return f"⚠️ 成員 {name} 不在團體中"
        adjustments[name] = int(offset)

    base_total = total_amount - sum(adjustments.values())
    share = base_total // len(members)
    final = {m: share + adjustments.get(m, 0) for m in members}
    for name, amt in final.items():
        append_group_fund_record(group, name, amt, 'deduct')

    append_group_record(group, meal, total_amount, '系統', adjustments)
    return f"✅ 分帳完成：每人約 {share} 元，已記入扣款"

def append_group_record(group, meal, amount, payer, adjustments):
    sheet = get_worksheet(group)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now, meal, amount, payer] + [f"{k}{v:+}" for k, v in adjustments.items()]
    sheet.append_row(row)

def get_group_records(group):
    sheet = get_worksheet(group)
    df = pd.DataFrame(sheet.get_all_records())
    if df.empty:
        return "⚠️ 尚未有任何記錄"
    df_str = df.to_string(index=False)
    return f"📊【{group}】團體記帳記錄：\n{df_str}"

def delete_group_meal(group, date_str, meal_name):
    sheet = get_worksheet(group)
    records = sheet.get_all_records()
    for idx, r in enumerate(records):
        record_date = r.get("時間", "")[:10]
        if record_date == date_str and r.get("餐別") == meal_name:
            sheet.delete_rows(idx + 2)  # +2 是因為 get_all_records() 從第2列開始
            return f"✅ 已刪除 {date_str} 的 {meal_name} 記錄"
    return f"⚠️ 找不到 {date_str} 的 {meal_name} 記錄"

def top_up_group_fund(group_name, records: dict):
    """
    儲值團體公費，records 是 dict 格式：{ '小明': 300, '小花': 200 }
    """
    sheet = get_worksheet('group_funds')
    today = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for name, amount in records.items():
        sheet.append_row([group_name, name, today, amount, '儲值'])
    return f"✅ 已為 {group_name} 儲值公費：{', '.join([f'{k}+{v}' for k, v in records.items()])}"

def format_group_fund_history(group_name):
    sheet = get_worksheet('group_funds')
    records = sheet.get_all_records()
    filtered = [r for r in records if r['group_name'] == group_name]

    if not filtered:
        return f"⚠️ 找不到 {group_name} 的公費紀錄"

    lines = [f"📜【{group_name}】公費紀錄："]
    for r in filtered:
        time = r.get('timestamp') or r.get('time') or ''
        action = "儲值" if r['type'] == '儲值' else "扣款"
        lines.append(f"{time} - {r['member']} {action} {r['amount']} 元")

    return "\n".join(lines)
