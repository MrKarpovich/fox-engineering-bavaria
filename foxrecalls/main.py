import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# === Настройка ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("🚫 TELEGRAM_BOT_TOKEN не найден в .env")

SCRIPT_DIR = Path(__file__).parent
USERS_FILE = SCRIPT_DIR / "users.json"
CODES_FILE = SCRIPT_DIR / "defect-code-info.txt"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoxBMW")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === Языки ===
MESSAGES = {
    "en": {
        "start_text": (
            "👋 Welcome! You can check your BMW by VIN using the buttons below.\n\n"
            "After checking, send the received codes here in this format:\n"
            "`0011200700, 0011350700`"
        ),
        "language_menu": "🌍 Current language: English\n🔄 Choose language:",
        "language_changed": "✅ Language changed to English.",
        "results": "🔍 Results:",
        "not_found": "❌ Not found",
        "buttons": {
            "language": "🌐 Language",
            "back": "🔙 Back"
        }
    },
    "ru": {
        "start_text": (
            "👋 Добро пожаловать! Вы можете проверить свой BMW по VIN через кнопки ниже.\n\n"
            "После проверки отправьте полученные цифры сюда в таком формате:\n"
            "`0011200700, 0011350700`"
        ),
        "language_menu": "🌍 Текущий язык: Русский\n🔄 Выберите язык:",
        "language_changed": "✅ Язык изменён на русский.",
        "results": "🔍 Результаты:",
        "not_found": "❌ Не найден",
        "buttons": {
            "language": "🌐 Язык",
            "back": "🔙 Назад"
        }
    }
}


# === Безопасное управление пользователями ===
def safe_load_json(file_path: Path) -> Dict[str, Any]:
    """Безопасная загрузка JSON с восстановлением структуры."""
    if not file_path.exists():
        return {"next_user_id": 1, "users": {}}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {"next_user_id": 1, "users": {}}
            data.setdefault("users", {})
            data.setdefault("next_user_id", 1)
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"⚠️ Ошибка загрузки {file_path.name}: {e}. Создаём новый.")
        return {"next_user_id": 1, "users": {}}


def save_users(data: Dict[str, Any]):
    """Сохранение пользователей в файл."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения users.json: {e}")


def get_or_create_user(
    user_id: int,
    first_name: Optional[str] = None,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """Получает или создаёт пользователя."""
    data = safe_load_json(USERS_FILE)
    user_key = str(user_id)

    if user_key not in data["users"]:
        internal_id = data["next_user_id"]
        safe_first_name = (first_name or "Anonymous")[:100]
        safe_username = (username or "")[:100]

        data["users"][user_key] = {
            "internal_id": internal_id,
            "language": "en",
            "first_name": safe_first_name,
            "username": safe_username,
            "user_id": user_id,
            "created_at": str(int(time.time()))
        }
        data["next_user_id"] += 1
        save_users(data)
        logger.info(f"🆕 Новый пользователь: {user_id} → ID #{internal_id}")

    return data["users"][user_key]


def set_user_language(user_id: int, lang: str):
    """Меняет язык пользователя."""
    data = safe_load_json(USERS_FILE)
    user_key = str(user_id)
    if user_key in data["users"]:
        data["users"][user_key]["language"] = lang
        save_users(data)


# === Загрузка кодов дефектов ===
def load_defect_codes() -> Dict[str, str]:
    """Загружает коды из твоего формата файла."""
    if not CODES_FILE.exists():
        logger.warning(f"⚠️ Файл {CODES_FILE.name} не найден.")
        return {}
    try:
        with open(CODES_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r"'([^']+)':\s*{\s*defectCodeDescription:\s*'([^']+)'", content)
        codes = {key.strip(): desc.strip() for key, desc in matches}
        logger.info(f"✅ Загружено {len(codes)} кодов дефектов.")
        return codes
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга {CODES_FILE.name}: {e}")
        return {}


DEFECT_CODES = load_defect_codes()


# === Клавиатуры ===
def get_vin_check_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🇪🇺 Проверить VIN Европа",
        url="https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html"
    )
    builder.button(
        text="🇺🇸 Проверить VIN США",
        url="https://www.bmwusa.com/safety-and-emission-recalls.html"
    )
    builder.button(
        text=MESSAGES[lang]["buttons"]["language"],
        callback_data="choose_language"
    )
    builder.button(
        text=MESSAGES[lang]["buttons"]["back"],
        callback_data="back_to_start"
    )
    builder.adjust(2, 1, 1)  # 2 кнопки, потом "Язык", потом "Назад"
    return builder.as_markup()


def get_language_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    other_lang = "ru" if current_lang == "en" else "en"
    flag = "🇷🇺" if other_lang == "ru" else "🇬🇧"
    label = "Русский" if other_lang == "ru" else "English"
    builder.button(text=f"{flag} {label}", callback_data=f"set_lang_{other_lang}")
    builder.button(text=MESSAGES[current_lang]["buttons"]["back"], callback_data="back_to_start")
    builder.adjust(1, 1)
    return builder.as_markup()


# === Обработчики ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = get_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    lang = user["language"]
    await message.answer(
        MESSAGES[lang]["start_text"],
        parse_mode="Markdown",
        reply_markup=get_vin_check_keyboard(lang),
        disable_web_page_preview=True
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    user = get_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    lang = user["language"]

    if lang == "en":
        help_text = (
            "ℹ️ <b>How to use?</b>\n\n"
            "1️⃣ Use the buttons below to open the official BMW service pages\n"
            "2️⃣ Enter your VIN on the selected page to check for active service actions.\n"
            "3️⃣ If you receive code(s) (e.g. <code>0011200700</code>), send them here.\n"
            "   ✅ Format: <code>0011200700</code> or <code>0011200700, 0011350700</code>\n"
            "4️⃣ Get a description of the technical action\n\n"
            "🦊 <b>Questions or suggestions?</b>\n"
            "→ I’m always open to talk: @JluceHok_u3_MuHcka"
        )
    else:  # ru
        help_text = (
            "ℹ️ <b>Как пользоваться?</b>\n\n"
            "1️⃣ Используйте кнопки ниже, чтобы перейти на официальные страницы BMW\n"
            "2️⃣ Введите VIN на выбранной странице, чтобы узнать о текущих сервисных акциях.\n"
            "3️⃣ Если вы получили код(ы) (например, <code>0011200700</code>), отправьте их сюда.\n"
            "   ✅ Формат: <code>0011200700</code> или <code>0011200700, 0011350700</code>\n"
            "4️⃣ Получите описание технической акции\n\n"
            "🦊 <b>Есть вопросы или идеи?</b>\n"
            "→ Всегда рад пообщаться: @JluceHok_u3_MuHcka"
        )

    await message.answer(
        help_text,
        parse_mode="HTML",
        reply_markup=get_vin_check_keyboard(lang),
        disable_web_page_preview=True
    )


@dp.callback_query(F.data == "choose_language")
async def cb_choose_language(callback: CallbackQuery):
    user = get_or_create_user(
        user_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username
    )
    lang = user["language"]
    await callback.message.edit_text(
        MESSAGES[lang]["language_menu"],
        reply_markup=get_language_keyboard(lang),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("set_lang_"))
async def cb_set_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[-1]
    if lang_code in ("en", "ru"):
        set_user_language(callback.from_user.id, lang_code)
        # Обновляем данные пользователя
        user = get_or_create_user(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username
        )
        lang = user["language"]
        await callback.message.edit_text(
            MESSAGES[lang]["language_changed"],
            reply_markup=get_vin_check_keyboard(lang)
        )
    await callback.answer()


@dp.callback_query(F.data == "back_to_start")
async def cb_back_to_start(callback: CallbackQuery):
    user = get_or_create_user(
        user_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username
    )
    lang = user["language"]
    await callback.message.edit_text(
        MESSAGES[lang]["start_text"],
        parse_mode="Markdown",
        reply_markup=get_vin_check_keyboard(lang),
        disable_web_page_preview=True
    )


# === Обработка кодов ===
@dp.message(F.text)
async def handle_defect_code(message: Message):
    user = get_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    lang = user["language"]
    text = message.text.strip()
    if not text:
        return

    codes = [c.strip() for c in text.split(",") if c.strip()]
    if not codes:
        return

    results = []
    for code in codes:
        desc = DEFECT_CODES.get(code, MESSAGES[lang]["not_found"])
        results.append(f"{code}: {desc}")

    response = f"{MESSAGES[lang]['results']}\n" + "\n".join(results)
    await message.answer(response)


# === Запуск ===
async def main():
    logger.info("🚀 Бот запущен. Поддержка: t.me/JluceHok_u3_MuHcka")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
