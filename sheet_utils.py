import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import re

# ==== Google Sheets 認證與初始化 ====

SPREADSHEET_ID = '1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94'
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
        if r['Group'] == group_name:
            return r['Members'].split(',')
    return []

def append_group_record(group, meal, amount, payer, adjustments):
    sheet = get_worksheet(group)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now, meal, amount, payer] + [f"{k}{v:+}" for k, v in adjustments.items()]
    sheet.append_row(row)

def get_group_records(group):
    sheet = get_worksheet(group)
    df = pd.DataFrame(sheet.get_all_records())
    return df

def delete_group_meal(group, date_str, meal_name):
    sheet = get_worksheet(group)
    records = sheet.get_all_records()
    headers = sheet.row_values(1)
    for idx, r in enumerate(records):
        if r['Date'].startswith(date_str) and r['Meal'] == meal_name:
            sheet.delete_rows(idx + 2)
            return True
    return False

def reset_group_records(group):
    sheet = get_worksheet(group)
    sheet.clear()
    sheet.append_row(["Date", "Meal", "Amount", "Payer", "Adjustments"])
    return True

# ==== 公費管理功能 ====

def append_group_fund_record(group, member, amount, record_type):
    sheet = get_worksheet("group_funds")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([now, group, member, amount, record_type])

def get_group_fund_balance(group):
    sheet = get_worksheet("group_funds")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df['Group'] == group]
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df['Amount'] = df.apply(lambda r: r['Amount'] if r['Type'] == 'topup' else -r['Amount'], axis=1)
    summary = df.groupby('Member')['Amount'].sum().to_dict()
    return summary

def format_group_fund_balance(group):
    balances = get_group_fund_balance(group)
    members = get_group_members(group)
    result = [f"💰【{group}】目前公費餘額："]
    total = 0
    for m in members:
        bal = balances.get(m, 0)
        result.append(f"{m}: {bal:.0f} 元")
        total += bal
    result.append(f"📊 公費總餘額：{total:.0f} 元")
    return "\n".join(result)

def suggest_group_fund_topup(group):
    balances = get_group_fund_balance(group)
    members = get_group_members(group)
    avg = sum(balances.get(m, 0) for m in members) / len(members)
    result = [f"💡【{group}】建議儲值金額："]
    for m in members:
        diff = avg - balances.get(m, 0)
        if diff > 0:
            result.append(f"{m}：建議補 {round(diff)} 元")
    return "\n".join(result)

def format_group_fund_history(group):
    sheet = get_worksheet("group_funds")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df['Group'] == group]
    if df.empty:
        return "⚠️ 查無記錄"
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df['Sign'] = df['Type'].apply(lambda x: '+' if x == 'topup' else '-')
    result = [f"📜【{group}】公費記錄："]
    for _, row in df.iterrows():
        result.append(f"{row['Date']} | {row['Member']} {row['Sign']}{abs(row['Amount'])} 元")
    return "\n".join(result)

def deduct_group_fund(group, deductions):
    for member, amount in deductions.items():
        append_group_fund_record(group, member, amount, 'deduct')

def top_up_group_fund(group, amount=None, contributions=None):
    members = get_group_members(group)
    if not members:
        return "❗查無團體成員"

    if contributions:  # 個別儲值
        try:
            for item in contributions:
                match = re.match(r"(\S+)\+(\d+)", item)
                if not match:
                    continue
                name, value = match.groups()
                if name not in members:
                    continue
                append_group_fund_record(group, name, int(value), 'topup')
            return f"✅【{group}】已記錄個別儲值"
        except:
            return "❗儲值格式錯誤，請使用：小明+300 小花+200"

    elif amount:  # 平均儲值
        avg = round(amount / len(members))
        for m in members:
            append_group_fund_record(group, m, avg, 'topup')
        return f"✅【{group}】每人平均儲值 {avg} 元"

    return "❗請提供儲值金額或明細"

# ==== 整體查詢整合 ====

def get_group_fund_summary(group):
    balances = get_group_fund_balance(group)
    members = get_group_members(group)
    total = sum(balances.get(m, 0) for m in members)
    avg = total / len(members)
    result = [f"📊【{group}】公費平衡分析："]
    for m in members:
        paid = balances.get(m, 0)
        diff = paid - avg
        status = f"多出 {round(diff)} 元" if diff > 0 else f"應補 {round(-diff)} 元"
        result.append(f"{m}：目前 {paid:.0f} 元，{status}")
    result.append(f"💼 公費總額：{total:.0f} 元")
    return "\n".join(result)

# ==== Alias for app.py 對接 ====

query_group_records = get_group_records
query_group_fund_history = format_group_fund_history
