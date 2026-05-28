#!/usr/bin/env python3
"""
🦊 FOX — BMW FA XML Comparator
Сравнение с расшифровкой кодов (логика как в твоём JS-скрипте).
Python 3.13, только стандартная библиотека.
"""

import xml.etree.ElementTree as ET
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────────────────────
BMW_NS = {'ns1': 'http://bmw.com/2005/psdz.data.fa'}
NS_PREFIX = '{http://bmw.com/2005/psdz.data.fa}'
CODE_TYPES = ['eCode', 'saCode', 'hoCode']
CODES_FILE = 'bmwcodes.txt'

COLORS = {
    'bg': '#1e1e2e', 'surface': '#2a2a3e', 'primary': '#89b4fa',
    'success': '#a6e3a1', 'warning': '#f9e2af', 'error': '#f38ba8',
    'text': '#cdd6f4', 'text_dim': '#a6adc8', 'highlight': '#45475a',
}

BMW_CODES_DB: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────
# Загрузка и поиск кодов (как в твоём JS)
# ─────────────────────────────────────────────────────────────
def load_code_database() -> bool:
    """Загрузить bmwcodes.txt: первое слово = код, остальное = описание."""
    global BMW_CODES_DB
    codes_path = Path(__file__).parent / CODES_FILE

    if not codes_path.exists():
        return False

    try:
        with open(codes_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for line_sep in ['\r\n', '\n', '\r']:
                if line_sep in content:
                    lines = content.split(line_sep)
                    break
            else:
                lines = content.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                raw_code, desc = parts
                BMW_CODES_DB[raw_code.upper()] = desc
        return bool(BMW_CODES_DB)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {CODES_FILE}: {e}")
        return False


def get_code_description(code: str) -> str:
    """
    Поиск по подстроке: если искомый код содержится в коде из файла — возвращаем описание.
    Точная копия логики твоего JS: code.indexOf(inputCode) >= 0
    """
    code_upper = code.strip().upper()

    for file_code, desc in BMW_CODES_DB.items():
        if code_upper in file_code:
            return desc
        if file_code in code_upper:
            return desc

    return "⚠️ Не найдено в bmwcodes.txt"


# ─────────────────────────────────────────────────────────────
# XML-обработка
# ─────────────────────────────────────────────────────────────
def parse_xml(file_path: str | Path) -> ET.Element | None:
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except (ET.ParseError, FileNotFoundError):
        return None


def extract_codes(root: ET.Element, tag_name: str) -> set[str]:
    codes = set()
    xpath = f'.//{NS_PREFIX}{tag_name}'
    for elem in root.iterfind(xpath, BMW_NS):
        if elem.text and (code := elem.text.strip().upper()):
            codes.add(code)
    return codes


def extract_header_info(root: ET.Element) -> dict[str, str]:
    header = root.find(f'.//{NS_PREFIX}header', BMW_NS)
    if header is None:
        return {'vin': 'N/A', 'series': 'N/A'}
    parent = header.find('..')
    return {
        'vin': header.get('vinLong', 'N/A'),
        'series': parent.get('series', 'N/A') if parent is not None else 'N/A',
        'date': header.get('date', 'N/A'),
    }


def compare_files(base_root: ET.Element, target_root: ET.Element) -> dict:
    result = {'identical': True, 'differences': {}}
    for code_type in CODE_TYPES:
        base_codes = extract_codes(base_root, code_type)
        target_codes = extract_codes(target_root, code_type)
        missing = base_codes - target_codes
        extra = target_codes - base_codes
        if missing or extra:
            result['identical'] = False
            result['differences'][code_type + 's'] = {
                'missing': sorted(missing),
                'extra': sorted(extra)
            }
    return result


# ─────────────────────────────────────────────────────────────
# GUI Приложение
# ─────────────────────────────────────────────────────────────
class FOXComparatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.files: list[Path] = []
        self.base_file_index: int = 0
        self._setup_window()
        self._setup_styles()
        self._build_ui()

    def _setup_window(self):
        self.root.title("🦊 FOX — Сравнение BMW FA XML")
        self.root.geometry("1150x800")
        self.root.minsize(950, 650)
        self.root.configure(bg=COLORS['bg'])
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Primary.TButton', background=COLORS['primary'], foreground='#11111b',
                        font=('Segoe UI', 10, 'bold'))
        style.configure('Surface.TFrame', background=COLORS['surface'])
        style.configure('Header.TLabel', background=COLORS['bg'], foreground=COLORS['primary'],
                        font=('Segoe UI', 12, 'bold'))
        style.configure('Body.TLabel', background=COLORS['bg'], foreground=COLORS['text'])
        style.configure('Dim.TLabel', background=COLORS['bg'], foreground=COLORS['text_dim'])
        style.map('Primary.TButton', background=[('active', '#74c7ec')])

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, style='Surface.TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="🦊 FOX — Сравнение BMW FA XML", style='Header.TLabel').pack(pady=(0, 15))

        # ── Секция файлов ──
        file_frame = ttk.LabelFrame(main_frame, text="📁 Выбранные файлы", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.X)
        self.file_listbox = tk.Listbox(list_frame, height=5, bg=COLORS['surface'], fg=COLORS['text'],
                                       selectbackground=COLORS['highlight'], selectforeground=COLORS['text'],
                                       activestyle='none', font=('Consolas', 9), borderwidth=0,
                                       highlightthickness=1, highlightbackground=COLORS['highlight'])
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=list_scroll.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="➕ Добавить файлы...", command=self._add_files, width=20).pack(side=tk.LEFT,
                                                                                                  padx=(0, 5))
        ttk.Button(btn_frame, text="🗑️ Удалить выбранные", command=self._remove_selected, width=20).pack(side=tk.LEFT,
                                                                                                         padx=(0, 5))
        ttk.Button(btn_frame, text="🔄 Очистить всё", command=self._clear_all, width=15).pack(side=tk.LEFT)

        base_frame = ttk.Frame(main_frame)
        base_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(base_frame, text="🎯 Сравнивать с:", style='Body.TLabel').pack(side=tk.LEFT)
        self.base_var = tk.StringVar(value="—")
        self.base_combo = ttk.Combobox(base_frame, textvariable=self.base_var, state='readonly', width=55,
                                       font=('Consolas', 9))
        self.base_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.base_combo.bind('<<ComboboxSelected>>', self._on_base_changed)

        ttk.Button(main_frame, text="▶️ СРАВНИТЬ ФАЙЛЫ", command=self._run_comparison, style='Primary.TButton').pack(
            pady=(10, 15), ipady=5)

        # ── Результаты: Таблица комплектации (УМЕНЬШЕНА) ──
        eq_frame = ttk.LabelFrame(main_frame, text="📋 Комплектация базового файла", padding=10)
        eq_frame.pack(fill=tk.X, pady=(0, 10))  # changed from fill=tk.BOTH, expand=True to fill=tk.X

        self.eq_tree = ttk.Treeview(eq_frame, columns=("code", "desc"), show="headings",
                                    height=7)  # changed from 12 to 7
        self.eq_tree.heading("code", text="Код")
        self.eq_tree.heading("desc", text="Расшифровка")
        self.eq_tree.column("code", width=110, anchor=tk.CENTER)
        self.eq_tree.column("desc", width=550, anchor=tk.W)

        eq_scroll = ttk.Scrollbar(eq_frame, orient=tk.VERTICAL, command=self.eq_tree.yview)
        self.eq_tree.configure(yscrollcommand=eq_scroll.set)
        self.eq_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)  # changed from fill=tk.BOTH
        eq_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Результаты: Различия (УВЕЛИЧЕНА) ──
        diff_frame = ttk.LabelFrame(main_frame, text="🔍 Найденные различия", padding=10)
        diff_frame.pack(fill=tk.BOTH, expand=True)  # expand=True чтобы занимала всё оставшееся место

        self.diff_text = scrolledtext.ScrolledText(diff_frame, wrap=tk.WORD, bg=COLORS['surface'], fg=COLORS['text'],
                                                   font=('Consolas', 9), borderwidth=0, highlightthickness=1,
                                                   highlightbackground=COLORS['highlight'], padx=10, pady=10)
        self.diff_text.pack(fill=tk.BOTH, expand=True)

        # Теги для подсветки
        for tag, color in [('header', COLORS['primary']), ('success', COLORS['success']),
                           ('warning', COLORS['warning']), ('error', COLORS['error']),
                           ('dim', COLORS['text_dim']), ('code', '#fab387')]:
            self.diff_text.tag_configure(tag, foreground=color)
            if tag == 'header':
                self.diff_text.tag_configure(tag, font=('Consolas', 10, 'bold'))

        self.status_var = tk.StringVar(value="Готово — Загрузите XML-файлы и bmwcodes.txt")
        ttk.Label(main_frame, textvariable=self.status_var, style='Dim.TLabel', anchor=tk.W).pack(fill=tk.X,
                                                                                                  pady=(15, 0))

        if not BMW_CODES_DB:
            self.status_var.set("⚠️ Файл bmwcodes.txt не найден. Расшифровки будут отображаться как 'Не найдено'")

    def _add_files(self):
        filetypes = [('XML-файлы', '*.xml'), ('Все файлы', '*.*')]
        new_files = filedialog.askopenfilenames(title="Выберите BMW FA XML-файлы", filetypes=filetypes,
                                                initialdir=str(Path.home()))
        for file in new_files:
            path = Path(file)
            if path not in self.files:
                self.files.append(path)
                self.file_listbox.insert(tk.END, f"• {path.name}")
        self._update_base_selector()
        if self.files:
            self.status_var.set(f"✓ Загружено файлов: {len(self.files)}")

    def _remove_selected(self):
        selection = self.file_listbox.curselection()
        if not selection: return
        for idx in reversed(selection):
            del self.files[idx]
            self.file_listbox.delete(idx)
        self._update_base_selector()
        self.status_var.set(
            f"✓ Осталось файлов: {len(self.files)}" if self.files else "Готово — Выберите XML-файлы для начала")

    def _clear_all(self):
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.base_var.set("—")
        self.base_combo['values'] = []
        self.eq_tree.delete(*self.eq_tree.get_children())
        self.diff_text.delete('1.0', tk.END)
        self.status_var.set("Готово — Выберите XML-файлы для начала")

    def _update_base_selector(self):
        names = [f"{i + 1}. {p.name}" for i, p in enumerate(self.files)]
        self.base_combo['values'] = names
        if self.files and (self.base_file_index >= len(self.files)):
            self.base_file_index = 0
        if self.files:
            self.base_var.set(names[self.base_file_index])

    def _on_base_changed(self, event=None):
        selection = self.base_combo.current()
        if selection >= 0:
            self.base_file_index = selection

    def _run_comparison(self):
        if len(self.files) < 2:
            messagebox.showwarning("⚠️ Недостаточно файлов", "Выберите минимум 2 XML-файла.", parent=self.root)
            return

        base_path = self.files[self.base_file_index]
        base_root = parse_xml(base_path)
        if base_root is None:
            messagebox.showerror("❌ Ошибка разбора", f"Не удалось обработать:\n{base_path.name}", parent=self.root)
            return

        self.eq_tree.delete(*self.eq_tree.get_children())
        self.diff_text.delete('1.0', tk.END)

        # Заполнение таблицы
        all_base_codes = set()
        for code_type in CODE_TYPES:
            all_base_codes.update(extract_codes(base_root, code_type))

        for code in sorted(all_base_codes):
            desc = get_code_description(code)
            self.eq_tree.insert('', tk.END, values=(code, desc))

        self.diff_text.insert(tk.END, f"🔍 Сравнение {len(self.files) - 1} файл(ов) с:\n", 'header')
        self.diff_text.insert(tk.END, f"   {base_path.name}\n\n", 'code')

        total_diffs = 0

        for i, target_path in enumerate(self.files):
            if i == self.base_file_index: continue
            target_root = parse_xml(target_path)
            if target_root is None:
                self.diff_text.insert(tk.END, f"⚠️  {target_path.name}: Ошибка разбора\n", 'warning')
                continue

            info_target = extract_header_info(target_root)
            self.diff_text.insert(tk.END, f"\n📄 {target_path.name}\n", 'header')
            self.diff_text.insert(tk.END, f"   VIN: {info_target['vin']} | Серия: {info_target['series']}\n", 'dim')

            diff = compare_files(base_root, target_root)

            if diff['identical']:
                self.diff_text.insert(tk.END, "   ✅ Все коды совпадают\n", 'success')
            else:
                total_diffs += 1
                for code_type, changes in diff['differences'].items():
                    if changes['missing']:
                        self.diff_text.insert(tk.END, f"   ➖ Отсутствуют {code_type}:\n", 'error')
                        for c in changes['missing']:
                            desc = get_code_description(c)
                            self.diff_text.insert(tk.END, f"      {c} — {desc}\n", 'code')
                    if changes['extra']:
                        self.diff_text.insert(tk.END, f"   ➕ Добавлены {code_type}:\n", 'success')
                        for c in changes['extra']:
                            desc = get_code_description(c)
                            self.diff_text.insert(tk.END, f"      {c} — {desc}\n", 'code')

        self.diff_text.insert(tk.END, "\n" + "─" * 50 + "\n", 'dim')
        if total_diffs == 0:
            self.diff_text.insert(tk.END, "🎉 Все файлы идентичны!\n", 'success')
            self.status_var.set("✓ Сравнение завершено — Различий не найдено")
        else:
            self.diff_text.insert(tk.END, f"⚠️  Найдены различия в {total_diffs} файл(ах)\n", 'warning')
            self.status_var.set(f"✓ Сравнение завершено — {total_diffs} файл(ов) с различиями")

        self.diff_text.see(tk.END)


# ─────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────
def main():
    if load_code_database():
        print(f"✓ Загружено {len(BMW_CODES_DB)} кодов из {CODES_FILE}")
    else:
        print(f"⚠️ Файл {CODES_FILE} не найден в директории скрипта.")

    root = tk.Tk()
    app = FOXComparatorApp(root)
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root.mainloop()


if __name__ == '__main__':
    sys.exit(main())
