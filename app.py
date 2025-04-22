import os
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from sheet_utils import append_record, get_personal_records_by_user, reset_personal_record_by_name

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化 LINE Bot API 和 WebhookHandler
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 設定 Webhook 路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    return 'OK'

# 範例：查詢個人記帳
@app.route("/check_personal_records/<name>", methods=["GET"])
def check_personal_records(name):
    records = get_personal_records_by_user(name)
    if records:
        return jsonify(records)
    else:
        return jsonify({"error": "No records found for this user"}), 404

# 範例：新增團體記帳
@app.route("/add_group_record", methods=["POST"])
def add_group_record():
    data = request.json
    record = {
        "item": data.get("item"),
        "amount": data.get("amount"),
        "participants": data.get("participants"),
        "date": data.get("date")
    }
    append_record('group_records', record)  # 使用 'group_records' 作為工作表名稱
    return jsonify({"message": "Group record added successfully!"}), 200

# 範例：新增個人記帳
@app.route("/add_personal_record", methods=["POST"])
def add_personal_record():
    data = request.json
    record = {
        "item": data.get("item"),
        "amount": data.get("amount"),
        "name": data.get("name"),
        "date": data.get("date")
    }
    append_record('personal_records', record)  # 使用 'personal_records' 作為工作表名稱
    return jsonify({"message": "Personal record added successfully!"}), 200

# 當作 WSGI 應用運行
if __name__ == "__main__":
    app.run(debug=True)
