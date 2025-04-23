import os
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from sheet_utils import append_record, get_personal_records, delete_record

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    return 'OK'

@app.route("/add_group_record", methods=["POST"])
def add_group_record():
    data = request.json
    record = [
        data.get("item"),
        data.get("amount"),
        ",".join(data.get("participants", [])),
        data.get("date")
    ]
    append_record("group_records", record)
    return jsonify({"message": "Group record added successfully!"}), 200

@app.route("/add_personal_record", methods=["POST"])
def add_personal_record():
    data = request.json
    record = [
        data.get("item"),
        data.get("amount"),
        data.get("name"),
        data.get("date")
    ]
    append_record("personal_records", record)
    return jsonify({"message": "Personal record added successfully!"}), 200

@app.route("/check_personal_records/<name>", methods=["GET"])
def check_personal_records(name):
    records = get_personal_records(name)
    if records:
        return jsonify(records)
    else:
        return jsonify({"error": "No records found for this user"}), 404

@app.route("/delete_personal_record", methods=["POST"])
def delete_personal_record():
    data = request.json
    record_id = data.get("record_id")
    delete_record("personal_records", record_id)
    return jsonify({"message": "Record deleted successfully!"}), 200

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/commands", methods=["GET"])
def list_commands():
    return jsonify({
        "指令列表": [
            "個人記帳 小明 早餐 60",
            "查詢記帳 小明",
            "重設記帳 小明",
            "團體記帳 早餐 小明:60 小美:40",
            "發票記帳 小明:60 小美:40",
            "個人發票記帳 小明",
            "查詢中獎",
            "查詢中獎 小明",
            "查詢中獎 2025/03-04",
            "刪除個人記帳 小明",
            "刪除 1",
            "匯出 小明",
        ]
    })

