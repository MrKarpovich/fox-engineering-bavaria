import sys
from pathlib import Path
import customtkinter as ctk
import webbrowser
import re

# Настройки внешнего вида
ctk.set_appearance_mode("light")  # Только светлая тема
ctk.set_default_color_theme("blue")  # Будем кастомизировать цвета вручную

def get_codes_file_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = Path(__file__).parent
    return Path(base_path) / "defect-code-info.txt"

def load_defect_codes():
    codes_file = get_codes_file_path()
    if not codes_file.exists():
        return {}
    try:
        content = codes_file.read_text(encoding="utf-8")
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
        "btn_eu": "🇪🇺 BMW EU",
        "btn_usa": "🇺🇸 BMW USA",
        "not_found": "❌ Not found",
        "results": "🔍 Results:",
        "lang_switch": "🌐 Русский",
        "eu_url": "https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html",
        "usa_url": "https://www.bmwusa.com/safety-and-emission-recalls.html",
        "disclaimer": (
            "ℹ️ Important:\n"
            "• For vehicles originally sold in the USA, use the BMW USA portal.\n"
            "• For vehicles originally sold in Europe, use the BMW EU portal.\n"
            "• Imported vehicles are NOT covered by technical campaigns, even if a code appears.\n"
            "• Campaigns apply ONLY to vehicles sold through official BMW dealer networks."
        )
    },
    "ru": {
        "title": "🦊 FoxRecalls",
        "label_input": "Введите коды неисправностей (напр. 0011200700, 0011350700):",
        "btn_search": "🔍 Поиск",
        "btn_eu": "🇪🇺 BMW EU",
        "btn_usa": "🇺🇸 BMW США",
        "not_found": "❌ Не найдено",
        "results": "🔍 Результаты:",
        "lang_switch": "🌐 English",
        "eu_mode": "https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html",
        "eu_url": "https://www.bmw.com.my/en/topics/bmw-owners/bmw-aftersales-services/technical-campaign.html",
        "usa_url": "https://www.bmwusa.com/safety-and-emission-recalls.html",
        "disclaimer": (
            "ℹ️ Важно:\n"
            "• Для автомобилей, изначально проданных в США, используйте портал BMW США.\n"
            "• Для автомобилей, изначально проданных в Европе, используйте портал BMW EU.\n"
            "• Импортированные автомобили НЕ участвуют в технических акциях, даже если код отображается.\n"
            "• Акции действуют ТОЛЬКО для авто, проданных через официальные дилерские сети BMW."
        )
    }
}

class FoxRecallsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_lang = "en"
        self.title("🦊 FoxRecalls")
        self.geometry("620x580")
        self.resizable(True, True)
        self.setup_ui()
        self.update_lang()

    def setup_ui(self):
        # Переключатель языка — в правом верхнем углу
        self.lang_btn = ctk.CTkButton(
            self, text="🌐 Русский", command=self.toggle_lang,
            width=80, height=24, font=("Segoe UI", 12)
        )
        self.lang_btn.pack(pady=(10, 5), padx=10, anchor="ne")

        # Метка ввода
        self.label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 14), text_color="#555"
        )
        self.label.pack(pady=(10, 5))

        # Поле ввода
        self.entry = ctk.CTkEntry(
            self, placeholder_text="0011200700, 0011350700",
            font=("Segoe UI", 14), width=500, height=36
        )
        self.entry.pack(pady=5)

        # Кнопка поиска
        self.search_btn = ctk.CTkButton(
            self, text="🔍 Search", command=self.search,
            font=("Segoe UI", 16, "bold"), width=150, height=40,
            fg_color="#ff7f0e", hover_color="#ff5f00", text_color="white"
        )
        self.search_btn.pack(pady=15)

        # Результаты
        self.result_label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 14, "bold"), text_color="#268bd2"
        )
        self.result_label.pack(pady=(10, 5))

        self.result_text = ctk.CTkTextbox(
            self, font=("Consolas", 13), width=580, height=110,
            wrap="word"
        )
        self.result_text.pack(pady=5, padx=10)

        # Кнопки ссылок
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.btn_eu = ctk.CTkButton(
            btn_frame, text="🇪🇺 BMW Malaysia", command=self.open_eu,
            font=("Segoe UI", 12), width=180, height=36,
            fg_color="#f0f0f0", text_color="#333", hover_color="#e0e0e0"
        )
        self.btn_eu.pack(side="left", padx=5)

        self.btn_usa = ctk.CTkButton(
            btn_frame, text="🇺🇸 BMW USA", command=self.open_usa,
            font=("Segoe UI", 12), width=180, height=36,
            fg_color="#f0f0f0", text_color="#333", hover_color="#e0e0e0"
        )
        self.btn_usa.pack(side="left", padx=5)

        # Disclaimer
        self.disclaimer_label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 11), text_color="#d32f2f",
            justify="left", wraplength=580
        )
        self.disclaimer_label.pack(pady=10, padx=10)

    def toggle_lang(self):
        self.current_lang = "ru" if self.current_lang == "en" else "en"
        self.update_lang()

    def update_lang(self):
        L = LANG[self.current_lang]
        self.title(L["title"])
        self.label.configure(text=L["label_input"])
        self.search_btn.configure(text=L["btn_search"])
        self.lang_btn.configure(text=L["lang_switch"])
        self.btn_eu.configure(text=L["btn_eu"])
        self.btn_usa.configure(text=L["btn_usa"])
        self.result_label.configure(text=L["results"])
        self.disclaimer_label.configure(text=L["disclaimer"])

    def open_eu(self):
        webbrowser.open_new_tab(LANG[self.current_lang]["eu_url"])

    def open_usa(self):
        webbrowser.open_new_tab(LANG[self.current_lang]["usa_url"])

    def search(self):
        raw = self.entry.get()
        if not raw or not isinstance(raw, str):
            return
        text = raw.strip()
        if not text:
            return

        codes = [c.strip() for c in text.split(",") if c.strip()]
        results = []
        for code in codes:
            desc = DEFECT_CODES.get(code, LANG[self.current_lang]["not_found"])
            results.append(f"{code}: {desc}")

        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", "\n".join(results))

if __name__ == "__main__":
    app = FoxRecallsApp()
    app.mainloop()
