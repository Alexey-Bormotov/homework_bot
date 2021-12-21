import json
import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from logging import StreamHandler

from exceptions import (HTTPConnectionError,
                        JSONConvertError,
                        JSONContentError,
                        ParsingError)

from telegram_handler import TelegramHandler

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
logger.setLevel(logging.DEBUG)

rf_handler = RotatingFileHandler(
    'homework_bot.log',
    maxBytes=50_000,
    backupCount=1
)
rf_handler.setLevel(logging.DEBUG)
rf_handler.setFormatter(formatter)
logger.addHandler(rf_handler)

s_handler = StreamHandler(sys.stdout)
s_handler.setLevel(logging.DEBUG)
s_handler.setFormatter(formatter)
logger.addHandler(s_handler)


RETRY_TIME = 60 * 10
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

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise HTTPConnectionError('Не удалось получить ответ от API.')
    else:
        logger.info('Ответ от API получен.')

    if response.status_code != 200:
        raise HTTPConnectionError('Ответ от API не верный.')

    try:
        response = response.json()
    except json.decoder.JSONDecodeError:
        raise JSONConvertError('Не удалось преобразовать ответ от API в JSON.')
    else:
        logger.info('Ответ от API преобразован в JSON.')

    return response


def check_response(response):
    """Проверка запроса к API на корректность и извлечение списка домашек."""
    if not isinstance(response['homeworks'], list):
        logger.error('В ответе от API нет списка домашек.')
        raise JSONContentError('В ответе от API нет списка домашек.')

    try:
        homeworks = response['homeworks']
    except TypeError:
        raise JSONContentError('Не удалось получить домашки из ответа от API.')
    else:
        logger.info('Список домашек в ответе от API получен.')

    if homeworks and not isinstance(homeworks[0], dict):
        raise JSONContentError('Содержимое списка домашек некорректно.')

    return homeworks


def parse_status(homework):
    """Получение статуса домашки и формирование сообщения для бота."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except TypeError:
        raise ParsingError('Не удалось получить имя и/или статус домашки.')
    else:
        logger.info('Имя и статус домашки получены.')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        raise ParsingError('Статус домашней работы не удалось распознать.')
    else:
        logger.info('Статус домашней работы распознан.')

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
    logger.info('--- Старт программы ---------->>>')

    if not check_tokens():
        exit()

    current_timestamp = int(time.time())
    previous_message = None

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.info('Связь с ботом установлена.')
    t_handler = TelegramHandler(bot, TELEGRAM_CHAT_ID)
    t_handler.setLevel(logging.ERROR)
    t_handler.setFormatter(formatter)
    logger.addHandler(t_handler)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
            else:
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
            except KeyError:
                current_timestamp = int(time.time())
                logger.debug(
                    'Не удалось получить время запроса из ответа от API. '
                    'Для выполнения следующего запроса принято текущее время.'
                )
            else:
                logger.info('Время запроса получено из ответа от API.')

            time.sleep(RETRY_TIME)
            logger.debug(
                'Программа работает. Предыдущий запрос был выполнен успешно.'
            )

        except Exception as error:
            current_error = f'Сбой в работе программы: "{error}"'
            logger.error(current_error)

            time.sleep(RETRY_TIME)

        finally:
            logger.info('--- Новый запрос ------------->>>')


if __name__ == '__main__':
    main()
