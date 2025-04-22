import datetime

# 解析金額映射（例如：小明:40,100 小美:60）
def parse_amount_mapping(mapping_str):
    mapping = {}
    try:
        entries = mapping_str.split(",")
        for entry in entries:
            name, amount = entry.split(":")
            mapping[name.strip()] = float(amount.strip())
    except ValueError:
        return None
    return mapping

# 格式化團體記帳資料
def format_group_records(group_records):
    formatted = []
    for record in group_records:
        formatted.append(f"{record['date']} - {', '.join([f'{name}: {amount}' for name, amount in record['amounts'].items()])}")
    return "\n".join(formatted)

# 格式化個人記帳資料
def format_personal_records(personal_records):
    formatted = []
    for record in personal_records:
        formatted.append(f"{record['date']} - {record['description']}: {record['amount']}")
    return "\n".join(formatted)

# 獲取當前月份的日期範圍（如：2025/04/01 - 2025/04/30）
def get_current_month_range():
    today = datetime.date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = datetime.date(today.year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
    
    return f"{first_day} - {last_day}"

# 格式化發票品項資料
def format_invoice_items(invoice_items):
    formatted_items = []
    for item in invoice_items:
        formatted_items.append(f"{item['name']}: {item['amount']}")
    return "\n".join(formatted_items)
