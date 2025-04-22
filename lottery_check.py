def check_lottery(invoice_number):
    # Placeholder for lottery checking logic
    winning_numbers = ["123456789", "987654321"]  # Example winning numbers
    if invoice_number in winning_numbers:
        return f"發票號碼 {invoice_number} 中獎了！"
    else:
        return f"發票號碼 {invoice_number} 沒有中獎。"
