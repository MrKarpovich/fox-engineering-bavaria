import os
import json
import hashlib
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def safe_hash_file(path: Path) -> str:
    try:
        hash_obj = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(65536):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, IOError):
        return ""


def scan_psdz_folder_with_warning(root: Path, progress_callback=None):
    """Полное сканирование с хешированием — для кнопки 1."""
    root = root.resolve()
    data = {}
    files = [f for f in root.rglob('*') if f.is_file()]
    total = len(files)
    for i, full_path in enumerate(files, 1):
        try:
            rel_path = full_path.relative_to(root).as_posix()
            size = full_path.stat().st_size
            file_hash = safe_hash_file(full_path)
            data[rel_path] = {"size": size, "hash": file_hash}
            if progress_callback:
                progress_callback(i, total)
        except Exception:
            continue
    return data


def make_long_path_safe(path: Path) -> Path:
    if os.name == 'nt':
        abs_path = str(path.resolve())
        if not abs_path.startswith('\\\\?\\'):
            return Path('\\\\?\\' + abs_path)
    return path


def safe_copy_files_by_list(src_root: Path, dst_root: Path, file_list, progress_callback=None):
    src_root = make_long_path_safe(src_root)
    dst_root = make_long_path_safe(dst_root)
    total = len(file_list)
    for i, rel in enumerate(file_list, 1):
        src = src_root / rel
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
        if progress_callback:
            progress_callback(i, total)


def atomic_save_json(data, path: Path):
    temp = path.with_suffix('.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp.replace(path)


# ========== GUI ==========

class PSDZApp:
    def __init__(self, root):
        self.root = root
        root.title("PSDZData Updater — для BMW ISTA/E-Sys")
        root.geometry("650x280")
        root.resizable(False, False)

        tk.Label(root, text="Экономия трафика: обновление без перекачки 300 ГБ",
                 font=("Arial", 11, "bold")).pack(pady=12)

        btns = tk.Frame(root)
        btns.pack(pady=10)

        tk.Button(btns, text="1. Просканировать psdzdata и создать json",
                  width=55, height=2, command=self.scan_psdz).pack(pady=7)

        tk.Button(btns, text="2. Создать python_psdzdata (Обновление ПО)",
                  width=55, height=2, command=self.create_update).pack(pady=7)

        self.status = tk.Label(root, text="Готово", fg="gray")
        self.status.pack(side="bottom", pady=8)

    def update_status(self, text):
        self.status.config(text=text)
        self.root.update()

    def show_progress(self, title="Прогресс"):
        self.pw = tk.Toplevel(self.root)
        self.pw.title(title)
        self.pw.geometry("420x110")
        self.pw.transient(self.root)
        self.pw.grab_set()
        self.pw.resizable(False, False)

        self.pl = tk.Label(self.pw, text="Начало...")
        self.pl.pack(pady=8)
        self.pb = ttk.Progressbar(self.pw, mode='determinate', length=380)
        self.pb.pack(pady=5)
        self.pw.update()

    def update_progress(self, curr, total):
        pct = int(100 * curr / total) if total else 0
        self.pl.config(text=f"{curr} из {total} файлов ({pct}%)")
        self.pb['value'] = pct
        self.pw.update()

    def scan_psdz(self):
        messagebox.showinfo("Внимание",
                            "Процесс займёт много времени (чтение 300 ГБ + хеширование).\n"
                            "Программа может не отвечать — это НОРМАЛЬНО.\n"
                            "НЕ закрывайте окно и не прерывайте процесс!"
                            )
        folder = filedialog.askdirectory(title="Выберите папку psdzdata для сканирования")
        if not folder: return
        out_file = filedialog.asksaveasfilename(
            title="Сохранить как...", defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if not out_file: return

        try:
            self.show_progress("Создание...")
            data = scan_psdz_folder_with_warning(Path(folder), self.update_progress)
            atomic_save_json(data, Path(out_file))
            self.pw.destroy()
            messagebox.showinfo("Готово!", f"Файл сохранён:\n{out_file}")
        except Exception as e:
            if hasattr(self, 'pw'): self.pw.destroy()
            messagebox.showerror("Ошибка!", str(e))

    def create_update(self):
        old_json = filedialog.askopenfilename(
            title="1. Выберите JSON СТАРОГО ПО (Версия клиента)",
            filetypes=[("JSON", "*.json")]
        )
        if not old_json: return

        new_json = filedialog.askopenfilename(
            title="2. Выберите JSON НОВОГО ПО (Последняя версия)",
            filetypes=[("JSON", "*.json")]
        )
        if not new_json: return

        new_psdz_folder = filedialog.askdirectory(
            title="3. Укажите папку с НОВЫМ ПО psdzdata (последняя версия)"
        )
        if not new_psdz_folder: return

        output_dir = filedialog.askdirectory(
            title="4. Куда мне сохранить патч для обновления? (Советую сначала хоть на рабочий стол, потом на флешку)"
        )
        if not output_dir: return

        # Подтверждение выбора
        msg = (
            f"Старый json клиента: {Path(old_json).name}\n"
            f"Новый json с последнним ПО: {Path(new_json).name}\n"
            f"Папка с последним ПО: {new_psdz_folder}\n"
            f"Сохраняем патч для обновления по пути: {output_dir}\n\n"
            "Всё верно?"
        )
        if not messagebox.askyesno("Проверка", msg):
            return

        try:
            # Загрузка
            old_data = json.load(open(old_json, encoding='utf-8'))
            new_data = json.load(open(new_json, encoding='utf-8'))

            # Сравнение — только по JSON!
            to_copy = []
            for rel, new_info in new_data.items():
                old_info = old_data.get(rel)
                if old_info is None or old_info["hash"] != new_info["hash"]:
                    to_copy.append(rel)

            if not to_copy:
                messagebox.showinfo("Информация", "Изменений не найдено.")
                return

            total_size = sum(new_data[f]["size"] for f in to_copy) / (1024 ** 3)
            confirm = messagebox.askyesno(
                "Подтверждение",
                f"Найдено {len(to_copy)} файлов для копирования.\n"
                f"Общий размер: {total_size:.1f} ГБ.\n"
                "Создать обновление?"
            )
            if not confirm:
                return

            # Копирование БЕЗ хеширования!
            dst = Path(output_dir) / "python_psdzdata" / "psdzdata"
            self.show_progress("Копирование файлов")
            safe_copy_files_by_list(Path(new_psdz_folder), dst, to_copy, self.update_progress)
            self.pw.destroy()

            messagebox.showinfo("Готово",
                                f"Обновление создано!\n"
                                f"Папка: {Path(output_dir) / 'python_psdzdata'}"
                                )

        except Exception as e:
            if hasattr(self, 'pw'): self.pw.destroy()
            messagebox.showerror("Ошибка", str(e))


# ========== ЗАПУСК ==========

if __name__ == "__main__":
    root = tk.Tk()
    app = PSDZApp(root)
    root.mainloop()
