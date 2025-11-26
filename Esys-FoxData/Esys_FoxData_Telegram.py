"""
E-Sys FoxData — Admin GUI + Telegram bot (aiogram 3.22, PyQt6)
Single-file version (Variant A) — uses admin JSON index only for searching.

Features:
 - Admin GUI (PyQt6) to set psdzdata_root, index_json (or generate), output_base and telegram token
 - Generate index (scan) with progress
 - Bot: inline buttons, typing action, progress updates, logging
 - Per-user personal folders: output_base/<user_id>/...
 - Uses admin index_json only (clients DO NOT upload JSON)
 - Automatic splitting of archives into parts <= 800 MB
 - Removal of user temp folder after successful send
 - /help and /faq commands with contact link
"""

import sys
import os
import json
import re
import shutil
import zipfile
import tempfile
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, List

import asyncio

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QMessageBox, QProgressBar, QStackedWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, pyqtSignal, QObject

# aiogram 3.22
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


def extract_search_tokens(query: str) -> Tuple[Any, Any]:
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


def ensure_user_dir(output_base: Path, user_id: int) -> Path:
    ud = output_base / str(user_id)
    ud.mkdir(parents=True, exist_ok=True)
    return ud


# split list of (rel_path, size) into batches where each batch total_size <= MAX_ARCHIVE_SIZE
def make_batches_by_size(items: List[Tuple[str, int]], max_bytes: int) -> List[List[Tuple[str, int]]]:
    batches = []
    current = []
    cur_size = 0
    for rel, size in items:
        if current and (cur_size + size > max_bytes):
            batches.append(current)
            current = []
            cur_size = 0
        current.append((rel, size))
        cur_size += size
    if current:
        batches.append(current)
    return batches


def create_zip_from_batch(psdz_root: Path, batch: List[Tuple[str, int]], zip_path: Path):
    # Create temporary folder and copy files into "psdzdata" subfolder structure, then zip and remove folder.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        psdz_dest = base / "psdzdata"
        for rel, _ in batch:
            src = psdz_root / rel
            dst = psdz_dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            # copy2 preserves metadata
            shutil.copy2(src, dst)
        # create zip from psdz_dest but arcname root should be "psdzdata/..."
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            root_len = len(str(psdz_dest.parent)) + 1
            for dirpath, dirs, files in os.walk(psdz_dest):
                for f in files:
                    full = os.path.join(dirpath, f)
                    arc = full[root_len:]
                    zf.write(full, arc)


# Alternative: directly add files to zip with arcname "psdzdata/rel"
def create_zip_direct(psdz_root: Path, batch: List[Tuple[str, int]], zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for rel, _ in batch:
            full = psdz_root / rel
            if full.exists():
                arc = os.path.join("psdzdata", rel)
                zf.write(full, arc)


# cleanup user dir
def cleanup_user_dir(user_dir: Path):
    try:
        if user_dir.exists():
            shutil.rmtree(user_dir)
        log_info(f"Removed user dir: {user_dir}")
    except Exception as e:
        log_error(f"Failed to remove user dir {user_dir}: {e}")


# ----------------------------
# PyQt Scanner Worker
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
        self.resize(720, 480)
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
        if folder:
            self.psdz_edit.setText(folder)

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
        if not folder:
            return
        json_path = Path(folder) / "psdz_index.json"
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Генерация индекса может занять много времени (чтение большого объёма файлов + хеширование). Продолжить?"
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
        if folder:
            self.output_edit.setText(folder)

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
            asyncio.run(start_bot(self.token, self.status_updated))
        except Exception as e:
            log_error(f"BotThread error: {e}")
            self.status_updated.emit("Ошибка: " + str(e))


# ----------------------------
# Telegram bot async logic
# ----------------------------
async def start_bot(token: str, status_signal):
    bot = Bot(token=token)
    dp = Dispatcher()

    # Helper: load admin index JSON (maps rel_path -> {size, hash})
    def load_admin_index() -> Dict[str, dict]:
        db = load_db()
        idx = db.get("index_json", "")
        if not idx:
            return {}
        try:
            with open(idx, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load admin index: {e}")
            return {}

    # /start, /help, /faq handlers
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        kb = InlineKeyboardBuilder()
        kb.button(text="❓ /help", callback_data="help_cb")
        kb.button(text="📚 /faq", callback_data="faq_cb")
        kb.adjust(2)
        await message.answer(
            "🦊 *Привет! Это E-Sys FoxData.*\n\n"
            "Отправь мне названия недостающих файлов (через пробел/новую строку/запятую).\n"
            f"⚠️ Максимальный суммарный размер архива: *{MAX_ARCHIVE_SIZE_MB} МБ*",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        txt = (
            "🆘 *Помощь — как пользоваться ботом*\n\n"
            "1. Отправь названия файлов в строке (например `CAFD_00001234_001_000_021`). Можно несколько — через пробел/новую строку/запятую.\n"
            "2. Я ищу по админскому JSON (индекс хранит администратор сервера).\n"
            "3. После поиска я покажу, что найдено и что нет — подтвердите продолжение.\n"
            "4. Я соберу архив(ы) и отправлю их вам. После успешной отправки временные файлы будут удалены.\n\n"
            "Если нужна помощь админа — свяжитесь с автором: t.me/JluceHok_u3_MuHcka"
        )
        await message.answer(txt, parse_mode="Markdown")

    @dp.message(Command("faq"))
    async def cmd_faq(message: types.Message):
        txt = (
            "📚 *FAQ*\n\n"
            "Q: Что если файл слишком большой?  \n"
            "A: Файлы >1450 МБ не отправляются автоматически; вы получите уведомление и сможете изменить запрос.\n\n"
            "Q: Как разбиваются архивы?  \n"
            f"A: Автоматически на части ≤ {MAX_ARCHIVE_SIZE_MB} МБ.\n\n"
            "Контакт: t.me/JluceHok_u3_MuHcka"
        )
        await message.answer(txt, parse_mode="Markdown")

    @dp.callback_query(lambda c: c.data == "help_cb")
    async def cb_help(cq: types.CallbackQuery):
        await cq.message.answer("Используйте /help и /faq для подробной информации.")
        await cq.answer()

    @dp.callback_query(lambda c: c.data == "faq_cb")
    async def cb_faq(cq: types.CallbackQuery):
        await cq.message.answer("См. /faq — там ответы на частые вопросы и контакты.")
        await cq.answer()

    # Helper: split user input tokens
    def split_tokens(text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[,\s\n]+', text) if s.strip()]

    # Main handler: user sends tokens
    @dp.message()
    async def handle_messages(message: types.Message):
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

        admin_index = load_admin_index()
        if not admin_index:
            await message.answer("⚠️ Админский индекс не доступен. Обратитесь к администратору.")
            return

        # Collect matches (unique)
        matches_map: Dict[str, dict] = {}
        search_report = []
        for token in tokens:
            res = search_in_json(admin_index, token)
            if res:
                search_report.append((token, True, len(res)))
                for rel, info in res.items():
                    matches_map[rel] = info
            else:
                search_report.append((token, False, 0))

        if not matches_map:
            await message.answer("❌ Ничего не найдено по вашим токенам.")
            return

        # Create list with sizes and existence check
        file_info = []
        not_found_on_disk = []
        for rel, info in matches_map.items():
            src = psdz_root / rel
            if src.exists() and src.is_file():
                file_info.append((rel, info.get("size", 0)))
            else:
                not_found_on_disk.append(rel)

        # Prepare feedback text
        summary_lines = []
        total_size = sum(size for _, size in file_info)
        for token, ok, cnt in search_report:
            summary_lines.append(("✅" if ok else "❌") + f" `{token}` — найдено: {cnt}")
        summary = "🔎 *Результаты поиска:*\n\n" + "\n".join(summary_lines)
        summary += f"\n\nНайденные на диске: {len(file_info)} файлов\n" \
                   f"Не найдено на диске (в JSON, но отсутствует по пути): {len(not_found_on_disk)}\n" \
                   f"\nСуммарный размер (файлы, которые есть на диске): *{total_size / (1024 ** 2):.1f} МБ*"

        if any(size > MAX_SINGLE_FILE_SIZE for _, size in file_info):
            summary += f"\n\n⚠️ Есть файлы >{MAX_SINGLE_FILE_SIZE // (1024 ** 2)} МБ — их нельзя отправить автоматически."

        if any(size > LARGE_FILE_THRESHOLD for _, size in file_info):
            summary += f"\n\n⚠️ Есть большие файлы (> {LARGE_FILE_THRESHOLD // (1024 ** 2)} МБ)."

        # Save snapshot for callback
        db = load_db()
        reqs = db.get("requests", {})
        reqs[str(message.from_user.id)] = {"matches": {rel: {"size": sz} for rel, sz in file_info},
                                           "not_on_disk": not_found_on_disk}
        db["requests"] = reqs
        save_db(db)

        # Inline: Continue / Cancel
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Продолжить (собирать архив и отправить)",
                  callback_data=json.dumps({"act": "continue", "uid": message.from_user.id}))
        kb.button(text="❌ Отменить", callback_data=json.dumps({"act": "cancel"}))
        kb.adjust(1)

        # Send summary
        await message.answer(summary, parse_mode="Markdown", reply_markup=kb.as_markup())
        log_info(
            f"user {message.from_user.id} search: found_on_disk={len(file_info)} missing_on_disk={len(not_found_on_disk)} total_mb={total_size / (1024 ** 2):.1f}")

    # Callback handler
    @dp.callback_query(lambda c: True)
    async def cb_general(cq: types.CallbackQuery):
        payload_raw = cq.data
        try:
            payload = json.loads(payload_raw)
        except Exception:
            await cq.answer()
            return
        act = payload.get("act")
        if act == "cancel":
            try:
                await cq.message.edit_text("❌ Операция отменена пользователем.")
            except Exception:
                pass
            await cq.answer()
            return
        if act != "continue":
            await cq.answer();
            return

        uid = str(payload.get("uid"))
        db = load_db()
        req = db.get("requests", {}).get(uid)
        if not req:
            await cq.message.answer("⚠️ Нет данных запроса — повторите поиск.")
            await cq.answer()
            return

        matches = req.get("matches", {})  # rel -> {"size": size}
        not_on_disk = req.get("not_on_disk", [])

        if not matches:
            await cq.message.answer("⚠️ Нет файлов для обработки.")
            await cq.answer()
            return

        # Separate files: too large (> MAX_SINGLE_FILE_SIZE) cannot be sent
        too_large = [rel for rel, info in matches.items() if info.get("size", 0) > MAX_SINGLE_FILE_SIZE]
        if too_large:
            txt = "❌ В запросе есть файлы, превышающие допустимый однофайловый лимит (>1450 МБ):\n" + "\n".join(
                f"• `{r}`" for r in too_large)
            txt += "\n\nПожалуйста, удалите эти файлы из запроса или обратитесь к администратору."
            try:
                await cq.message.edit_text(txt, parse_mode="Markdown")
            except Exception:
                pass
            await cq.answer()
            return

        # Proceed: prepare user folder and copy files
        db_cfg = load_db()
        psdz_root = Path(db_cfg.get("psdzdata_root", ""))
        output_base = Path(db_cfg.get("output_base", ""))
        if not (psdz_root.exists() and output_base.exists()):
            await cq.message.answer("⚠️ Системная ошибка: psdz_root/output_base не доступны.")
            await cq.answer()
            return

        user_dir = output_base / uid
        # Fresh build: remove existing psdzdata folder (but keep maybe other files)
        psdz_dest = user_dir / "psdzdata"
        if psdz_dest.exists():
            shutil.rmtree(psdz_dest)
        psdz_dest.mkdir(parents=True, exist_ok=True)

        # Progress message
        progress_msg = await cq.message.answer("🔁 Копирование файлов: 0%")
        await cq.answer()

        items = list(matches.items())  # list of (rel, {"size":size})
        total = len(items)
        copied_count = 0
        copied_list: List[Tuple[str, int]] = []
        for i, (rel, info) in enumerate(items, start=1):
            src = psdz_root / rel
            dst = psdz_dest / rel
            try:
                if not src.exists():
                    # skip missing files (should not happen because earlier we filtered by existence)
                    await cq.message.answer(f"⚠️ Файл не найден на диске: `{rel}`", parse_mode="Markdown")
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                size = info.get("size", src.stat().st_size if src.exists() else 0)
                copied_list.append((rel, size))
                copied_count += 1
            except Exception as e:
                await cq.message.answer(f"⚠️ Ошибка копирования `{rel}`: {e}")
                log_error(f"Copy error {rel}: {e}")

            pct = int(100 * i / total)
            try:
                await bot.send_chat_action(cq.message.chat.id, ChatAction.TYPING)
            except Exception:
                pass
            try:
                await progress_msg.edit_text(f"🔁 Копирование файлов: {i}/{total} ({pct}%)")
            except Exception:
                pass

        if not copied_list:
            await progress_msg.edit_text("❌ Ни один файл не был скопирован. Отмена.")
            await cq.answer()
            return

        # Now create batches by size
        batches = make_batches_by_size(copied_list, MAX_ARCHIVE_SIZE)

        # create zips in temporary folder under user_dir
        tmp_out_dir = user_dir / "zips"
        if tmp_out_dir.exists():
            shutil.rmtree(tmp_out_dir)
        tmp_out_dir.mkdir(parents=True, exist_ok=True)

        zip_paths: List[Path] = []
        # For each batch create zip
        for idx, batch in enumerate(batches, start=1):
            zip_name = f"Esys_FoxData_part{idx}.zip"
            zip_path = tmp_out_dir / zip_name
            # create zip directly from psdz_root using rel paths (so arcs contain psdzdata/rel)
            # but our copied files are inside psdz_dest, so we can zip from there
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                for rel, _ in batch:
                    full = psdz_dest / rel
                    if full.exists():
                        arc = os.path.join("psdzdata", rel)
                        zf.write(str(full), arc)
            zip_paths.append(zip_path)

            try:
                await progress_msg.edit_text(f"📦 Создан архив {idx}/{len(batches)} — {zip_name}")
            except Exception:
                pass

        # If there are files that were in JSON but missing on disk, inform user
        if not_on_disk:
            try:
                await cq.message.answer(
                    "⚠️ Некоторые файлы присутствовали в JSON, но отсутствуют на диске и были пропущены:\n" + "\n".join(
                        f"• `{r}`" for r in not_on_disk), parse_mode="Markdown")
            except Exception:
                pass

        # Send zip files one by one
        sent_count = 0
        for zp in zip_paths:
            try:
                await bot.send_chat_action(cq.message.chat.id, ChatAction.UPLOAD_DOCUMENT)
            except Exception:
                pass
            try:
                await bot.send_document(cq.message.chat.id, document=FSInputFile(str(zp)),
                                        caption=f"📦 Часть архива: {zp.name}")
                sent_count += 1
                log_info(f"Sent zip {zp} to user {uid}")
            except Exception as e:
                await cq.message.answer(f"⚠️ Ошибка отправки {zp.name}: {e}")
                log_error(f"Send zip error {zp}: {e}")

        # After successful sends, cleanup user folder
        try:
            cleanup_user_dir(user_dir)
        except Exception:
            pass

        try:
            await progress_msg.edit_text(f"✅ Отправлено {sent_count} архив(ов). Удачи!")
        except Exception:
            pass

        await cq.message.answer("🦊 Готово — архивы отправлены. Если нужно, начните новый поиск с новыми названиями.")
        await cq.answer()

    # start polling
    try:
        status_signal.emit("Бот: polling...")
    except Exception:
        pass
    await dp.start_polling(bot)


# ----------------------------
# Main: run GUI
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
