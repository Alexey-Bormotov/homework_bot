from logging import Handler


class TelegramHandler(Handler):
    def __init__(self, bot, chat_id):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id
        self.previous_error = None

    def emit(self, record):
        message = self.format(record)
        current_error = record.message

        if current_error != self.previous_error:
            self.bot.send_message(chat_id=self.chat_id, text=message)
            self.previous_error = current_error
