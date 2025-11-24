# ISTA RegFox 🦊 — Управление реестром ISTA
# Версия: 1.5 (исправлены синтаксис и область видимости переменных)
# Требует запуска от администратора

import sys
import os
import json
import ctypes
from pathlib import Path

# --- GUI ---
import tkinter as tk
from tkinter import messagebox, filedialog

# --- Реестр Windows ---
import winreg

# --- Константы ---
APP_NAME = "ISTA RegFox"
CACHE_DIR = Path(os.getenv("APPDATA")) / APP_NAME
CACHE_FILE = CACHE_DIR / "cache.json"

BMW_KEYS = {
    "new": r"SOFTWARE\BMWGroup\ISPI",
    "old": r"SOFTWARE\WOW6432Node\BMWGroup\ISPI"
}

RHEINGOLD_SUBKEY = "Rheingold"
ISTA_SUBKEY = "ISTA"

DEFAULT_SWI_VERSION = "4.55.30"
PSDZ_BASE_REL = r"..\\..\\..\\PSdZ"

# --- Вспомогательные функции ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def restart_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

def save_cache(data):
    try:
        CACHE_FILE.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось сохранить кэш:\n{e}")

# --- Работа с реестром ---
def find_ista_flavors():
    flavors = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, BMW_KEYS["new"], 0, winreg.KEY_READ) as key:
            winreg.OpenKey(key, ISTA_SUBKEY, 0, winreg.KEY_READ)
            flavors.append("new")
    except FileNotFoundError:
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, BMW_KEYS["old"], 0, winreg.KEY_READ) as key:
            winreg.OpenKey(key, ISTA_SUBKEY, 0, winreg.KEY_READ)
            flavors.append("old")
    except FileNotFoundError:
        pass

    return flavors

def read_registry_value(root_path, subkey, value_name):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{root_path}\\{subkey}", 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, value_name)
            return value, reg_type
    except (FileNotFoundError, OSError):
        return None, None

def set_registry_value(root_path, subkey, value_name, value, reg_type=winreg.REG_SZ):
    try:
        full_path = f"{root_path}\\{subkey}"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, full_path) as key:
            winreg.SetValueEx(key, value_name, 0, reg_type, value)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка записи в реестр", f"Не удалось записать {value_name}:\n{e}")
        return False

def read_entire_ista_tree(flavor):
    data = {}
    base_key = BMW_KEYS[flavor]
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key, 0, winreg.KEY_READ) as main_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(main_key, i)
                    subkey_path = f"{base_key}\\{subkey_name}"
                    subkey_data = {}
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path, 0, winreg.KEY_READ) as subkey:
                        j = 0
                        while True:
                            try:
                                name, value, reg_type = winreg.EnumValue(subkey, j)
                                type_str = {
                                    winreg.REG_SZ: "REG_SZ",
                                    winreg.REG_DWORD: "REG_DWORD",
                                    winreg.REG_BINARY: "REG_BINARY",
                                    winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
                                    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ"
                                }.get(reg_type, f"REG_UNKNOWN({reg_type})") # type: ignore

                                subkey_data[name] = {
                                    "value": value if reg_type != winreg.REG_BINARY else value.hex(),
                                    "type": type_str
                                }
                                j += 1
                            except OSError:
                                break
                    if subkey_data:
                        data[subkey_path] = subkey_data
                    i += 1
                except OSError:
                    break
    except Exception as e:
        print(f"Ошибка чтения {base_key}: {e}")
    return data

def write_registry_from_json(reg_data):
    type_map = {
        "REG_SZ": winreg.REG_SZ,
        "REG_DWORD": winreg.REG_DWORD,
        "REG_BINARY": winreg.REG_BINARY,
        "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ
    }

    for full_path, values in reg_data.items():
        if full_path.startswith("HKEY_LOCAL_MACHINE\\"):
            path = full_path[len("HKEY_LOCAL_MACHINE\\"):]
        else:
            path = full_path

        parts = path.split("\\", 1)
        if len(parts) == 1:
            root = parts[0]
            sub = ""
        else:
            root, sub = parts

        for name, info in values.items():
            try:
                reg_type = type_map.get(info["type"], winreg.REG_SZ)
                value = info["value"]
                if info["type"] == "REG_BINARY":
                    value = bytes.fromhex(value)
                elif info["type"] == "REG_DWORD" and isinstance(value, str):
                    value = int(value)
                set_registry_value(root, sub, name, value, reg_type)
            except Exception as e:
                messagebox.showerror("Ошибка импорта", f"Не удалось записать:\nПуть: {full_path}\\{name}\nОшибка: {e}")
                return False
    return True

# --- Основной класс GUI ---
class ISTARegFoxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISTA RegFox 🦊")
        self.root.geometry("600x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#f9f9f9")

        # Заголовок
        title_font = ("Arial Rounded MT Bold", 20, "bold")
        title = tk.Label(
            root,
            text="ISTA RegFox 🦊",
            font=title_font,
            fg="#ff6b35",
            bg="#f9f9f9"
        )
        title.pack(pady=(15, 5))

        # Статус
        self.status_var = tk.StringVar(value="Поиск ISTA...")
        status_label = tk.Label(
            root,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            fg="#555",
            bg="#f9f9f9"
        )
        status_label.pack(pady=(0, 10))

        # Кнопки
        button_frame = tk.Frame(root, bg="#f9f9f9")
        button_frame.pack(pady=10)

        buttons_info = [
            ("📥 Сохранить настройки в файл", self.save_settings, "#42a5f5"),
            ("📤 Загрузить настройки из файла", self.load_settings, "#42a5f5"),
            ("✅ Активировать режим программирования", self.activate_programming, "#66bb6a"),
            ("❌ Деактивировать режим программирования", self.deactivate_programming, "#ef5350"),
            ("⏪ Сбросить запоминание настроек", self.reset_cache, "#bdbdbd")
        ]

        self.buttons = []
        for text, command, color in buttons_info:
            btn = tk.Button(
                button_frame,
                text=text,
                command=command,
                font=("Segoe UI", 10, "bold"),
                bg="white",
                fg="black",
                activebackground="#ffb74d",
                activeforeground="black",
                relief="flat",
                padx=20,
                pady=8,
                bd=1,
                highlightthickness=0,
                cursor="hand2"
            )
            btn.pack(fill="x", padx=30, pady=5)
            self.buttons.append(btn)

            btn.bind("<Enter>", lambda e, b=btn: self.on_hover(e, b))
            btn.bind("<Leave>", lambda e, b=btn: self.on_leave(e, b))

        self.cache = load_cache()
        self.ista_flavors = find_ista_flavors()
        self.update_status()

    def on_hover(self, event, button):
        button.config(bg="#ffe0b2")

    def on_leave(self, event, button):
        button.config(bg="white")

    def update_status(self):
        if not self.ista_flavors:
            self.status_var.set("❗ ISTA не найдена в реестре")
            for btn in self.buttons[2:4]:
                btn.config(state="disabled")
        elif len(self.ista_flavors) == 1:
            flavor = "Новая ISTA" if self.ista_flavors[0] == "new" else "Старая ISTA"
            self.status_var.set(f"✅ Найдено: {flavor}")
            for btn in self.buttons[2:4]:
                btn.config(state="normal")
        else:
            self.status_var.set("✅ Найдено: Новая и Старая ISTA")
            for btn in self.buttons[2:4]:
                btn.config(state="normal")

    def save_settings(self):
        if not self.ista_flavors:
            messagebox.showwarning("Предупреждение", "ISTA не найдена. Нечего сохранять.")
            return

        data = {}
        for flavor in self.ista_flavors:
            data.update(read_entire_ista_tree(flavor))

        if not data:
            messagebox.showinfo("Информация", "Нет данных для сохранения.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить настройки ISTA",
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Успех", f"Настройки сохранены в:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def load_settings(self):
        file_path = filedialog.askopenfilename(
            title="Загрузить настройки ISTA",
            filetypes=[("JSON файлы", "*.json")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if write_registry_from_json(data):
                messagebox.showinfo("Успех", "Настройки успешно восстановлены!")
                self.ista_flavors = find_ista_flavors()
                self.update_status()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")

    def choose_flavor(self):
        if len(self.ista_flavors) == 1:
            return self.ista_flavors[0]

        flavor = None
        dialog = tk.Toplevel(self.root)
        dialog.title("Выберите версию ISTA")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Найдено несколько версий ISTA:", font=("Segoe UI", 10)).pack(pady=10)
        var = tk.StringVar(value=self.ista_flavors[0])

        for f in self.ista_flavors:
            text = "Новая ISTA" if f == "new" else "Старая ISTA"
            tk.Radiobutton(dialog, text=text, variable=var, value=f, font=("Segoe UI", 10)).pack()

        def submit():
            nonlocal flavor
            flavor = var.get()
            dialog.destroy()

        tk.Button(dialog, text="Далее", command=submit, bg="#ff6b35", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=15)
        self.root.wait_window(dialog)
        return flavor

    def get_swi_version(self, current=None):
        version = current or DEFAULT_SWI_VERSION
        user_version = None

        dialog = tk.Toplevel(self.root)
        dialog.title("Версия ISTA")
        dialog.geometry("350x140")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Укажите версию ISTA:", font=("Segoe UI", 10)).pack(pady=10)
        entry = tk.Entry(dialog, font=("Segoe UI", 10), justify="center")
        entry.insert(0, version)
        entry.pack(pady=5)
        entry.focus()

        def submit():
            nonlocal user_version
            user_version = entry.get().strip()
            if user_version:
                dialog.destroy()
            else:
                messagebox.showwarning("Ошибка", "Версия не может быть пустой.")

        tk.Button(dialog, text="OK", command=submit, bg="#66bb6a", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=10)
        self.root.wait_window(dialog)
        return user_version

    def choose_psdz_type(self):
        cached = self.cache.get("psdz_choice")
        if cached in ("factory", "external"):
            return cached, self.cache.get("psdz_external_path")

        choice = None
        path_holder = [None]

        dialog = tk.Toplevel(self.root)
        dialog.title("Тип psdzdata")
        dialog.geometry("400x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Какой тип psdzdata вы используете?", font=("Segoe UI", 10)).pack(pady=10)

        var = tk.StringVar(value="factory")

        tk.Radiobutton(dialog, text="Заводская (data или data_swi внутри ISTA)", variable=var, value="factory", font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        tk.Radiobutton(dialog, text="Полная внешняя psdzdata (на USB/диске)", variable=var, value="external", font=("Segoe UI", 10)).pack(anchor="w", padx=30)

        browse_button = tk.Button(
            dialog,
            text="Выбрать папку...",
            command=lambda: self.browse_external_path(path_holder),
            state="disabled",
            font=("Segoe UI", 9)
        )
        browse_button.pack(pady=5)

        def toggle_browse():
            if var.get() == "external":
                browse_button.config(state="normal")
            else:
                browse_button.config(state="disabled")

        var.trace("w", lambda *args: toggle_browse())

        def submit():
            nonlocal choice
            choice = var.get()
            dialog.destroy()

        tk.Button(dialog, text="OK", command=submit, bg="#ff6b35", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=10)
        self.root.wait_window(dialog)

        self.cache["psdz_choice"] = choice
        if path_holder[0]:
            self.cache["psdz_external_path"] = path_holder[0]
        save_cache(self.cache)

        return choice, path_holder[0]

    def browse_external_path(self, path_holder):
        folder = filedialog.askdirectory(title="Выберите папку с полной psdzdata")
        if folder:
            path_holder[0] = folder

    def choose_factory_folder(self):
        cached = self.cache.get("factory_psdz_folder")
        if cached in ("data", "data_swi"):
            return cached

        folder = None
        dialog = tk.Toplevel(self.root)
        dialog.title("Заводская папка psdzdata")
        dialog.geometry("350x160")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Где лежит заводская psdzdata?", font=("Segoe UI", 10)).pack(pady=10)
        var = tk.StringVar(value="data_swi")

        tk.Radiobutton(dialog, text="В папке data_swi", variable=var, value="data_swi", font=("Segoe UI", 10)).pack()
        tk.Radiobutton(dialog, text="В папке data", variable=var, value="data", font=("Segoe UI", 10)).pack()

        def submit():
            nonlocal folder
            folder = var.get()
            dialog.destroy()

        tk.Button(dialog, text="OK", command=submit, bg="#ff6b35", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=15)
        self.root.wait_window(dialog)

        self.cache["factory_psdz_folder"] = folder
        save_cache(self.cache)
        return folder

    def activate_programming(self):
        if not self.ista_flavors:
            messagebox.showwarning("Ошибка", "ISTA не найдена.")
            return

        flavor = self.choose_flavor()
        if not flavor:
            return

        base_key = BMW_KEYS[flavor]
        swi_val, _ = read_registry_value(base_key, ISTA_SUBKEY, "SWIData")
        if swi_val is None:
            swi_val = self.get_swi_version()
            if not swi_val:
                return
            if not set_registry_value(base_key, ISTA_SUBKEY, "SWIData", swi_val):
                return

        psdz_choice, external_path = self.choose_psdz_type()
        if psdz_choice == "external":
            if not external_path:
                messagebox.showwarning("Ошибка", "Путь к внешней psdzdata не выбран.")
                return
            psdz_path = external_path
        else:
            folder = self.choose_factory_folder()
            psdz_path = f"{PSDZ_BASE_REL}\\{folder}"

        success = True
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.Enabled", "true")
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.ExpertMode", "true")
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.PsdzDataPath", psdz_path)

        if success:
            messagebox.showinfo("Готово!", "✅ Режим программирования активирован!")
            self.cache["last_psdz_path"] = psdz_path
            save_cache(self.cache)

    def deactivate_programming(self):
        if not self.ista_flavors:
            messagebox.showwarning("Ошибка", "ISTA не найдена.")
            return

        flavor = self.choose_flavor()
        if not flavor:
            return

        base_key = BMW_KEYS[flavor]

        # Получаем сохранённый выбор
        folder = self.cache.get("factory_psdz_folder")
        if folder not in ("data", "data_swi"):
            # Если не выбрано — спрашиваем у пользователя
            folder = self.choose_factory_folder()
            if not folder:
                messagebox.showwarning("Отмена", "Деактивация отменена: не выбрана папка psdzdata.")
                return

        psdz_path = f"{PSDZ_BASE_REL}\\{folder}"

        success = True
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.PsdzDataPath", psdz_path)
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.Enabled", "false")
        success &= set_registry_value(base_key, RHEINGOLD_SUBKEY, "BMW.Rheingold.Programming.ExpertMode", "false")

        if success:
            messagebox.showinfo("Готово!", "❌ Режим программирования деактивирован!")

    def reset_cache(self):
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        self.cache = {}
        messagebox.showinfo("Сброс", "Настройки сброшены. Перезапустите программу.")

# --- Точка входа ---
if __name__ == "__main__":
    if not is_admin():
        restart_as_admin()

    ensure_cache_dir()

    root = tk.Tk()
    app = ISTARegFoxApp(root)
    root.mainloop()
