import nest_asyncio  # <-- Добавлено
nest_asyncio.apply()  # <-- Добавлено

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from datetime import datetime
import gspread

# ========== НАСТРОЙКИ ========== #
TELEGRAM_TOKEN = "7945532914:AAEeZjJAs3iWxynhjgvMBOiKkBdxAuzB2c8"
GOOGLE_CREDS_FILE = "dogwood-cinema-457117-a2-43d4cd6fd399.json"
GOOGLE_SHEET_NAME = "Пищевой дневник"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
# =============================== #

# Инициализация Google Sheets
client = gspread.service_account(filename=GOOGLE_CREDS_FILE, scopes=SCOPES)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

# Состояния диалога
CHOOSING_COLUMN = 1

COLUMNS = [
    "дата", "ощущения", "перекус", "ощущения", "ощущения",
    "завтрак", "ощущения", "ощущения", "перекус", "ощущения",
    "ощущения", "обед", "ощущения", "ощущения", "перекус",
    "ощущения", "ощущения", "ужин", "ощущения"
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)

def find_or_create_today_row():
    """Ищет или создает строку для сегодняшней даты"""
    today = datetime.now().strftime("%d.%m.%Y")
    try:
        records = sheet.get_all_values()

        for i, row in enumerate(records[1:], start=2):
            if i % 2 == 0 and row[0] == today:
                return i

        new_row = len(records) + 2 if len(records) % 2 else len(records) + 1
        sheet.update_cell(new_row, 1, today)
        return new_row

    except Exception as e:
        logging.error(f"Ошибка при работе с таблицей: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍏 Привет! Я твой пищевой ассистент.\n"
        "Просто напиши мне что ты съел/сделал, а я помогу записать это в дневник!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data = context.user_data
        user_data["message"] = update.message.text.strip()
        user_data["current_row"] = find_or_create_today_row()

        columns_menu = "\n".join([f"{idx+1:>2}. {name}" for idx, name in enumerate(COLUMNS)])

        await update.message.reply_text(
            f"📌 Выбери куда записать:\n\n{columns_menu}\n\nОтправь номер столбца (1-19):"
        )
        return CHOOSING_COLUMN

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("😢 Что-то пошло не так. Попробуй позже.")
        return ConversationHandler.END

async def choose_column(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    try:
        choice = int(update.message.text)
        if 1 <= choice <= 19:
            sheet.update_cell(user_data["current_row"], choice, user_data["message"])
            time_str = update.message.date.astimezone().strftime("%H:%M")
            sheet.update_cell(user_data["current_row"] + 1, choice, f"🕒 {time_str}")

            await update.message.reply_text(
                f"✅ Записано в столбец {choice}!\n"
                f"Текст: {user_data['message']}\n"
                f"Время: {time_str}"
            )
        else:
            await update.message.reply_text("❌ Некорректный номер! Введи от 1 до 19")

    except ValueError:
        await update.message.reply_text("🔢 Нужно отправить только число!")
    except Exception as e:
        logging.error(f"Ошибка записи: {e}")
        await update.message.reply_text("🚨 Ошибка записи в таблицу!")

    finally:
        return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={CHOOSING_COLUMN: [MessageHandler(filters.TEXT, choose_column)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    logging.info("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()