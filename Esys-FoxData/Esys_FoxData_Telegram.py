"""
E-Sys FoxData — Admin GUI + Telegram bot (aiogram 3.22, PyQt6)
Features:
 - Admin GUI (PyQt6) to set psdzdata_root, index_json, output_base and telegram token
 - Generate index (scan) with progress
 - Bot: inline buttons, typing action, progress updates, logging
 - Per-user personal folders: output_base/<user_id>/...
 - Uses admin index_json (optionally user can upload personal JSON)
"""

import os
import sys
import json
import re
import shutil
import zipfile
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any

import asyncio

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QMessageBox, QProgressBar, QStackedWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, pyqtSignal, QObject

# aiogram imports (3.22)
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ----------------------------
# Logging
# ----------------------------
LOG_FILE = "foxdata.log"
logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)


def log_info(msg: str):
    logging.info(msg)
    print(msg)


def log_error(msg: str):
    logging.error(msg)
    print("ERROR:", msg)


# ----------------------------
# Constants / Limits
# ----------------------------
DB_PATH = Path("foxdata_db.json")
MAX_ARCHIVE_SIZE = 800 * 1024 * 1024  # 800 MB
MAX_SINGLE_FILE_SIZE = 1450 * 1024 * 1024  # 1450 MB
LARGE_FILE_THRESHOLD = 999 * 1024 * 1024  # 999 MB
MAX_ARCHIVE_SIZE_MB = int(MAX_ARCHIVE_SIZE / (1024 ** 2))


# ----------------------------
# Utility functions
# ----------------------------
def load_db() -> Dict[str, Any]:
    if DB_PATH.exists():
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"psdzdata_root": "", "index_json": "", "output_base": "", "telegram_token": "", "requests": {}}


def save_db(d: Dict[str, Any]):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def safe_hash_file(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def scan_psdz_folder_with_warning(folder_path: Path, progress_callback=None) -> Dict[str, dict]:
    folder_path = folder_path.resolve()
    data = {}
    files = [f for f in folder_path.rglob('*') if f.is_file()]
    total = len(files)
    for i, full_path in enumerate(files, 1):
        try:
            rel_path = full_path.relative_to(folder_path).as_posix()
            size = full_path.stat().st_size
            file_hash = safe_hash_file(full_path)
            data[rel_path] = {"size": size, "hash": file_hash}
            if progress_callback:
                progress_callback(i, total)
        except (OSError, ValueError, PermissionError):
            continue
    return data


def atomic_save_json(data: dict, path: Path):
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp.replace(path)


def extract_search_tokens(query: str):
    parts = query.strip().lower().split('_')
    if len(parts) < 5:
        return None, None
    return parts[1], '_'.join(parts[2:5])


def search_in_json(data: dict, query: str) -> dict:
    hex_part, version_suffix = extract_search_tokens(query)
    if not hex_part or not version_suffix:
        return {}
    results = {}
    for key in data:
        key_lower = key.lower()
        if hex_part in key_lower and version_suffix in key_lower:
            results[key] = data[key]
    return results


def zip_folder(folder_path: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, folder_path)
                zf.write(full, arc)


# ----------------------------
# Scanner Worker (PyQt thread)
# ----------------------------
class ScannerWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, psdz_root: str, json_path: str):
        super().__init__()
        self.psdz_root = Path(psdz_root)
        self.json_path = Path(json_path)

    def run(self):
        try:
            data = scan_psdz_folder_with_warning(self.psdz_root, self.progress.emit)
            atomic_save_json(data, self.json_path)
            self.finished.emit(str(self.json_path))
        except Exception as e:
            self.error.emit(str(e))


# ----------------------------
# Admin GUI (PyQt6)
# ----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🦊 E-Sys FoxData — Настройка")
        self.resize(760, 520)
        self.db = load_db()
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.page1 = self.create_page1()
        self.page2 = self.create_page2()
        self.page3 = self.create_page3()
        self.page4 = self.create_page4()

        self.stacked.addWidget(self.page1)
        self.stacked.addWidget(self.page2)
        self.stacked.addWidget(self.page3)
        self.stacked.addWidget(self.page4)
        self.stacked.setCurrentIndex(0)

    def create_page1(self):
        w = QWidget();
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 1: Укажите папку с полной psdzdata", font=QFont("Arial", 11)))
        self.psdz_edit = QLineEdit(self.db.get("psdzdata_root", ""))
        browse_btn = QPushButton("Выбрать папку psdzdata...")
        browse_btn.clicked.connect(self.browse_psdz)
        lay.addWidget(self.psdz_edit);
        lay.addWidget(browse_btn)
        lay.addStretch()
        next_btn = QPushButton("Далее →");
        next_btn.clicked.connect(self.to_page2)
        lay.addWidget(next_btn)
        return w

    def browse_psdz(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку psdzdata")
        if folder: self.psdz_edit.setText(folder)

    def to_page2(self):
        path = self.psdz_edit.text().strip()
        if not path or not Path(path).is_dir():
            QMessageBox.critical(self, "Ошибка", "Укажите корректную папку!")
            return
        self.db["psdzdata_root"] = path;
        save_db(self.db)
        self.stacked.setCurrentIndex(1)

    def create_page2(self):
        w = QWidget();
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 2: Укажите index JSON (или сгенерируйте новый)", font=QFont("Arial", 11)))
        btn_existing = QPushButton("Выбрать существующий JSON")
        btn_existing.clicked.connect(self.use_existing_json)
        btn_gen = QPushButton("Сгенерировать JSON (сканирование psdzdata)")
        btn_gen.clicked.connect(self.generate_json)
        lay.addWidget(btn_existing);
        lay.addWidget(btn_gen)
        lay.addStretch()
        back_btn = QPushButton("← Назад");
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        lay.addWidget(back_btn)
        return w

    def use_existing_json(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выберите JSON-файл", "", "JSON (*.json)")
        if file:
            self.db["index_json"] = file;
            save_db(self.db)
            self.stacked.setCurrentIndex(2)

    def generate_json(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения JSON")
        if not folder: return
        json_path = Path(folder) / "psdz_index.json"
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Генерация индекса может занять много времени. Продолжить?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.show_scanner_window(json_path)

    def show_scanner_window(self, json_path: Path):
        self.scan_win = QWidget();
        self.scan_win.setWindowTitle("Генерация индекса...")
        self.scan_win.resize(520, 150)
        lay = QVBoxLayout(self.scan_win)
        self.scan_label = QLabel("Начало...");
        self.scan_bar = QProgressBar()
        lay.addWidget(self.scan_label);
        lay.addWidget(self.scan_bar)
        self.scan_win.show()

        self.scanner_thread = QThread()
        self.scanner_worker = ScannerWorker(self.db["psdzdata_root"], str(json_path))
        self.scanner_worker.moveToThread(self.scanner_thread)
        self.scanner_worker.progress.connect(self.update_scan_progress)
        self.scanner_worker.finished.connect(self.on_scan_finished)
        self.scanner_worker.error.connect(self.on_scan_error)
        self.scanner_thread.started.connect(self.scanner_worker.run)
        self.scanner_thread.start()

    def update_scan_progress(self, curr, total):
        pct = int(100 * curr / total) if total else 0
        self.scan_label.setText(f"{curr} / {total} файлов ({pct}%)")
        self.scan_bar.setValue(pct)

    def on_scan_finished(self, json_path):
        self.scanner_thread.quit();
        self.scanner_thread.wait();
        self.scan_win.close()
        self.db["index_json"] = json_path;
        save_db(self.db)
        QMessageBox.information(self, "Готово!", f"Индекс сохранён:\n{json_path}")
        self.stacked.setCurrentIndex(2)

    def on_scan_error(self, err):
        self.scanner_thread.quit();
        self.scanner_thread.wait();
        self.scan_win.close()
        QMessageBox.critical(self, "Ошибка", err)

    def create_page3(self):
        w = QWidget();
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 3: Укажите папку для результатов (output_base)", font=QFont("Arial", 11)))
        self.output_edit = QLineEdit(self.db.get("output_base", ""))
        out_btn = QPushButton("Выбрать папку результатов...");
        out_btn.clicked.connect(self.browse_output)
        lay.addWidget(self.output_edit);
        lay.addWidget(out_btn)
        lay.addStretch()
        back_btn = QPushButton("← Назад");
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        next_btn = QPushButton("Далее →");
        next_btn.clicked.connect(self.to_page4)
        lay.addWidget(next_btn);
        lay.addWidget(back_btn)
        return w

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для результатов")
        if folder: self.output_edit.setText(folder)

    def to_page4(self):
        path = self.output_edit.text().strip()
        if not path or not Path(path).is_dir():
            QMessageBox.critical(self, "Ошибка", "Укажите корректную папку для результатов!")
            return
        self.db["output_base"] = path;
        save_db(self.db)
        self.stacked.setCurrentIndex(3)

    def create_page4(self):
        w = QWidget();
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 4: Telegram API-токен", font=QFont("Arial", 11)))
        self.token_edit = QLineEdit(self.db.get("telegram_token", ""))
        lay.addWidget(self.token_edit)
        help_btn = QPushButton("Как получить токен?");
        help_btn.clicked.connect(self.show_token_help)
        lay.addWidget(help_btn)
        save_btn = QPushButton("Сохранить и запустить бота");
        save_btn.clicked.connect(self.save_and_launch)
        lay.addWidget(save_btn)
        back_btn = QPushButton("← Назад");
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(2))
        lay.addWidget(back_btn)
        self.status_label = QLabel("Статус: бот не запущен")
        lay.addWidget(self.status_label)
        return w

    def show_token_help(self):
        QMessageBox.information(self, "Инструкция", "Найдите @BotFather в Telegram и создайте бота. Скопируйте токен.")

    def save_and_launch(self):
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.critical(self, "Ошибка", "Введите токен!")
            return
        self.db["telegram_token"] = token;
        save_db(self.db)

        # Start bot thread
        self.bot_thread = BotThread(token)
        self.bot_thread.status_updated.connect(self.update_status)
        self.bot_thread.start()
        self.status_label.setText("Статус: бот запущен (в фоне)...")
        log_info("Admin started bot.")

    def update_status(self, msg: str):
        self.status_label.setText("Статус: " + msg)


# ----------------------------
# BotThread (runs asyncio loop in thread)
# ----------------------------
class BotThread(QThread):
    status_updated = pyqtSignal(str)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def run(self):
        try:
            self.status_updated.emit("Запуск бота...")
            # Run asynchronous bot
            asyncio.run(start_bot(self.token, self.status_updated))
        except Exception as e:
            log_error(f"BotThread error: {e}")
            self.status_updated.emit("Ошибка: " + str(e))


# ----------------------------
# Telegram bot logic (async)
# ----------------------------
async def start_bot(token: str, status_signal):
    bot = Bot(token=token)
    dp = Dispatcher()

    db = load_db()
    psdz_root = Path(db.get("psdzdata_root", ""))
    index_json = Path(db.get("index_json", ""))  # admin index
    output_base = Path(db.get("output_base", ""))

    # /start handler
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        kb = InlineKeyboardBuilder()
        kb.button(text="📂 Загрузить личный JSON", callback_data="upload_personal_json")
        kb.button(text="❓ Как это работает", callback_data="how_it_works")
        kb.adjust(1)
        await message.answer(
            "🦊 *Привет! Это E-Sys FoxData.*\n\n"
            "Отправь мне названия недостающих файлов (через пробел/новую строку/запятую).\n"
            f"⚠️ Максимальный суммарный размер архива: *{MAX_ARCHIVE_SIZE_MB} МБ*",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )

    # inline callbacks
    @dp.callback_query(lambda c: c.data == "upload_personal_json")
    async def cb_upload_personal_json(cb: types.CallbackQuery):
        await cb.message.answer("📄 Отправьте JSON-файл как документ — я сохраню его в вашей персональной папке.")
        await cb.answer()

    @dp.callback_query(lambda c: c.data == "how_it_works")
    async def cb_how_it_works(cb: types.CallbackQuery):
        await cb.message.answer(
            "1. Отправляете названия файлов (например `CAFD_00001234_001_000_021`).\n"
            "2. Я ищу в админском JSON (и в вашем личном, если вы загрузили).\n"
            "3. Показываю найденные/не найденные. Вы подтверждаете.\n"
            "4. Я копирую найденные файлы из admin psdzdata в вашу личную папку и архивирую.\n"
            "5. Отправляю архив вам.\n\n"
            "Если нужно — отправьте личный JSON перед поиском."
        )
        await cb.answer()

    # Handler: user uploads personal JSON document
    @dp.message(lambda m: m.document is not None and m.document.file_name.lower().endswith('.json'))
    async def handle_personal_json(message: types.Message):
        db = load_db()
        if not output_base:
            await message.answer("⚠️ Администратор не настроил output_base. Обратитесь к администратору.")
            return
        user_dir = Path(db.get("output_base")) / str(message.from_user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        dest = user_dir / "user_index.json"
        # Download document using aiogram convenient method
        try:
            await message.document.download(destination=dest.as_posix())
            await message.answer("✅ Личный JSON сохранён в вашей персональной папке.")
            log_info(f"user {message.from_user.id} uploaded personal JSON -> {dest}")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка сохранения JSON: {e}")
            log_error(f"download personal json error: {e}")

    # Helper to split tokens
    def split_tokens(text: str):
        return [s.strip() for s in re.split(r'[,\s\n]+', text) if s.strip()]

    # Main text handler — user sends tokens to search
    @dp.message()
    async def handle_search(message: types.Message):
        db = load_db()
        psdz_root = Path(db.get("psdzdata_root", ""))
        index_path = Path(db.get("index_json", ""))
        output_base = Path(db.get("output_base", ""))

        if not (psdz_root.exists() and index_path.exists() and output_base.exists()):
            await message.answer(
                "⚠️ Администратор не завершил настройку (psdzdata/index_json/output_base). Попробуйте позже.")
            return

        text = message.text.strip()
        if not text:
            await message.answer("❗ Пожалуйста, отправьте названия файлов.")
            return

        tokens = split_tokens(text)
        if not tokens:
            await message.answer("❗ Не удалось извлечь токены.")
            return

        # Load admin index
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                admin_index = json.load(f)
        except Exception as e:
            await message.answer(f"⚠️ Ошибка загрузки index JSON: {e}")
            log_error(f"Failed to load admin index json: {e}")
            return

        # Also load user personal index if exists
        user_personal_index = {}
        user_index_path = output_base / str(message.from_user.id) / "user_index.json"
        if user_index_path.exists():
            try:
                with open(user_index_path, "r", encoding="utf-8") as f:
                    user_personal_index = json.load(f)
            except Exception as e:
                log_error(f"Failed load user personal index: {e}")

        # Search tokens in admin_index (and also in personal index)
        matches_map = {}  # rel_path -> info
        search_report = []
        for token in tokens:
            # try user index first, then admin index
            found_in_user = search_in_json(user_personal_index, token) if user_personal_index else {}
            found_in_admin = search_in_json(admin_index, token)
            total_found = {}
            total_found.update(found_in_admin or {})
            total_found.update(found_in_user or {})
            if total_found:
                search_report.append((token, True, len(total_found)))
                for rel, info in total_found.items():
                    matches_map[rel] = info
            else:
                search_report.append((token, False, 0))

        if not matches_map:
            await message.answer("❌ Ничего не найдено по вашим токенам.")
            return

        # Build feedback message
        found_lines = []
        total_size = 0
        too_large = []
        big_files = []
        for rel, info in matches_map.items():
            sz = info.get("size", 0)
            total_size += sz
            found_lines.append(f"• `{rel}` ({sz / (1024 ** 2):.1f} МБ)")
            if sz > MAX_SINGLE_FILE_SIZE:
                too_large.append((rel, sz))
            elif sz > LARGE_FILE_THRESHOLD:
                big_files.append((rel, sz))

        summary = "🔎 *Результаты поиска:*\n\n"
        for token, ok, cnt in search_report:
            summary += ("✅" if ok else "❌") + f" `{token}` — найдено: {cnt}\n"
        summary += f"\nНайденные файлы (показано до 200 строк):\n" + "\n".join(found_lines[:200])
        summary += f"\n\nСуммарный размер: *{total_size / (1024 ** 2):.1f} МБ*"

        if too_large:
            summary += "\n\n⚠️ Есть файлы >1450 МБ — их нельзя отправить автоматически."
        if big_files:
            summary += "\n\n⚠️ Некоторые файлы >999 МБ — вы будете спрошены, продолжать ли с ними."

        # Save request snapshot to DB for callback usage
        db = load_db()
        reqs = db.get("requests", {})
        reqs[str(message.from_user.id)] = {
            "matches": matches_map,
            "total_size": total_size
        }
        db["requests"] = reqs
        save_db(db)

        # Inline buttons: continue / cancel
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Продолжить (скопировать в личную папку)", callback_data=json.dumps({
            "act": "continue",
            "uid": message.from_user.id
        }))
        kb.button(text="❌ Отменить", callback_data=json.dumps({"act": "cancel"}))
        kb.adjust(1)

        # Send summary
        await message.answer(summary, parse_mode="Markdown", reply_markup=kb.as_markup())
        log_info(
            f"user {message.from_user.id} search: {len(matches_map)} files, total {total_size / (1024 ** 2):.1f} MB")

    # Callback query handler to process continue/cancel
    @dp.callback_query(lambda c: True)
    async def cb_any(cq: types.CallbackQuery):
        try:
            payload = json.loads(cq.data)
        except Exception:
            await cq.answer()
            return

        act = payload.get("act")
        if act == "cancel":
            await cq.message.edit_text("❌ Операция отменена пользователем.")
            await cq.answer()
            return

        if act == "continue":
            uid = str(payload.get("uid"))
            db = load_db()
            req = db.get("requests", {}).get(uid)
            if not req:
                await cq.message.answer("⚠️ Данные запроса не найдены. Повторите поиск.")
                await cq.answer()
                return

            matches: Dict[str, dict] = req.get("matches", {})
            total_size = req.get("total_size", 0)

            # Basic checks
            if total_size > MAX_ARCHIVE_SIZE * 10:
                await cq.message.answer("⚠️ Общий размер слишком большой. Разбейте запрос.")
                await cq.answer()
                return

            # If any single file > MAX_SINGLE_FILE_SIZE -> abort and report
            singles = [r for r, info in matches.items() if info.get("size", 0) > MAX_SINGLE_FILE_SIZE]
            if singles:
                txt = "❌ Эти файлы >1450 МБ и не могут быть отправлены автоматически:\n" + "\n".join(
                    f"• `{s}`" for s in singles)
                await cq.message.edit_text(txt, parse_mode="Markdown")
                await cq.answer()
                return

            # Copy files to user's personal folder inside output_base/<uid>/psdzdata/...
            db = load_db()
            psdz_root = Path(db.get("psdzdata_root", ""))
            output_base = Path(db.get("output_base", ""))
            if not (psdz_root.exists() and output_base.exists()):
                await cq.message.answer("⚠️ Администратор не настроил систему (psdz_root/output_base).")
                await cq.answer()
                return

            user_dir = output_base / uid
            psdz_dest = user_dir / "psdzdata"
            # remove previous psdzdata folder for fresh copy
            if psdz_dest.exists():
                shutil.rmtree(psdz_dest)
            psdz_dest.mkdir(parents=True, exist_ok=True)

            # Progress message
            progress_msg = await cq.message.answer("🔁 Копирование файлов: 0%")
            await cq.answer()

            items = list(matches.items())
            total = len(items)
            copied = 0
            for i, (rel, info) in enumerate(items, start=1):
                src = psdz_root / rel
                dst = psdz_dest / rel
                try:
                    if not src.exists():
                        await cq.message.answer(f"⚠️ Файл не найден в источнике: `{rel}`", parse_mode="Markdown")
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception as e:
                    await cq.message.answer(f"⚠️ Ошибка копирования `{rel}`: {e}")
                    log_error(f"copy error {rel}: {e}")

                pct = int(100 * i / total)
                try:
                    # typing animation
                    await bot.send_chat_action(cq.message.chat.id, ChatAction.TYPING)
                except Exception:
                    pass
                # update progress message
                try:
                    await progress_msg.edit_text(f"🔁 Копирование файлов: {i}/{total} ({pct}%)")
                except Exception:
                    pass

            # Build the zip inside user_dir
            await progress_msg.edit_text("📦 Сборка архива...")
            zip_out = user_dir / f"Esys_FoxData_{uid}.zip"
            # remove old zip if exists
            if zip_out.exists():
                zip_out.unlink(missing_ok=True)
            # create zip (include psdzdata folder structure)
            with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_STORED) as zf:
                for root, dirs, files in os.walk(user_dir):
                    for fn in files:
                        full = os.path.join(root, fn)
                        # skip the zip itself if somehow inside
                        if Path(full) == zip_out:
                            continue
                        arc = os.path.relpath(full, user_dir)
                        zf.write(full, arc)

            await progress_msg.edit_text("🚀 Архив собран. Отправляю...")
            try:
                # send typing + upload action
                await bot.send_chat_action(cq.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
            except Exception:
                pass

            try:
                await bot.send_document(cq.message.chat.id, document=FSInputFile(str(zip_out)),
                                        caption="📦 Ваш архив готов")
                log_info(f"Sent archive to user {uid}: {zip_out}")
            except Exception as e:
                await cq.message.answer(f"⚠️ Ошибка отправки архива: {e}")
                log_error(f"send_document error: {e}")
            await cq.message.answer("✅ Готово! Если нужно — начинайте новый поиск.")
            await cq.answer()

    # Start polling
    try:
        status_signal.emit("Бот: polling...")
    except Exception:
        pass
    await dp.start_polling(bot)


# ----------------------------
# Run GUI main
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
