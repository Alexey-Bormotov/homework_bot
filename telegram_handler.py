from logging import Handler

import telegram


class TelegramHandler(Handler):
    def __init__(self, token, chat_id):
        Handler.__init__(self)
        self.token = token
        self.chat_id = chat_id

    def init_bot(self):
        self.bot = telegram.Bot(token=self.token)

    def emit(self, record):
        self.init_bot()
        message = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=message)
