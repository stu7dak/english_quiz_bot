import logging
import datetime
import json
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from config import BOT_TOKEN, SHEET_NAME, GOOGLE_CREDENTIALS_FILE, MAX_ATTEMPTS
from topics import TOPICS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём файл credentials.json из переменной окружения
import os
if os.environ.get('GOOGLE_CREDENTIALS'):
    with open('credentials.json', 'w') as f:
        f.write(os.environ.get('GOOGLE_CREDENTIALS'))

# Инициализация Google Sheets
def get_google_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Quiz_Statistics").worksheet(SHEET_NAME) # Убедитесь, что имя таблицы совпадает
        return sheet
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

# Хранилище данных пользователей в памяти (user_id -> данные)
user_data_store = {}

def get_user_data(user_id):
    if user_id not in user_data_store:
        user_data_store[user_id] = {"attempts": 0, "current_topic": None, "score": 0, "q_index": 0, "start_time": None}
    return user_data_store[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = []
    for topic_key, topic_data in TOPICS.items():
        keyboard.append([InlineKeyboardButton(topic_data["title"], callback_data=f"start_{topic_key}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nВыберите тему для прохождения теста.\n"
        f"У вас есть максимум {MAX_ATTEMPTS} попыток.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user_data = get_user_data(user_id)

    # Начало теста
    if data.startswith("start_"):
        topic_key = data.split("start_")[1]
        if user_data["attempts"] >= MAX_ATTEMPTS:
            await query.edit_message_text("Вы исчерпали лимит попыток (3). Обратитесь к преподавателю.")
            return

        user_data["current_topic"] = topic_key
        user_data["score"] = 0
        user_data["q_index"] = 0
        user_data["start_time"] = datetime.datetime.now()
        user_data["attempts"] += 1
        
        await send_question(query, user_id)

    # Ответ на вопрос
    elif data.startswith("ans_"):
        answer = data.split("ans_")[1]
        topic_key = user_data["current_topic"]
        q_index = user_data["q_index"]
        question = TOPICS[topic_key]["questions"][q_index]

        if answer == question["correct"]:
            user_data["score"] += 1

        user_data["q_index"] += 1
        if user_data["q_index"] < len(TOPICS[topic_key]["questions"]):
            await send_question(query, user_id)
        else:
            await finish_test(query, user_id)

async def send_question(query, user_id):
    user_data = get_user_data(user_id)
    topic_key = user_data["current_topic"]
    q_index = user_data["q_index"]
    question = TOPICS[topic_key]["questions"][q_index]

    keyboard = []
    for option in question["options"]:
        keyboard.append([InlineKeyboardButton(option, callback_data=f"ans_{option}")])

    await query.edit_message_text(
        f"Вопрос {q_index + 1} из {len(TOPICS[topic_key]['questions'])}\n\n{question['text']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finish_test(query, user_id):
    user_data = get_user_data(user_id)
    topic_key = user_data["current_topic"]
    topic_title = TOPICS[topic_key]["title"]
    total_questions = len(TOPICS[topic_key]["questions"])
    score = user_data["score"]
    
    end_time = datetime.datetime.now()
    start_time = user_data["start_time"]
    duration = (end_time - start_time).total_seconds() / 60  # в минутах

    # Сохранение в Google Таблицу
    sheet = get_google_sheet()
    if sheet:
        try:
            sheet.append_row([
                query.from_user.first_name,
                f"@{query.from_user.username}" if query.from_user.username else "Нет",
                topic_title,
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(duration, 2),
                f"{score}/{total_questions}",
                user_data["attempts"]
            ])
            logger.info("Данные успешно сохранены в Google Таблицу")
        except Exception as e:
            logger.error(f"Ошибка записи в таблицу: {e}")
            await query.edit_message_text("Тест завершен, но произошла ошибка при сохранении статистики.")
            return

    # Очистка данных пользователя для нового теста (но попытки сохраняются)
    user_data["current_topic"] = None
    user_data["q_index"] = 0
    user_data["score"] = 0

    attempts_left = MAX_ATTEMPTS - user_data["attempts"]
    msg = (
        f"🎉 Тест завершен!\n\n"
        f"Тема: {topic_title}\n"
        f"Ваш результат: {score} из {total_questions} правильных ответов.\n"
        f"Время прохождения: {round(duration, 1)} мин.\n"
        f"Осталось попыток: {attempts_left}"
    )
    
    keyboard = []
    if attempts_left > 0:
        keyboard.append([InlineKeyboardButton("Пройти другой тест", callback_data="restart")])
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)

async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))

    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
    main()
