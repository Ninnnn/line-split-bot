from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 暫存分帳資料（記憶體儲存，重啟會清空）
session_data = []

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if text.startswith("記帳"):
        try:
            msg = text[2:].strip()
            main_part, payer = msg.split("/")
            amount_str, purpose, *members = main_part.strip().split()
            amount = int(amount_str)
            payer = payer.strip()
            purpose = purpose.strip()
            participants = [m.strip() for m in members if m.strip()]
            if not participants or payer not in participants:
                raise ValueError("付款人必須包含在參與者中")

            session_data.append({
                "amount": amount,
                "payer": payer,
                "purpose": purpose,
                "members": participants
            })

            reply_text = (
                f"【記帳成功】\n"
                f"金額：{amount} 元\n"
                f"用途：{purpose}\n"
                f"付款人：{payer}\n"
                f"參與者：{', '.join(participants)}\n\n"
                f"你可以繼續輸入「記帳」或輸入「結算」來計算總表"
            )

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=(
                    "【記帳格式錯誤】\n"
                    "請使用以下格式（用途必填）：\n\n"
                    "記帳 金額 用途 名單 / 付款人\n"
                    "範例：\n"
                    "記帳 600 晚餐 小明 小美 小王 / 小明"
                ))
            )

    elif text == "結算":
        if not session_data:
            reply = "目前沒有任何記帳紀錄，請先輸入「記帳」開始。"
        else:
            paid = {}
            share = {}

            for record in session_data:
                amt = record["amount"]
                payer = record["payer"]
                members = record["members"]
                split = amt / len(members)

                paid[payer] = paid.get(payer, 0) + amt
                for m in members:
                    share[m] = share.get(m, 0) + split

            all_names = sorted(set(paid.keys()) | set(share.keys()))
            lines = ["【分帳結算結果】"]
            lines.append("姓名    實付     應付     差額")
            lines.append("－" * 30)

            for name in all_names:
                actual = paid.get(name, 0)
                should = share.get(name, 0)
                diff = actual - should
                if diff > 0:
                    status = f"+{diff:.0f}（多付）"
                elif diff < 0:
                    status = f"{diff:.0f}（需補）"
                else:
                    status = "0（剛好）"

                lines.append(f"{name:<6} {actual:>5.0f}元   {should:>5.0f}元   {status}")

            reply = "\n".join(lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    elif text in ["重設", "重啟"]:
        session_data.clear()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="【已清空】\n所有記帳資料已重設，可重新開始記帳。")
        )

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=(
                "【指令說明】\n"
                "你可以使用以下指令：\n\n"
                "1. 記帳 金額 用途 名單 / 付款人\n"
                "   例如：記帳 600 晚餐 小明 小美 / 小明\n\n"
                "2. 結算（統計誰多付、誰該補）\n"
                "3. 重設 或 重啟（清空所有記帳資料）"
            ))
        )
