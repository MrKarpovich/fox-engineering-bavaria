#!/usr/bin/env python3
"""
FOX — BMW FA XML Comparator
Сравнение множественных XML-файлов с поддержкой пространств имён.
Python 3.13 совместимо, только стандартная библиотека.
PEP 8 compliant.
"""

import xml.etree.ElementTree as ET
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from collections import defaultdict
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────────────────────
BMW_NS = {'ns1': 'http://bmw.com/2005/psdz.data.fa'}
NS_PREFIX = '{http://bmw.com/2005/psdz.data.fa}'
CODE_TYPES = ['eCode', 'saCode', 'hoCode']

# Цветовая схема (современная, доступная)
COLORS = {
    'bg': '#1e1e2e',
    'surface': '#2a2a3e',
    'primary': '#89b4fa',
    'success': '#a6e3a1',
    'warning': '#f9e2af',
    'error': '#f38ba8',
    'text': '#cdd6f4',
    'text_dim': '#a6adc8',
    'highlight': '#45475a',
}


# ─────────────────────────────────────────────────────────────
# Логика обработки XML
# ─────────────────────────────────────────────────────────────
def parse_xml(file_path: str | Path) -> ET.Element | None:
    """Разобрать XML-файл и вернуть корневой элемент."""
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except ET.ParseError:
        return None
    except FileNotFoundError:
        return None


def extract_codes(root: ET.Element, tag_name: str) -> set[str]:
    """Извлечь все значения кодов из элементов с указанным именем тега."""
    codes = set()
    xpath = f'.//{NS_PREFIX}{tag_name}'
    for elem in root.iterfind(xpath, BMW_NS):
        if elem.text and (code := elem.text.strip()):
            codes.add(code)
    return codes


def extract_header_info(root: ET.Element) -> dict[str, str]:
    """Извлечь VIN и метаданные из заголовка."""
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
    """Сравнить два XML-корня и вернуть структурированные различия."""
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
        self.root.title("🦊 FOX — Сравнение FA XML")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS['bg'])

        # Центрировать окно
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Primary.TButton',
                        background=COLORS['primary'],
                        foreground='#11111b',
                        font=('Segoe UI', 10, 'bold'))
        style.configure('Danger.TButton',
                        background=COLORS['error'],
                        foreground='#11111b',
                        font=('Segoe UI', 10))
        style.configure('Surface.TFrame', background=COLORS['surface'])
        style.configure('Header.TLabel',
                        background=COLORS['bg'],
                        foreground=COLORS['primary'],
                        font=('Segoe UI', 12, 'bold'))
        style.configure('Body.TLabel',
                        background=COLORS['bg'],
                        foreground=COLORS['text'])
        style.configure('Dim.TLabel',
                        background=COLORS['bg'],
                        foreground=COLORS['text_dim'])
        style.configure('Result.Treeview',
                        background=COLORS['surface'],
                        foreground=COLORS['text'],
                        fieldbackground=COLORS['surface'],
                        borderwidth=0)
        style.map('Primary.TButton',
                  background=[('active', '#74c7ec')])

    def _build_ui(self):
        # Главный контейнер
        main_frame = ttk.Frame(self.root, style='Surface.TFrame', padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        header = ttk.Label(main_frame,
                           text="🦊 FOX — Сравнение BMW FA XML",
                           style='Header.TLabel')
        header.pack(pady=(0, 15))

        # Секция выбора файлов
        file_frame = ttk.LabelFrame(main_frame, text="📁 Выбранные файлы", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        # Список файлов с прокруткой
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.X)

        self.file_listbox = tk.Listbox(
            list_frame,
            height=6,
            bg=COLORS['surface'],
            fg=COLORS['text'],
            selectbackground=COLORS['highlight'],
            selectforeground=COLORS['text'],
            activestyle='none',
            font=('Consolas', 9),
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=COLORS['highlight']
        )
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=list_scroll.set)

        self.file_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления файлами
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="➕ Добавить файлы...", command=self._add_files, width=20).pack(side=tk.LEFT,
                                                                                                  padx=(0, 5))
        ttk.Button(btn_frame, text="🗑️ Удалить выбранные", command=self._remove_selected, width=20).pack(side=tk.LEFT,
                                                                                                         padx=(0, 5))
        ttk.Button(btn_frame, text="🔄 Очистить всё", command=self._clear_all, width=15).pack(side=tk.LEFT)

        # Выбор базового файла
        base_frame = ttk.Frame(main_frame)
        base_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(base_frame, text="🎯 Сравнивать с:", style='Body.TLabel').pack(side=tk.LEFT)
        self.base_var = tk.StringVar(value="—")
        self.base_combo = ttk.Combobox(
            base_frame,
            textvariable=self.base_var,
            state='readonly',
            width=55,
            font=('Consolas', 9)
        )
        self.base_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.base_combo.bind('<<ComboboxSelected>>', self._on_base_changed)

        # Кнопка сравнения
        compare_btn = ttk.Button(
            main_frame,
            text="▶️ СРАВНИТЬ ФАЙЛЫ",
            command=self._run_comparison,
            style='Primary.TButton'
        )
        compare_btn.pack(pady=(10, 15), ipady=5)

        # Секция результатов
        results_frame = ttk.LabelFrame(main_frame, text="📊 Результаты сравнения", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            bg=COLORS['surface'],
            fg=COLORS['text'],
            font=('Consolas', 9),
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=COLORS['highlight'],
            padx=10,
            pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Настройка тегов для цветного вывода
        self.results_text.tag_configure('header', foreground=COLORS['primary'], font=('Consolas', 10, 'bold'))
        self.results_text.tag_configure('success', foreground=COLORS['success'])
        self.results_text.tag_configure('warning', foreground=COLORS['warning'])
        self.results_text.tag_configure('error', foreground=COLORS['error'])
        self.results_text.tag_configure('dim', foreground=COLORS['text_dim'])
        self.results_text.tag_configure('code', foreground='#fab387')

        # Строка состояния
        self.status_var = tk.StringVar(value="Готово — Выберите XML-файлы для начала")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style='Dim.TLabel', anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(15, 0))

    def _add_files(self):
        """Открыть диалог выбора файлов и добавить выбранные XML."""
        filetypes = [('XML-файлы', '*.xml'), ('Все файлы', '*.*')]
        new_files = filedialog.askopenfilenames(
            title="Выберите BMW FA XML-файлы",
            filetypes=filetypes,
            initialdir=str(Path.home())
        )

        for file in new_files:
            path = Path(file)
            if path not in self.files:
                self.files.append(path)
                self.file_listbox.insert(tk.END, f"• {path.name}")

        self._update_base_selector()
        if self.files:
            self.status_var.set(f"✓ Загружено файлов: {len(self.files)}")

    def _remove_selected(self):
        """Удалить выбранные файлы из списка."""
        selection = self.file_listbox.curselection()
        if not selection:
            return

        for idx in reversed(selection):
            del self.files[idx]
            self.file_listbox.delete(idx)

        self._update_base_selector()
        self.status_var.set(
            f"✓ Осталось файлов: {len(self.files)}" if self.files else "Готово — Выберите XML-файлы для начала")

    def _clear_all(self):
        """Очистить все выбранные файлы."""
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.base_var.set("—")
        self.base_combo['values'] = []
        self.results_text.delete('1.0', tk.END)
        self.status_var.set("Готово — Выберите XML-файлы для начала")

    def _update_base_selector(self):
        """Обновить комбобокс выбора базового файла."""
        names = [f"{i + 1}. {p.name}" for i, p in enumerate(self.files)]
        self.base_combo['values'] = names
        if self.files and (self.base_file_index >= len(self.files)):
            self.base_file_index = 0
        if self.files:
            self.base_var.set(names[self.base_file_index])

    def _on_base_changed(self, event=None):
        """Обработать изменение выбора базового файла."""
        selection = self.base_combo.current()
        if selection >= 0:
            self.base_file_index = selection

    def _run_comparison(self):
        """Выполнить сравнение и отобразить результаты."""
        if len(self.files) < 2:
            messagebox.showwarning("⚠️ Недостаточно файлов",
                                   "Пожалуйста, выберите минимум 2 XML-файла для сравнения.",
                                   parent=self.root)
            return

        base_path = self.files[self.base_file_index]
        base_root = parse_xml(base_path)

        if base_root is None:
            messagebox.showerror("❌ Ошибка разбора",
                                 f"Не удалось обработать базовый файл:\n{base_path.name}",
                                 parent=self.root)
            return

        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, f"🔍 Сравнение {len(self.files) - 1} файл(ов) с:\n", 'header')
        self.results_text.insert(tk.END, f"   {base_path.name}\n\n", 'code')

        total_diffs = 0

        for i, target_path in enumerate(self.files):
            if i == self.base_file_index:
                continue

            target_root = parse_xml(target_path)
            if target_root is None:
                self.results_text.insert(tk.END, f"⚠️  {target_path.name}: Ошибка разбора файла\n", 'warning')
                continue

            # Показать информацию из заголовков
            info_base = extract_header_info(base_root)
            info_target = extract_header_info(target_root)

            self.results_text.insert(tk.END, f"\n📄 {target_path.name}\n", 'header')
            self.results_text.insert(tk.END, f"   VIN: {info_target['vin']} | Серия: {info_target['series']}\n", 'dim')

            # Сравнить
            diff = compare_files(base_root, target_root)

            if diff['identical']:
                self.results_text.insert(tk.END, "   ✅ Все коды совпадают\n", 'success')
            else:
                total_diffs += 1
                for code_type, changes in diff['differences'].items():
                    if changes['missing']:
                        self.results_text.insert(tk.END, f"   ➖ Отсутствуют {code_type}: ", 'error')
                        self.results_text.insert(tk.END, ", ".join(changes['missing']) + "\n", 'code')
                    if changes['extra']:
                        self.results_text.insert(tk.END, f"   ➕ Добавлены {code_type}: ", 'success')
                        self.results_text.insert(tk.END, ", ".join(changes['extra']) + "\n", 'code')

        # Итог
        self.results_text.insert(tk.END, "\n" + "─" * 50 + "\n", 'dim')
        if total_diffs == 0:
            self.results_text.insert(tk.END, "🎉 Все файлы идентичны!\n", 'success')
            self.status_var.set("✓ Сравнение завершено — Различий не найдено")
        else:
            self.results_text.insert(tk.END, f"⚠️  Найдены различия в {total_diffs} файл(ах)\n", 'warning')
            self.status_var.set(f"✓ Сравнение завершено — {total_diffs} файл(ов) с различиями")

        self.results_text.see(tk.END)


# ─────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = FOXComparatorApp(root)
    root.mainloop()


if __name__ == '__main__':
    # Включить DPI-awareness на Windows для чёткого интерфейса
    if sys.platform == 'win32':
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    sys.exit(main())
