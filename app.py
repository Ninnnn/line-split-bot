from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 分帳與個人記帳資料（記憶體儲存）
session_data = []
personal_data = {}

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

    # --- 團體記帳 ---
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

        except:
            reply_text = (
                "【記帳格式錯誤】\n"
                "請使用：\n記帳 金額 用途 名單 / 付款人\n"
                "範例：\n記帳 500 晚餐 小明 小美 / 小明"
            )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    # --- 團體結算 ---
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

            record_lines = ["【所有消費記錄】"]
            for i, record in enumerate(session_data, start=1):
                line = (
                    f"{i}. {record['amount']} 元（{record['purpose']}）"
                    f"由 {record['payer']} 付款，參與：{', '.join(record['members'])}"
                )
                record_lines.append(line)

            summary_lines = ["【金錢統計】", "姓名    實付     應付     差額", "－" * 30]
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
                summary_lines.append(f"{name:<6} {actual:>5.0f}元   {should:>5.0f}元   {status}")

            reply = "\n".join(["【分帳結算結果】", ""] + record_lines + [""] + summary_lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 重設全部資料 ---
    elif text in ["重設", "重啟"]:
        session_data.clear()
        personal_data.clear()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="【已清空】\n所有記帳資料已重設，可重新開始記帳。"))

    # --- 個人記帳 ---
    elif text.startswith("個人記帳"):
        try:
            msg = text[4:].strip()
            main_part, person = msg.split("/")
            amount_str, purpose = main_part.strip().split(maxsplit=1)
            amount = int(amount_str)
            person = person.strip()
            purpose = purpose.strip()
            date_str = datetime.now().strftime("%Y/%m/%d")

            if person not in personal_data:
                personal_data[person] = []

            personal_data[person].append({
                "date": date_str,
                "amount": amount,
                "purpose": purpose
            })

            reply = (
                f"【個人記帳成功】\n"
                f"{person} 登記了 {amount} 元（{purpose}）\n"
                f"日期：{date_str}"
            )

        except:
            reply = (
                "【個人記帳格式錯誤】\n"
                "請使用：\n個人記帳 金額 用途 / 姓名\n"
                "範例：\n個人記帳 150 早餐 / 小明"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 查詢個人記帳 ---
    elif text.startswith("查詢個人"):
        name = text[5:].strip()
        today = datetime.now().strftime("%Y/%m/%d")
        records = personal_data.get(name)

        if not records:
            reply = f"【查詢日期】：{today}\n{name} 尚未有個人記帳紀錄。"
        else:
            total = sum(r["amount"] for r in records)
            lines = [f"【查詢日期】：{today}", f"【{name}的個人記帳紀錄】"]
            for i, r in enumerate(records, start=1):
                lines.append(f"{i}. {r['date']} {r['purpose']} {r['amount']} 元")
            lines.append(f"\n總消費：{total} 元")
            reply = "\n".join(lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 重設個人記帳 ---
    elif text.startswith("重設個人"):
        name = text[5:].strip()
        if name in personal_data:
            del personal_data[name]
            reply = f"【個人記帳清除成功】\n已清空 {name} 的所有個人記帳紀錄。"
        else:
            reply = f"{name} 尚無個人記帳資料，無需清除。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 指令說明 ---
    else:
        reply = (
            "【指令說明】\n"
            "● 記帳 金額 用途 名單 / 付款人\n"
            "  例：記帳 300 晚餐 小明 小美 / 小明\n"
            "● 結算：統計所有人分帳結果\n"
            "● 重設：清空所有資料\n\n"
            "【個人記帳】\n"
            "● 個人記帳 金額 用途 / 姓名\n"
            "  例：個人記帳 150 早餐 / 小明\n"
            "● 查詢個人 姓名\n"
            "  例：查詢個人 小明\n"
            "● 重設個人 姓名\n"
            "  例：重設個人 小明"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
