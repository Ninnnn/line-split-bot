# commands.py
from features.command_guide import get_command_guide
from features.personal_record import handle_personal_command
from features.group_record import handle_group_command
from features.invoice_record import handle_invoice_command
from features.deletion import handle_delete_command
from features.export_excel import handle_export_command
from features.prize_check import handle_prize_check_command

def process_command(user_id, message):
    # 指令導覽
    if message.startswith("指令") or message.lower().startswith("help"):
        return get_command_guide()

    # 個人記帳
    if message.startswith("個人記帳"):
        return handle_personal_command(user_id, message)

    # 團體記帳
    if message.startswith("團體記帳"):
        return handle_group_command(user_id, message)

    # 個人發票記帳 or 團體發票記帳
    if message.startswith("個人發票記帳") or message.startswith("發票記帳"):
        return handle_invoice_command(user_id, message)

    # 查詢中獎
    if message.startswith("查詢中獎"):
        return handle_prize_check_command(user_id, message)

    # 匯出 Excel
    if message.startswith("匯出"):
        return handle_export_command(user_id, message)

    # 刪除記錄流程
    if message.startswith("刪除"):
        return handle_delete_command(user_id, message)

    # 無法辨識的指令
    return "無法辨識的指令，請輸入「指令」查看使用說明。"
