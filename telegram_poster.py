import requests

class TelegramPoster:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            resp = requests.post(url, json=payload)
            if resp.ok:
                return True
            else:
                print(f"Telegram API Error: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"Telegram Request Exception: {e}")
            return False