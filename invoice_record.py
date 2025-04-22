def log_invoice_to_personal_record(user_name, invoice_data, amount):
    record = [user_name, datetime.now().strftime('%Y/%m/%d'), '發票記帳', amount, invoice_data]
    append_record('personal_records', record)

def log_invoice_to_group_record(invoice_data, amount, users):
    for user in users:
        record = [user, datetime.now().strftime('%Y/%m/%d'), '發票記帳', amount, invoice_data]
        append_record('group_records', record)
