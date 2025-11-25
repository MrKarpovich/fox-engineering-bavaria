import sys
import json
import asyncio
import zipfile
import tempfile
import re
from pathlib import Path
from typing import List, Tuple

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox,
    QProgressBar, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command


# ========== КОНСТАНТЫ ==========
DB_PATH = Path("foxdata_db.json")
MAX_ARCHIVE_SIZE_MB = 700


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def load_db() -> dict:
    if DB_PATH.exists():
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "psdzdata_root": "",
        "index_json": "",
        "telegram_token": "",
        "requests": {}
    }

def save_db(data: dict):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def safe_hash_file(path: Path) -> str:
    import hashlib
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return ""

def scan_psdz_to_json(psdz_root: Path, json_path: Path, progress_callback=None):
    root = psdz_root.resolve()
    files = [f for f in root.rglob("*") if f.is_file()]
    total = len(files)
    data = {}
    for i, fp in enumerate(files, 1):
        try:
            rel = fp.relative_to(root).as_posix()
            size = fp.stat().st_size
            hsh = safe_hash_file(fp)
            data[rel] = {"size": size, "hash": hsh}
            if progress_callback:
                progress_callback(i, total)
        except Exception:
            continue
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_files_by_keywords(keywords: List[str], index_data: dict) -> List[Tuple[str, dict]]:
    matches = []
    for rel_path, info in index_data.items():
        if any(kw in rel_path for kw in keywords):
            matches.append((rel_path, info))
    return matches

def create_zip_archive(file_list: List[Tuple[str, dict]], zip_path: Path, psdz_root: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel_path, _ in file_list:
            full_path = psdz_root / rel_path
            if full_path.exists():
                zf.write(full_path, arcname=rel_path)


# ========== ПОТОК СКАНИРОВАНИЯ ==========
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
            scan_psdz_to_json(self.psdz_root, self.json_path, self.progress.emit)
            self.finished.emit(str(self.json_path))
        except Exception as e:
            self.error.emit(str(e))


# ========== ПОТОК БОТА ==========
class BotThread(QThread):
    status_updated = pyqtSignal(str)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            self.status_updated.emit("Запуск Telegram-бота...")
            bot = Bot(token=self.token)
            dp = Dispatcher()

            @dp.message(Command("start"))
            async def cmd_start(message: Message):
                await message.answer(
                    "🦊 Привет! Это **E-Sys FoxData**.\n\n"
                    "Инструкция:\n"
                    "1. В E-Sys → Comfort Mode → TAL-calculating\n"
                    "2. Сгенерируйте TAL → нажмите Check software\n"
                    "3. Отправьте сюда названия недостающих файлов (например: `CAFD_00001234_001_000_021`)\n\n"
                    f"⚠️ Макс. размер архива: {MAX_ARCHIVE_SIZE_MB} МБ"
                )

            @dp.message()
            async def handle_files(message: Message):
                db = load_db()
                psdz_root = Path(db["psdzdata_root"])
                index_path = Path(db["index_json"])

                if not (psdz_root.exists() and index_path.exists()):
                    await message.answer("⚠️ Администратор не завершил настройку. Попробуйте позже.")
                    return

                text = message.text.strip()
                if not text:
                    await message.answer("Пожалуйста, отправьте названия файлов.")
                    return

                keywords = [kw.strip() for kw in re.split(r'[,\s\n]+', text) if kw.strip()]
                if not keywords:
                    await message.answer("Не удалось извлечь названия. Попробуйте снова.")
                    return

                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        index_data = json.load(f)

                    matches = find_files_by_keywords(keywords, index_data)
                    if not matches:
                        await message.answer("❌ Ничего не найдено по вашему запросу.")
                        return

                    total_size = sum(info["size"] for _, info in matches)
                    size_mb = total_size / (1024 ** 2)

                    if size_mb > MAX_ARCHIVE_SIZE_MB:
                        details = "\n".join(f"- `{rel}` ({info['size'] / (1024**2):.1f} МБ)" for rel, info in matches)
                        await message.answer(
                            f"❌ Суммарный размер: **{size_mb:.1f} МБ**\n"
                            f"Превышен лимит в **{MAX_ARCHIVE_SIZE_MB} МБ**.\n\n"
                            f"Запрошенные файлы:\n{details}\n\n"
                            "Пожалуйста, разбейте запрос на части.",
                            parse_mode="Markdown"
                        )
                        return

                    # Сохраняем запрос
                    reqs = db.get("requests", {})
                    reqs[str(message.from_user.id)] = {
                        "username": message.from_user.username or f"user_{message.from_user.id}",
                        "files": [rel for rel, _ in matches],
                        "size_mb": round(size_mb, 1)
                    }
                    db["requests"] = reqs
                    save_db(db)

                    # Архивация
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zip_path = Path(tmpdir) / "Esys-FoxData_Requested.zip"
                        create_zip_archive(matches, zip_path, psdz_root)

                        await message.answer_document(
                            document=zip_path.open("rb"),
                            caption=f"✅ Найдено файлов: {len(matches)}\nРазмер: {size_mb:.1f} МБ"
                        )

                except Exception as e:
                    await message.answer(f"⚠️ Ошибка: {str(e)}")

            self.status_updated.emit("✅ Бот запущен! Ожидание сообщений...")
            loop.run_until_complete(dp.start_polling(bot))

        except Exception as e:
            self.status_updated.emit(f"❌ Ошибка бота: {e}")


# ========== ОСНОВНОЕ ОКНО ==========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🦊 E-Sys FoxData — Настройка")
        self.resize(700, 480)
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
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 1 из 4: Укажите папку с полной psdzdata", font=QFont("Arial", 11)))
        self.psdz_edit = QLineEdit(self.db.get("psdzdata_root", ""))
        browse_btn = QPushButton("Выбрать папку...")
        browse_btn.clicked.connect(self.browse_psdz)
        lay.addWidget(self.psdz_edit)
        lay.addWidget(browse_btn)
        lay.addStretch()
        next_btn = QPushButton("Далее →")
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
        self.db["psdzdata_root"] = path
        save_db(self.db)
        self.stacked.setCurrentIndex(1)

    def create_page2(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 2 из 4: У вас есть JSON-индекс?", font=QFont("Arial", 11)))
        btn1 = QPushButton("✅ У меня есть")
        btn1.clicked.connect(self.use_existing_json)
        btn2 = QPushButton("🔄 Сгенерировать новый")
        btn2.clicked.connect(self.generate_json)
        lay.addWidget(btn1)
        lay.addWidget(btn2)
        lay.addStretch()
        back_btn = QPushButton("← Назад")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        lay.addWidget(back_btn)
        return w

    def use_existing_json(self):
        file, _ = QFileDialog.getOpenFileName(self, "Выберите JSON-файл", "", "JSON (*.json)")
        if file:
            self.db["index_json"] = file
            save_db(self.db)
            self.stacked.setCurrentIndex(2)

    def generate_json(self):
        folder = QFileDialog.getExistingDirectory(self, "Куда сохранить JSON?")
        if not folder: return
        json_path = Path(folder) / f"psdzdata_{Path(folder).name}.json"
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Генерация займёт несколько часов!\n"
            "Программа может не отвечать — это НОРМАЛЬНО.\n"
            "НЕ закрывайте окно!\n\nПродолжить?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.show_scanner_window(json_path)

    def show_scanner_window(self, json_path: Path):
        self.scanner_win = QWidget()
        self.scanner_win.setWindowTitle("Генерация индекса...")
        self.scanner_win.resize(500, 140)
        lay = QVBoxLayout(self.scanner_win)
        self.scan_label = QLabel("Начало...")
        self.scan_bar = QProgressBar()
        lay.addWidget(self.scan_label)
        lay.addWidget(self.scan_bar)
        self.scanner_win.show()

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
        self.scanner_thread.quit()
        self.scanner_thread.wait()
        self.scanner_win.close()
        self.db["index_json"] = json_path
        save_db(self.db)
        QMessageBox.information(self, "Готово!", f"Индекс сохранён:\n{json_path}")
        self.stacked.setCurrentIndex(2)

    def on_scan_error(self, err):
        self.scanner_thread.quit()
        self.scanner_thread.wait()
        self.scanner_win.close()
        QMessageBox.critical(self, "Ошибка", err)

    def create_page3(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Шаг 3 из 4: Telegram API-токен", font=QFont("Arial", 11)))
        self.token_edit = QLineEdit(self.db.get("telegram_token", ""))
        lay.addWidget(self.token_edit)
        help_btn = QPushButton("Как получить токен? (инструкция)")
        help_btn.clicked.connect(self.show_token_help)
        lay.addWidget(help_btn)
        next_btn = QPushButton("Далее →")
        next_btn.clicked.connect(self.to_page4)
        lay.addWidget(next_btn)
        back_btn = QPushButton("← Назад")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        lay.addWidget(back_btn)
        return w

    def show_token_help(self):
        msg = (
            "1. Откройте Telegram → найдите @BotFather\n"
            "2. Нажмите /newbot → введите имя (например, EsysFoxData)\n"
            "3. Получите токен вида:\n   1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ\n"
            "4. Скопируйте его и вставьте в поле выше."
        )
        QMessageBox.information(self, "Инструкция", msg)

    def to_page4(self):
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.critical(self, "Ошибка", "Введите токен!")
            return
        self.db["telegram_token"] = token
        save_db(self.db)
        self.stacked.setCurrentIndex(3)

    def create_page4(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("🦊 Настройка завершена!", font=QFont("Arial", 14, QFont.Weight.Bold)))
        lay.addWidget(QLabel("Нажмите «Запустить бота» и оставьте окно открытым.", font=QFont("Arial", 10)))
        self.status_label = QLabel("Статус: ожидание запуска")
        lay.addWidget(self.status_label)
        start_btn = QPushButton("🚀 Запустить бота")
        start_btn.setStyleSheet("background-color: orange; color: black; font-weight: bold;")
        start_btn.clicked.connect(self.launch_bot)
        lay.addWidget(start_btn)
        back_btn = QPushButton("← Назад к настройкам")
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(2))
        lay.addWidget(back_btn)
        return w

    def launch_bot(self):
        token = self.db["telegram_token"]
        if not token:
            QMessageBox.critical(self, "Ошибка", "Токен не задан!")
            return
        self.bot_thread = BotThread(token)
        self.bot_thread.status_updated.connect(self.update_status)
        self.bot_thread.start()
        self.status_label.setText("Запуск... Пожалуйста, подождите.")

    def update_status(self, message: str):
        self.status_label.setText(message)


# ========== ЗАПУСК ==========
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
