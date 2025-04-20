@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_name = event.source.display_name  # 获取用户的显示名称
    msg = event.message.text.strip()

    if msg.startswith("個人記帳 "):
        try:
            parts = msg.split()
            amount = int(parts[1])
            note = parts[2] if len(parts) > 2 else ""
            date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")

            # 儲存個人記錄
            if user_id not in personal_records:
                personal_records[user_id] = []
            personal_records[user_id].append({
                'amount': amount,
                'note': note,
                'date': date
            })

            # 寫入 Google Sheet
            try:
                append_personal_record(user_id, user_name, amount, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（個人）:", e)

            msg = f"已記錄：{amount} 元，備註：{note}，消費日：{date}"

        except Exception as e:
            msg = "格式錯誤！請使用：個人記帳 金額 備註 日期(選填)"

    elif msg == "查詢個人":
        if not msg.split()[1:]:
            msg = "查詢個人後請指定查詢的對象，例：查詢個人 寧"
        else:
            name = msg.split()[1]
            records = get_personal_records_by_user(name)
            total = sum([r['amount'] for r in records])
            detail = "\n".join([f"{r['date']}: {r['amount']} 元 - {r['note']}" for r in records])
            msg = f"【個人記帳查詢】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"
    
    elif msg == "重設個人":
        if not msg.split()[1:]:
            msg = "重設個人後請指定重設的對象，例：重設個人 寧"
        else:
            name = msg.split()[1]
            reset_personal_record_by_name(name)
            msg = f"{name}的個人記帳資料已重設"

    else:
        msg = "請輸入指令，例如：\n- 記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 查帳\n- 個人記帳 150 便當 2025-04-20\n- 查詢個人 寧\n- 重設個人 寧\n- 重啟（清除團體資料）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )
