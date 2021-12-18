from logging import StreamHandler

import telegram


class TelegramHandler(StreamHandler):
    def __init__(self, token, chat_id):
        StreamHandler.__init__(self)
        self.token = token
        self.chat_id = chat_id
        self.bot = telegram.Bot(token=self.token)

    def emit(self, record):
        message = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=message)
