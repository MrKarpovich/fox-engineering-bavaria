import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser
import re
from pathlib import Path

# === Настройки ===
SCRIPT_DIR = Path(__file__).parent
CODES_FILE = SCRIPT_DIR / "defect-code-info.txt"


# === Загрузка кодов ===
def load_defect_codes():
    if not CODES_FILE.exists():
        return {}
    try:
        content = CODES_FILE.read_text(encoding="utf-8")
        matches = re.findall(r"'([^']+)':\s*{\s*defectCodeDescription:\s*'([^']+)'", content)
        return {key.strip(): desc.strip() for key, desc in matches}
    except Exception:
        return {}


DEFECT_CODES = load_defect_codes()

# === Языки ===
LANG = {
    "en": {
        "title": "🦊 FoxRecalls",
        "label_input": "Enter defect codes (e.g. 0011200700, 0011350700):",
        "btn_search": "🔍 Search",
        "btn_eu": "🇪🇺 Check VIN — BMW EU",
        "btn_usa": "🇺🇸 Check VIN — BMW USA",
        "not_found": "❌ Not found",
        "results": "🔍 Results:",
        "lang_switch": "🌐 Русский",
        "eu_url": "https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html",
        "usa_url": "https://www.bmwusa.com/safety-and-emission-recalls.html",
        "disclaimer": "It's important:\n"
                      "- For cars originally sold in the USA, use the BMW USA portal.\n"
                      "- For cars originally sold in Europe, use the BMW Europe portal.\n"
                      "- Imported cars do NOT participate in technical promotions,\n"
                      " even if the code is displayed in the system.\n"
                      "- Technical promotions are valid ONLY for cars:\n" 
                      "sold through official BMW dealer networks in the relevant region."
    },
    "ru": {
        "title": "🦊 FoxRecalls",
        "label_input": "Введите коды неисправностей (напр. 0011200700, 0011350700):",
        "btn_search": "🔍 Поиск",
        "btn_eu": "🇪🇺 Проверить VIN — BMW Европа",
        "btn_usa": "🇺🇸 Проверить VIN — BMW США",
        "not_found": "❌ Не найдено",
        "results": "🔍 Результаты:",
        "lang_switch": "🌐 English",
        "eu_url": "https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html",
        "usa_url": "https://www.bmwusa.com/safety-and-emission-recalls.html",
        "disclaimer": "Важно:\n"
                      "- Для автомобилей, изначально проданных в США, используйте портал BMW США.\n"
                      "- Для автомобилей, изначально проданных в Европе, используйте портал BMW Европа.\n"
                      "- Импортированные автомобили НЕ участвуют в технических акциях,\n"
                      " даже если код отображается в системе.\n"
                      "- Технические акции действуют ТОЛЬКО для автомобилей:\n, проданных через официальные "
                      "дилерские сети BMW в соответствующем регионе."
    }
}


class FoxRecallsApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "en"
        self.setup_ui()
        self.update_lang()

    def setup_ui(self):
        self.root.title("🦊 FoxRecalls")
        self.root.geometry("600x600")
        self.root.resizable(True, True)
        self.root.configure(bg="#fdf6e3")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", background="#ff7f0e", foreground="white")
        style.map("Accent.TButton", background=[("active", "#ff5f00")])

        # Верхняя панель — язык
        self.lang_btn = ttk.Button(self.root, text="🌐 Русский", command=self.toggle_lang)
        self.lang_btn.pack(pady=(10, 5), padx=10, anchor="ne")

        # Поле ввода
        self.label = tk.Label(self.root, text="", font=("Segoe UI", 10), bg="#fdf6e3", fg="#586e75")
        self.label.pack(pady=(10, 5))

        self.entry = tk.Entry(self.root, font=("Segoe UI", 11), width=60, relief="flat", bg="#eee8d5")
        self.entry.pack(pady=5)

        # Кнопка поиска
        self.search_btn = ttk.Button(self.root, text="🔍 Search", style="Accent.TButton", command=self.search)
        self.search_btn.pack(pady=10)

        # Результаты
        self.result_label = tk.Label(self.root, text="", font=("Segoe UI", 10, "bold"), bg="#fdf6e3", fg="#268bd2")
        self.result_label.pack(pady=(10, 5))

        self.result_text = scrolledtext.ScrolledText(
            self.root, width=70, height=10, font=("Consolas", 10),
            bg="#eee8d5", relief="flat", wrap=tk.WORD
        )
        self.result_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Кнопки ссылок
        btn_frame = tk.Frame(self.root, bg="#fdf6e3")
        btn_frame.pack(pady=10)

        self.btn_eu = ttk.Button(btn_frame, text="🇪🇺 Check VIN — BMW EU", command=self.open_eu)
        self.btn_eu.pack(side="left", padx=5)

        self.btn_usa = ttk.Button(btn_frame, text="🇺🇸 Check VIN — BMW USA", command=self.open_usa)
        self.btn_usa.pack(side="left", padx=5)

        # Disclaimer
        self.disclaimer_label = tk.Label(
            self.root, text="", font=("Segoe UI", 8),
            bg="#fdf6e3", fg="#dc322f", justify="center"
        )
        self.disclaimer_label.pack(pady=5)

    def toggle_lang(self):
        self.current_lang = "ru" if self.current_lang == "en" else "en"
        self.update_lang()

    def update_lang(self):
        L = LANG[self.current_lang]
        self.root.title(L["title"])
        self.label.config(text=L["label_input"])
        self.search_btn.config(text=L["btn_search"])
        self.lang_btn.config(text=L["lang_switch"])
        self.btn_eu.config(text=L["btn_eu"])
        self.btn_usa.config(text=L["btn_usa"])
        self.result_label.config(text=L["results"])
        self.disclaimer_label.config(text=L["disclaimer"])

    def open_eu(self):
        webbrowser.open_new_tab(LANG[self.current_lang]["eu_url"])

    def open_usa(self):
        webbrowser.open_new_tab(LANG[self.current_lang]["usa_url"])

    def search(self):
        text = self.entry.get().strip()
        if not text:
            return

        codes = [c.strip() for c in text.split(",") if c.strip()]
        results = []
        for code in codes:
            desc = DEFECT_CODES.get(code, LANG[self.current_lang]["not_found"])
            results.append(f"{code}: {desc}")

        self.result_text.config(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "\n".join(results))
        self.result_text.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = FoxRecallsApp(root)
    root.mainloop()
