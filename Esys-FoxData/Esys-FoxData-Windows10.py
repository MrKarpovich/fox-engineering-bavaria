import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog


def extract_search_tokens(query):
    """
    Из строки вида 'btld_0000a1b4_015_005_040' извлекает:
    - hex_part: '0000a1b4'
    - version_suffix: '015_005_040'
    """
    parts = query.strip().lower().split('_')
    if len(parts) < 5:
        return None, None
    hex_part = parts[1]
    version_suffix = '_'.join(parts[2:5])
    return hex_part, version_suffix


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


def copy_structure(full_psdzdata_dir, output_dir, results):
    """
    Копирует файлы из full_psdzdata_dir в output_dir/Esys_FoxData/psdzdata/...
    """
    target_root = os.path.join(output_dir, "Esys_FoxData", "psdzdata")
    os.makedirs(target_root, exist_ok=True)

    copied = 0
    not_found = 0

    for rel_path in results:
        src_path = os.path.join(full_psdzdata_dir, rel_path)
        dst_path = os.path.join(target_root, rel_path)

        if os.path.isfile(src_path):
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)  # копирует с метаданными
            print(f"✅ Скопирован: {rel_path}")
            copied += 1
        else:
            print(f"⚠️  Не найден в источнике: {rel_path}")
            not_found += 1

    return copied, not_found


def select_json_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askopenfilename(
        title="Выберите JSON-файл с данными",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )


def select_folder(title):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askdirectory(title=title)


def main():
    print("📁 Выберите JSON-файл с путями...")
    json_path = select_json_file()
    if not json_path:
        print("❌ Отменено.")
        return

    print("📁 Выберите ПОЛНУЮ папку psdzdata (источник файлов)...")
    full_psdzdata_dir = select_folder("Полная папка psdzdata (источник)")
    if not full_psdzdata_dir:
        print("❌ Отменено.")
        return

    print("📁 Выберите папку для сохранения результата...")
    output_dir = select_folder("Папка для сохранения результата")
    if not output_dir:
        print("❌ Отменено.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")
        return

    print(f"\n✅ JSON загружен: {os.path.basename(json_path)}")
    print(f"📦 Источник: {full_psdzdata_dir}")
    print(f"📁 Результат: {output_dir}")
    print("\n🔍 Введите строку для поиска (например: btld_0000a1b4_015_005_040)")
    print("Введите 'exit' для выхода.\n")

    while True:
        user_input = input("Поиск: ").strip()
        if user_input.lower() == 'exit':
            break
        if not user_input:
            continue

        results = search_in_json(data, user_input)
        if not results:
            print("❌ Ничего не найдено. Проверьте формат запроса.\n")
            continue

        print(f"\n🎯 Найдено {len(results)} записей. Копирую файлы...\n")
        copied, not_found = copy_structure(full_psdzdata_dir, output_dir, results)

        print(f"\n🎉 Готово!")
        print(f"✅ Скопировано: {copied}")
        if not_found:
            print(f"⚠️  Не найдено: {not_found}")
        print(f"📁 Результат: {os.path.join(output_dir, 'Esys_FoxData', 'psdzdata')}\n")


if __name__ == '__main__':
    main()
