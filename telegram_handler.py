from logging import Handler


class TelegramHandler(Handler):
    def __init__(self, bot, chat_id):
        Handler.__init__(self)
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record):
        message = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=message)
