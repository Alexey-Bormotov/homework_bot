import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from logging import StreamHandler


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
logger.setLevel(logging.DEBUG)  # Надо ли???
# Использую сразу два хэндлера ради интереса
# Если какой то не нужен, могу убрать)
rf_handler = RotatingFileHandler(
    'homework_bot.log',
    maxBytes=50000,
    backupCount=1
)
rf_handler.setLevel(logging.DEBUG)
rf_handler.setFormatter(formatter)
logger.addHandler(rf_handler)

s_handler = StreamHandler(sys.stdout)
s_handler.setLevel(logging.DEBUG)
s_handler.setFormatter(formatter)
logger.addHandler(s_handler)


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сформированного сообщения в Telegram с помощью бота."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info('Бот успешно отправил сообщение в Telegram.')
    except Exception as error:
        logger.error(
            f'Боту не удалось отправить сообщение в Telegram. {error}'
        )


def get_api_answer(current_timestamp):
    """Запрос домашек у API Яндекс.Практикума и преобразование в JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)

    if response.status_code != 200:
        logger.error('Ответ от API неверный, либо API не отвечает.')
        raise Exception('Ответ от API неверный, либо API не отвечает.')

    logger.info('Ответ от API получен.')

    return response.json()


def check_response(response):
    """Проверка запроса к API на корректность и извлечение списка домашек."""
    if isinstance(response['homeworks'], list):
        try:
            homeworks = response['homeworks']
            logger.info('Список домашек в ответе от API получен.')
        except TypeError:
            logger.error(
                'Не удалось получить список домашек из ответа от API.'
            )

        return homeworks


def parse_status(homework):
    """Получение статуса домашки и формирование сообщения для бота."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        logger.info('Статус домашки из ответа API получен.')
    except TypeError:
        logger.error('Не удалось получить статус домашки из ответа API.')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.info('Статус домашней работы распознан.')
    except TypeError:
        logger.error('Статус домашней работы не удалось распознать.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    ENV_VARS = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID',
    }

    for env_var, name in ENV_VARS.items():
        if env_var is None:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: \'{name}\'. '
                f'Программа принудительно остановлена.'
            )
            return False

    logger.info('Проверка переменных окружения пройдена успешно.')
    return True


def main():
    """Основная логика работы бота."""
    logger.info('---------------------------------')
    logger.info('Запуск программы бота-ассистента.')
    if not check_tokens():
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.info('Связь с ботом установлена.')

    current_timestamp = 1
    previous_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            try:
                message = parse_status(homeworks[0])
            except IndexError:
                message = 'Обновлений по домашке нет.'
                logger.debug('Обновлений по домашке нет.')

            if message != previous_message:
                logger.info('Сформировано новое сообщение.')
                send_message(bot, message)
                previous_message = message
            else:
                logger.info('Нет нового сообщения.')

            try:
                current_timestamp = response['current_date']
                logger.info('Время запроса получено из ответа API.')
            except TypeError:
                logger.error(
                    'Не удалось получить время запроса из ответа API.'
                )

            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(f'Сбой в работе программы: {error}')

            time.sleep(RETRY_TIME)
        else:
            logger.info('---')
            logger.info('Программа работает. Отправка нового запроса к API.')


if __name__ == '__main__':
    main()
