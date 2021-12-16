import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from logging import StreamHandler

from exceptions import (HTTPConnectionException,
                        JSONConvertException,
                        JSONContentException,
                        ParsingException)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
logger.setLevel(logging.DEBUG)

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

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logger.error('Не удалось получить ответ от API.')
        raise HTTPConnectionException('Не удалось получить ответ от API.')
    else:
        logger.info('Ответ от API получен.')

    # response.raise_for_status() - не проходит pytest для домашки,
    # может не так его применяю?! оставил пока проверку по коду 200
    if response.status_code != 200:
        logger.error('Ответ от API неверный.')
        raise HTTPConnectionException('Ответ от API неверный.')

    try:
        response = response.json()
    except AttributeError:
        logger.error(
            'Не удалось преобразовать ответ в JSON.'
        )
        raise JSONConvertException(
            'Не удалось преобразовать ответ от API в JSON.'
        )
    else:
        logger.info('Ответ от API преобразован в JSON.')

    return response


def check_response(response):
    """Проверка запроса к API на корректность и извлечение списка домашек."""
    if isinstance(response['homeworks'], list):
        try:
            homeworks = response['homeworks']
        except TypeError:
            logger.error(
                'Не удалось получить домашки из ответа от API.'
            )
            raise JSONContentException(
                'Не удалось получить домашки из ответа от API.'
            )
        else:
            logger.info('Список домашек в ответе от API получен.')
    else:
        logger.error('В ответе от API нет списка домашек.')
        raise JSONContentException(
            'В ответе от API нет списка домашек.'
        )

    if homeworks != [] and not isinstance(homeworks[0], dict):
        logger.error('Содержимое списка домашек некорректно.')
        raise JSONContentException(
            'Содержимое списка домашек некорректно.'
        )

    return homeworks


def parse_status(homework):
    """Получение статуса домашки и формирование сообщения для бота."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except TypeError:  # Почему то pytest в этом месте ругается на KeyError! =о
        logger.error(
            'Не удалось получить имя и/или статус домашки.'
        )
        raise ParsingException(
            'Не удалось получить имя и/или статус домашки.'
        )
    else:
        logger.info('Имя и статус домашки получены.')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logger.error('Статус домашней работы не удалось распознать.')
        raise ParsingException(
            'Статус домашней работы не удалось распознать.'
        )
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


# Пришлось написать отдельную функцию для проверки ошибок
# т.к. flake8 ругался, что main() получилась слишком сложная
def error_processing(bot, current_error, previous_error):
    """Обработка ошибок и отправка сообщения об ошибке в Telegram."""
    if current_error != previous_error:
        send_message(bot, current_error)
        logger.error(current_error)
    else:
        logger.error(
            f'Программа не работает. '
            f'{current_error} всё ещё не устранён.'
        )
    return current_error


def main():
    """Основная логика работы бота."""
    logger.info('--- Старт программы ---------->>>')

    if not check_tokens():
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.info('Связь с ботом установлена.')

    current_timestamp = int(time.time())
    previous_message = ''
    previous_error = ''

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
            except KeyError:
                current_timestamp = int(time.time())
                logger.debug(
                    'Не удалось получить время запроса из ответа от API. '
                    'Для выполнения следующего запроса принято текущее время.'
                )
            else:
                logger.info('Время запроса получено из ответа от API.')

            time.sleep(RETRY_TIME)
            logger.info('--- Новый запрос ------------->>>')

        except Exception as error:
            current_error = f'Сбой в работе программы: "{error}"'
            previous_error = error_processing(
                bot, current_error, previous_error
            )

            time.sleep(RETRY_TIME)
            logger.info('--- Новый запрос ------------->>>')

        else:
            logger.debug(
                'Программа работает. Предыдущий запрос был выполнен успешно.'
            )


if __name__ == '__main__':
    main()
