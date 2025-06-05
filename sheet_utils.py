import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import requests

# ===== Google Sheets 授權設定 =====
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

SPREADSHEET_ID = "1lC2baFstZ51E3iT_29N8KOfMoknrHMleSzTKx2emZ94"  # 替換成你的 Google Sheet ID

# ===== 個人記帳功能 =====
def append_personal_record(name, item, amount, date, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    sheet.append_row([name, item, float(amount), date, invoice_number])

def get_personal_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Name"] == name]

    if df.empty:
        return "⚠️ 查無記錄", 0

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
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

    row_number = records.index[index] + 2
    sheet.delete_rows(row_number)
    return True

# ===== 團體記帳功能 =====
def append_group_record(group, date, meal, item, payer, member_string, amount, invoice_number=""):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    sheet.append_row([group, date, meal, item, payer, member_string, float(amount), invoice_number])

def get_group_records_by_group(group):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Group"] == group]
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df

def get_group_id(group_name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet('groups')
    data = sheet.get_all_records()
    for row in data:
        if row['group_name'] == group_name:
            return row['group_id']
    return None


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

def delete_group_record_by_meal(group, date, meal):
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

def create_group(group_name, members, group_id=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("groups")
    groups = sheet.col_values(1)
    if group_name in groups:
        return False

    members_str = ",".join(members)
    if group_id:
        sheet.append_row([group_name, group_id, members_str])
    else:
        sheet.append_row([group_name, "", members_str])
    return True

def get_group_members(group_name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("groups")
    records = sheet.get_all_records()
    for r in records:
        if r["Group"] == group_name:
            members = r.get("Member", "")
            if members:
                return [m.strip() for m in members.split(",") if m.strip()]
            else:
                return []
    return []

def add_member(group_name, member):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("groups")
    records = sheet.get_all_records()
    for i, r in enumerate(records, start=2):
        if r["Group"] == group_name:
            members = r.get("Member", "")
            members_list = [m.strip() for m in members.split(",") if m.strip()]
            if member in members_list:
                return True
            members_list.append(member)
            new_members_str = ",".join(members_list)
            sheet.update_cell(i, 2, new_members_str)
            return True
    return False

def remove_member(group_name, member):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("groups")
    records = sheet.get_all_records()
    for i, r in enumerate(records, start=2):
        if r["Group"] == group_name:
            members = r.get("Member", "")
            members_list = [m.strip() for m in members.split(",") if m.strip()]
            if member not in members_list:
                return False
            members_list.remove(member)
            new_members_str = ",".join(members_list)
            sheet.update_cell(i, 2, new_members_str)
            return True
    return False

def get_group_list():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("groups")
    records = sheet.get_all_records()
    return sorted(list(set(r["Group"] for r in records)))

# ===== 公費（群組基金）管理功能 =====
def add_group_fund(group, member, amount, date=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    if date is None:
        date = datetime.now().strftime("%Y/%m/%d")
    sheet.append_row([group, member, float(amount), "topup", date])

def deduct_group_fund(group, member, amount, date=None):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    if date is None:
        date = datetime.now().strftime("%Y/%m/%d")
    sheet.append_row([group, member, -float(amount), "deduct", date])

def get_group_fund_balance(group, member):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    balance = sum(
        r["Amount"] for r in records
        if r["Group"] == group and r["Member"] == member
    )
    return balance

def get_group_fund_summary(group):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    summary = {}
    for r in records:
        if r["Group"] == group:
            member = r["Member"]
            summary.setdefault(member, 0)
            summary[member] += r["Amount"]
    return summary

def get_group_fund_history(group_name):
    sheet = get_worksheet("group_fund_records")
    records = sheet.get_all_records()
    history = [r for r in records if r["群組"] == group_name]
    return history


def get_group_fund_balance_summary(group):
    balances = calculate_group_fund_balances(group)
    lines = [f"📊【{group}】公費結餘狀況："]
    for name, data in balances.items():
        lines.append(f"{name} ➜ 儲值 {data['top_up']} 元，扣款 {data['deducted']} 元，剩餘 {data['balance']} 元")
    return "\n".join(lines)


def format_group_fund_history(group, member=None):
    history = get_group_fund_history(group, member)
    if not history:
        return "⚠️ 查無記錄"
    lines = [f"📜【{group}】{' - ' + member if member else ''} 公費記錄："]
    for r in history:
        sign = "+" if r["Type"] == "topup" else "-"
        lines.append(f"{r['Date']} | {r['Member']} {sign}{abs(r['Amount'])} 元")
    return "\n".join(lines)

def delete_group_record_by_index_fund(group, index):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    count = 0
    for i, r in enumerate(records, start=2):
        if r["Group"] == group:
            if count == index:
                sheet.delete_rows(i)
                return True
            count += 1
    return False

def preview_group_fund_history_for_delete(group):
    history = get_group_fund_history(group)
    lines = [f"🧾【{group}】公費記錄索引列表："]
    for i, r in enumerate(history):
        lines.append(f"{i}. {r['Date']} | {r['Member']} | {r['Type']} | {r['Amount']} 元")
    return "\n".join(lines)

def preview_group_record_for_delete(group):
    df = get_group_records_by_group(group)
    if df.empty:
        return "⚠️ 無記錄"
    lines = [f"🧾【{group}】記帳記錄索引列表："]
    for i, row in df.iterrows():
        lines.append(f"{i}. {row['Date']} {row['Meal']} - {row['Item']}（{row['Amount']} 元）by {row['Payer']}")
    return "\n".join(lines)

def suggest_topup_for_group(group):
    balances = calculate_group_fund_balances(group)
    avg = sum(data["top_up"] for data in balances.values()) / len(balances)
    suggestions = []
    for name, data in balances.items():
        diff = round(avg - data["top_up"])
        if diff > 0:
            suggestions.append(f"{name} 建議補儲 {diff} 元")
    if not suggestions:
        return "✅ 所有成員儲值均衡，無需補儲"
    return "📌 公費補儲建議：\n" + "\n".join(suggestions)



def calculate_group_fund_balances(group_id):
    """
    回傳 dict：{
        '小明': {'top_up': 3000, 'deducted': 1750, 'balance': 1250},
        '小花': {...},
        ...
    }
    """
    fund_data = read_group_fund(group_id)
    spend_data = read_group_records(group_id)

    balances = {}
    for name in get_group_members(group_id):
        balances[name] = {'top_up': 0.0, 'deducted': 0.0, 'balance': 0.0}

    for record in fund_data:
        name, amount = record['name'], float(record['amount'])
        if name in balances:
            balances[name]['top_up'] += amount

    for record in spend_data:
        for member, amount in record['members'].items():
            if member in balances:
                balances[member]['deducted'] += float(amount)

    for name in balances:
        balances[name]['balance'] = balances[name]['top_up'] - balances[name]['deducted']

    return balances

def read_group_fund(group_id):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_funds")
    records = sheet.get_all_records()
    return [
        {"name": r["Member"], "amount": float(r["Amount"])}
        for r in records if r["Group"] == group_id
    ]

def read_group_records(group_id):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("group_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[df["Group"] == group_id]
    records = []
    for _, row in df.iterrows():
        members_str = row.get("Members") or row.get("MemberString", "")
        member_amounts = {}
        for part in members_str.split(","):
            part = part.strip()
            if "+" in part:
                name, adj = part.split("+")
                member_amounts[name.strip()] = float(adj.strip())
            else:
                member_amounts[part] = 0.0
        records.append({"members": member_amounts})
    return records




# ===== 發票功能 =====
def append_invoice_record(name, invoice_number, date, amount):
    append_personal_record(name, "發票補登", float(amount), date, invoice_number)

def get_invoice_records_by_user(name):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("personal_records")
    df = pd.DataFrame(sheet.get_all_records())
    df = df[(df["Name"] == name) & (df["Invoice"] != "")]
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df

def get_invoice_total_by_user(name):
    df = get_invoice_records_by_user(name)
    return df["Amount"].sum() if not df.empty else 0

def get_invoice_lottery_results(name):
    df = get_invoice_records_by_user(name)
    if df.empty:
        return f"⚠️ {name} 沒有發票紀錄"

    invoice_list = df[["Date", "Invoice"]].dropna().to_dict(orient="records")

    try:
        url = "https://invoice.etax.nat.gov.tw/invoice.json"
        res = requests.get(url)
        award_data = res.json()[0]
        year_month = f"{award_data['year']}/{award_data['month']}"

        special = award_data["superPrizeNo"]
        grand = award_data["spcPrizeNo"]
        first = award_data["firstPrize"]
        additional = award_data["sixPrize"]

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
