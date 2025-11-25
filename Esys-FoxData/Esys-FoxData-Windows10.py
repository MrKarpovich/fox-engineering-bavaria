import json
import os
import shutil
import zipfile
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import tkinter.ttk as ttk

# === Константы ===
MAX_ARCHIVE_SIZE = 800 * 1024 * 1024  # 800 МБ
MAX_SINGLE_FILE_SIZE = 1450 * 1024 * 1024  # 1450 МБ
LARGE_FILE_THRESHOLD = 999 * 1024 * 1024  # 999 МБ


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def safe_hash_file(path: Path) -> str:
    try:
        hash_obj = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(65536):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, IOError):
        return ""


def scan_psdz_folder_with_warning(folder_path: Path, progress_callback=None):
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
            # OSError: ошибка чтения, нет доступа
            # ValueError: relative_to() не может обработать путь (маловероятно, но возможно)
            # PermissionError: нет прав
            continue
    return data


def atomic_save_json(data, path: Path):
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp.replace(path)


def make_long_path_safe(path: Path) -> Path:
    if os.name == 'nt':
        abs_path = str(path.resolve())
        if not abs_path.startswith('\\\\?\\'):
            return Path('\\\\?\\' + abs_path)
    return path


# === НОВАЯ ФУНКЦИЯ: создание JSON через GUI ===

class ProgressWindow:
    def __init__(self, title="Прогресс"):
        self.pw = tk.Toplevel()
        self.pw.title(title)
        self.pw.geometry("420x110")
        self.pw.transient()
        self.pw.grab_set()
        self.pw.resizable(False, False)

        self.label = tk.Label(self.pw, text="Начало...")
        self.label.pack(pady=8)
        self.bar = ttk.Progressbar(self.pw, mode='determinate', length=380)
        self.bar.pack(pady=5)
        self.pw.update()

    def update(self, curr, total):
        pct = int(100 * curr / total) if total else 0
        self.label.config(text=f"{curr} из {total} файлов ({pct}%)")
        self.bar['value'] = pct
        self.pw.update()

    def destroy(self):
        self.pw.destroy()


def create_json_interactive():
    # Предупреждение (как в твоём коде!)
    messagebox.showinfo("Внимание",
                        "Процесс займёт много времени (чтение 300 ГБ + хеширование).\n"
                        "Программа может не отвечать — это НОРМАЛЬНО.\n"
                        "НЕ закрывайте окно и не прерывайте процесс!"
                        )

    psdz_folder = filedialog.askdirectory(title="Выберите папку psdzdata для сканирования")
    if not psdz_folder:
        return None

    save_path = filedialog.asksaveasfilename(
        title="Сохранить JSON как...",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")]
    )
    if not save_path:
        return None

    pw = None
    try:
        pw = ProgressWindow("Создание JSON...")
        data = scan_psdz_folder_with_warning(Path(psdz_folder), pw.update)
        atomic_save_json(data, Path(save_path))
        pw.destroy()
        messagebox.showinfo("Готово!", f"JSON сохранён:\n{save_path}")
        return save_path
    except Exception as e:
        if pw is not None:
            pw.destroy()
        messagebox.showerror("Ошибка", str(e))
        return None


# === ОСТАЛЬНОЙ КОД (поиск, копирование, архивация) ===

def extract_search_tokens(query):
    parts = query.strip().lower().split('_')
    if len(parts) < 5:
        return None, None
    return parts[1], '_'.join(parts[2:5])


def search_in_json(data, query):
    hex_part, version_suffix = extract_search_tokens(query)
    if not hex_part or not version_suffix:
        print("❌ Неверный формат запроса. Пример: btld_0000a1b4_015_005_040")
        return {}

    results = {}
    for key in data:
        key_lower = key.lower()
        if hex_part in key_lower and version_suffix in key_lower:
            results[key] = data[key]
    return results


def get_file_size_from_source(full_psdzdata_dir, rel_path):
    src = os.path.join(full_psdzdata_dir, rel_path)
    if os.path.isfile(src):
        return os.path.getsize(src)
    return None


def create_zip_from_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
        root_len = len(os.path.dirname(folder_path)) + 1
        for dirpath, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(dirpath, file)
                arcname = full_path[root_len:]
                zf.write(full_path, arcname)


def main():
    # === ШАГ 1: Выбор JSON ===
    choice = messagebox.askyesno(
        "Выбор JSON",
        "У вас уже есть готовый JSON-файл?\n\n"
        "→ Нажмите 'Да', чтобы выбрать существующий\n"
        "→ Нажмите 'Нет', чтобы создать новый (сканирование psdzdata)"
    )

    if choice:
        # Использовать существующий
        json_path = filedialog.askopenfilename(
            title="Выберите JSON-файл",
            filetypes=[("JSON files", "*.json")]
        )
        if not json_path:
            print("❌ JSON не выбран. Выход.")
            return
    else:
        # Создать новый
        json_path = create_json_interactive()
        if not json_path:
            print("❌ Создание JSON отменено или завершилось с ошибкой.")
            return

    # === ШАГ 2: Остальные выборы (как раньше) ===
    print("📁 Выберите ПОЛНУЮ psdzdata (источник)...")
    full_psdzdata_dir = filedialog.askdirectory(title="Полная psdzdata")
    if not full_psdzdata_dir:
        return

    print("📁 Выберите папку для сохранения архивов...")
    output_base = filedialog.askdirectory(title="Папка для результатов")
    if not output_base:
        return

    # Загрузка JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return

    # === Основной цикл поиска ===
    while True:
        query = input("\n🔍 Введите строку для поиска ('exit' для выхода): ").strip()
        if query.lower() == 'exit':
            print("🚪 Выход.")
            return
        if not query:
            continue

        results = search_in_json(data, query)
        if not results:
            print("❌ Ничего не найдено.")
            continue

        file_info = []
        for rel_path in results:
            size = get_file_size_from_source(full_psdzdata_dir, rel_path)
            if size is not None:
                file_info.append((rel_path, size))

        if not file_info:
            print("❌ Ни один файл не найден в источнике.")
            continue

        final_files = []
        large_files = []
        skip_all = False

        for rel_path, size in file_info:
            if size > MAX_SINGLE_FILE_SIZE:
                msg = f"Файл >1450 МБ:\n{rel_path}\n({size / (1024 ** 2):.1f} МБ)\nПродолжить без него?"
                if messagebox.askyesno("Слишком большой файл", msg):
                    continue
                else:
                    skip_all = True
                    break
            elif size > LARGE_FILE_THRESHOLD:
                large_files.append((rel_path, size))
            else:
                final_files.append((rel_path, size))

        if skip_all:
            continue
        if not final_files and not large_files:
            continue

        # === Создание архивов ===
        archive_index = 1
        current_batch = []
        current_size = 0

        for rel_path, size in final_files:
            if current_batch and (current_size + size > MAX_ARCHIVE_SIZE):
                folder_name = f"Esys_FoxData_{archive_index}"
                folder_path = os.path.join(output_base, folder_name)
                psdz_path = os.path.join(folder_path, "psdzdata")
                os.makedirs(psdz_path, exist_ok=True)

                for rp, _ in current_batch:
                    src = os.path.join(full_psdzdata_dir, rp)
                    dst = os.path.join(psdz_path, rp)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

                zip_path = os.path.join(output_base, f"{folder_name}.zip")
                create_zip_from_folder(folder_path, zip_path)
                shutil.rmtree(folder_path)
                print(f"📦 Архив: {folder_name}.zip")
                archive_index += 1
                current_batch = []
                current_size = 0

            current_batch.append((rel_path, size))
            current_size += size

        if current_batch:
            folder_name = f"Esys_FoxData_{archive_index}"
            folder_path = os.path.join(output_base, folder_name)
            psdz_path = os.path.join(folder_path, "psdzdata")
            os.makedirs(psdz_path, exist_ok=True)
            for rp, _ in current_batch:
                src = os.path.join(full_psdzdata_dir, rp)
                dst = os.path.join(psdz_path, rp)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            zip_path = os.path.join(output_base, f"{folder_name}.zip")
            create_zip_from_folder(folder_path, zip_path)
            shutil.rmtree(folder_path)
            print(f"📦 Архив: {folder_name}.zip")
            archive_index += 1

        for rel_path, size in large_files:
            folder_name = f"Esys_FoxData_Single_{archive_index}"
            folder_path = os.path.join(output_base, folder_name)
            psdz_path = os.path.join(folder_path, "psdzdata")
            os.makedirs(psdz_path, exist_ok=True)
            src = os.path.join(full_psdzdata_dir, rel_path)
            dst = os.path.join(psdz_path, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            zip_path = os.path.join(output_base, f"{folder_name}.zip")
            create_zip_from_folder(folder_path, zip_path)
            shutil.rmtree(folder_path)
            print(f"📦 Архив (большой файл): {folder_name}.zip")
            archive_index += 1

        print(f"\n✅ Готово! Архивы в: {output_base}")


# === ЗАПУСК ===
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    main()
