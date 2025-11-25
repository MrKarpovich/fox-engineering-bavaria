import json
import os
import shutil
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox

# Константы (в байтах)
MAX_ARCHIVE_SIZE = 800 * 1024 * 1024  # 800 МБ
MAX_SINGLE_FILE_SIZE = 1450 * 1024 * 1024  # 1450 МБ
LARGE_FILE_THRESHOLD = 999 * 1024 * 1024  # 999 МБ


def extract_search_tokens(query):
    """
    Из строки вида 'btld_0000a1b4_015_005_040' извлекает hex_part и версию.
    """
    parts = query.strip().lower().split('_')
    if len(parts) < 5:
        return None, None
    hex_part = parts[1]
    version_suffix = '_'.join(parts[2:5])
    return hex_part, version_suffix


def search_in_json(data, query):
    """
    Ищет в JSON все ключи, содержащие hex_part и version_suffix.
    """
    hex_part, version_suffix = extract_search_tokens(query)
    if not hex_part or not version_suffix:
        print("❌ Неверный формат запроса. Пример: btld_0000a1b4_015_005_040")
        return {}

    results = {}
    for key in data:  # ← ПОЛНОСТЬЮ ЗАВЕРШЁННЫЙ ЦИКЛ
        key_lower = key.lower()
        if hex_part in key_lower and version_suffix in key_lower:
            results[key] = data[key]
    return results


def get_file_size_from_source(full_psdzdata_dir, rel_path):
    """
    Возвращает размер файла из источника или None, если не найден.
    """
    src_path = os.path.join(full_psdzdata_dir, rel_path)
    if os.path.isfile(src_path):
        return os.path.getsize(src_path)
    return None


def create_zip_from_folder(folder_path, zip_path):
    """
    Создаёт ZIP-архив из папки (включая подпапки).
    """
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        root_len = len(os.path.dirname(folder_path)) + 1
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = full_path[root_len:]
                zf.write(full_path, arcname)


def main():
    # === Выбор файлов/папок через диалоги ===
    print("📁 Выберите JSON-файл с данными...")
    json_path = filedialog.askopenfilename(
        title="Выберите JSON-файл",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if not json_path:
        print("❌ Отменено: JSON не выбран.")
        return

    print("📁 Выберите ПОЛНУЮ папку psdzdata (источник)...")
    full_psdzdata_dir = filedialog.askdirectory(title="Полная psdzdata")
    if not full_psdzdata_dir:
        print("❌ Отменено: папка источника не выбрана.")
        return

    print("📁 Выберите папку для сохранения архивов...")
    output_base = filedialog.askdirectory(title="Папка для результатов")
    if not output_base:
        print("❌ Отменено: папка вывода не выбрана.")
        return

    # === Загрузка JSON ===
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return

    # === Основной цикл ввода ===
    while True:
        query = input("\n🔍 Введите строку для поиска ('exit' для выхода): ").strip()
        if query.lower() == 'exit':
            print("🚪 Выход.")
            return
        if not query:
            continue

        # === Поиск в JSON ===
        results = search_in_json(data, query)
        if not results:
            print("❌ Ничего не найдено по запросу.")
            continue

        # === Сбор информации о файлах и их размерах ===
        file_info = []
        for rel_path in results:
            size = get_file_size_from_source(full_psdzdata_dir, rel_path)
            if size is None:
                print(f"⚠️  Файл не найден в источнике: {rel_path}")
            else:
                file_info.append((rel_path, size))

        if not file_info:
            print("❌ Ни один файл не найден в источнике.")
            continue

        # === Обработка очень больших файлов (>1450 МБ) ===
        final_files = []  # файлы ≤ 999 МБ → в общие архивы
        large_files = []  # 999–1450 МБ → отдельные архивы
        skip_all = False

        for rel_path, size in file_info:
            if size > MAX_SINGLE_FILE_SIZE:
                msg = (
                    f"Файл превышает 1450 МБ:\n{rel_path}\n\n"
                    f"Размер: {size / (1024 ** 2):.1f} МБ\n\n"
                    "Продолжить без этого файла?"
                )
                if messagebox.askyesno("Слишком большой файл", msg):
                    print(f"⏭️  Пропущен: {rel_path} (>1450 МБ)")
                    continue
                else:
                    print("🛑 Операция отменена пользователем.")
                    skip_all = True
                    break
            elif size > LARGE_FILE_THRESHOLD:
                large_files.append((rel_path, size))
            else:
                final_files.append((rel_path, size))

        if skip_all:
            continue

        # === Создание архивов ===
        archive_index = 1

        # ---- 1. Общие архивы (≤800 МБ) ----
        current_batch = []
        current_size = 0

        for rel_path, size in final_files:
            if current_batch and (current_size + size > MAX_ARCHIVE_SIZE):
                # Создаём архив
                folder_name = f"Esys_FoxData_{archive_index}"
                folder_path = os.path.join(output_base, folder_name)
                psdz_path = os.path.join(folder_path, "psdzdata")
                os.makedirs(psdz_path, exist_ok=True)

                for rp, _ in current_batch:
                    src = os.path.join(full_psdzdata_dir, rp)
                    dst = os.path.join(psdz_path, rp)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

                zip_name = f"{folder_name}.zip"
                zip_path = os.path.join(output_base, zip_name)
                create_zip_from_folder(folder_path, zip_path)
                shutil.rmtree(folder_path)
                print(f"📦 Создан архив: {zip_name}")
                archive_index += 1
                current_batch = []
                current_size = 0

            current_batch.append((rel_path, size))
            current_size += size

        # Последний батч
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

            zip_name = f"{folder_name}.zip"
            zip_path = os.path.join(output_base, zip_name)
            create_zip_from_folder(folder_path, zip_path)
            shutil.rmtree(folder_path)
            print(f"📦 Создан архив: {zip_name}")
            archive_index += 1

        # ---- 2. Отдельные архивы для больших файлов (999–1450 МБ) ----
        for rel_path, size in large_files:
            folder_name = f"Esys_FoxData_Single_{archive_index}"
            folder_path = os.path.join(output_base, folder_name)
            psdz_path = os.path.join(folder_path, "psdzdata")
            os.makedirs(psdz_path, exist_ok=True)

            src = os.path.join(full_psdzdata_dir, rel_path)
            dst = os.path.join(psdz_path, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

            zip_name = f"{folder_name}.zip"
            zip_path = os.path.join(output_base, zip_name)
            create_zip_from_folder(folder_path, zip_path)
            shutil.rmtree(folder_path)
            print(f"📦 Создан архив для большого файла: {zip_name}")
            archive_index += 1

        print(f"\n✅ Всё готово! Архивы сохранены в: {output_base}")


# === Точка входа ===
if __name__ == '__main__':
    # Настройка Tkinter для диалогов
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    main()
