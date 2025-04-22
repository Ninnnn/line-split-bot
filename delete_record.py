def delete_personal_record(user_name, record_id):
    records = get_personal_records(user_name)
    if 0 < record_id <= len(records):
        record = records[record_id - 1]
        delete_record('personal_records', record['id'])

def delete_group_record(group_name, record_id):
    records = get_group_records(group_name)
    if 0 < record_id <= len(records):
        record = records[record_id - 1]
        delete_record('group_records', record['id'])
