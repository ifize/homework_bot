import logging
import os

import requests

import telegram
import time
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("logger.log", maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s : [%(levelname)s] [%(lineno)d] : %(message)s"
)

handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logger.error(f'Бот не отправил сообщение "{message}" из-за {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        error_message = (
            f'Сбой запроса к эндпоинту статус {homework_statuses.status_code}'
        )
        send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)
        logger.error(error_message)
        raise Exception
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response["homeworks"]) != list:
        error_message = "Неверный тип данных"
        logger.error(error_message)
        send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)
    else:
        try:
            response["homeworks"]
            return response["homeworks"]
        except Exception:
            if not response["homeworks"]:
                error_message = "Пришел пустой словарь"
                logger.error(error_message)
                send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)
            else:
                error_message = "Отсутствуют ожидаемые ключи в ответе API"
                logger.error(error_message)
                send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)


def parse_status(homework):
    """Проверяет статус домашней работы."""
    homework_name = homework["homework_name"]
    homework_status = homework["status"]
    if homework_status not in HOMEWORK_STATUSES:
        error_message = "Недокументированный статус домашней работы"
        logger.error(error_message)
        send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)
        raise Exception
    else:
        try:
            verdict = HOMEWORK_STATUSES[homework_status]
            return f'Изменился статус проверки "{homework_name}". {verdict}'
        except Exception:
            error_message = "В ответе API неопределён статус домашней работы"
            logger.error(error_message)
            send_message(telegram.Bot(token=TELEGRAM_TOKEN), error_message)


def check_tokens():
    """Проверяет наличие обязательных переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        logger.critical("Отсутствует обязательная переменная окружения")
        return False


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            current_timestamp = response.get("current_date")
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == "__main__":
    main()
