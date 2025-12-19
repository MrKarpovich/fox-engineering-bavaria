"""
BMW i3 LED Pattern Designer — 2026 Edition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tool for generating LED control patterns for BMW i3 (2013–2021) charging port lighting.

Author: JluceHok_u3_MuHcka
Year: 2026
License: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

# === CORE FUNCTION: GENERATE LEDpatterns2 EXACTLY LIKE WE DID MANUALLY ===

def generate_ledpatterns2(r, g, b):
    """Generate static LED pattern EXACTLY like we did manually today."""
    # Базовый белый паттерн (22 байта) — заводской BMW i3
    WHITE_PATTERN = [
        0x00, 0x00, 0x0C, 0x17, 0x3A, 0x73, 0xAD, 0xE6,  # красный (8)
        0x00, 0x0D, 0x1A, 0x40, 0x80, 0xBF, 0xFF,        # зелёный (7)
        0x00, 0x0A, 0x14, 0x32, 0x64, 0x96, 0xC8         # синий (7)
    ]

    rf = r / 255.0
    gf = g / 255.0
    bf = b / 255.0

    result = []
    # Красный: байты 0–7
    for i in range(8):
        result.append(int(round(WHITE_PATTERN[i] * rf)))
    # Зелёный: байты 8–14
    for i in range(8, 15):
        result.append(int(round(WHITE_PATTERN[i] * gf)))
    # Синий: байты 15–21
    for i in range(15, 22):
        result.append(int(round(WHITE_PATTERN[i] * bf)))

    # Clamp to 0–255
    result = [min(255, max(0, x)) for x in result]
    return ', '.join(f'{x:02X}' for x in result)

# === ANIMATION: ONLY ONE MODE (breathing) ===

def generate_breathing(r, g, b):
    """Smooth breathing animation (47 bytes) — your peach→pink→purple style."""
    # Header
    header = [0x14, 0x96]

    # Red pulse (24 bytes) — from your manual example
    RED_PULSE = [
        0x00, 0x0A, 0x14, 0x1E, 0x3C, 0x46, 0x50, 0x5A,
        0x64, 0x6E, 0x82, 0x96, 0xFF, 0xF8, 0xE5, 0xC8,
        0x60, 0x44, 0x2D, 0x1D, 0x11, 0x0A, 0x03, 0x01
    ]
    red_scaled = [min(255, int(round(v * r / 255))) for v in RED_PULSE]

    # Separator
    sep = [0x00]

    # Green static (6 bytes)
    GREEN_STATIC = [0x0D, 0x1A, 0x40, 0x80, 0xBF, 0xFF]
    green_scaled = [min(255, int(round(v * g / 255))) for v in GREEN_STATIC]

    # Blue pulse (14 bytes)
    BLUE_PULSE = [
        0x00, 0x03, 0x06, 0x0A, 0x14, 0x1E, 0x28,
        0x28, 0x1E, 0x14, 0x0A, 0x06, 0x03, 0x00
    ]
    blue_scaled = [min(255, int(round(v * b / 255))) for v in BLUE_PULSE]

    result = header + red_scaled + sep + green_scaled + blue_scaled
    return ', '.join(f'{x:02X}' for x in result)

# === PALETTE (like MS Paint) ===
PAINT_COLORS = [
    "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#000000",
    "#800000", "#008000", "#000080", "#808000", "#800080", "#008080", "#808080", "#C0C0C0",
    "#FF8080", "#80FF80", "#8080FF", "#FFFF80", "#FF80FF", "#80FFFF", "#FFCC99", "#99FF99",
    "#9999FF", "#FFFF99", "#FF99FF", "#99FFFF", "#666666", "#333333",
    "#FF6666", "#66FF66", "#6666FF", "#FFFF66", "#FF66FF", "#66FFFF", "#FF9966", "#66FF99",
    "#6699FF", "#FFFF66", "#FF66FF", "#66FFFF", "#444444", "#222222",
    "#FF4444", "#44FF44", "#4444FF", "#FFFF44", "#FF44FF", "#44FFFF", "#FF8844", "#44FF88",
    "#4488FF", "#FFFF44", "#FF44FF", "#44FFFF", "#111111", "#000000",
]

class BMWi3LEDGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("BMW i3 LED Pattern Designer — 2026")
        self.root.geometry("900x750")
        self.root.configure(bg="#0f0f0f")

        self.mode = tk.StringVar(value="static")
        self.rgb = (255, 100, 200)  # default pink
        self.selected_color_index = -1

        self.setup_ui()

    def setup_ui(self):
        # Scrollable canvas
        main_canvas = tk.Canvas(self.root, bg="#0f0f0f", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas, padding=10)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Style
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabelframe", background="#1e1e1e", foreground="white")
        style.configure("TLabelframe.Label", background="#1e1e1e", foreground="cyan", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.map("TButton",
                  background=[('active', '#0078D4')],
                  foreground=[('active', 'white')])

        # Header
        header = ttk.Label(scrollable_frame, text="🔧 BMW i3 LED Pattern Designer — 2026",
                          font=("Segoe UI", 18, "bold"), foreground="cyan", background="#0f0f0f")
        header.pack(pady=10)

        # Mode selection
        mode_frame = ttk.LabelFrame(scrollable_frame, text="Где будет использоваться ваш свет?", padding=12)
        mode_frame.pack(padx=20, pady=10, fill='x')

        ttk.Radiobutton(
            mode_frame,
            text="🔌 Порт открыт — статический цвет (LEDpatterns2)",
            variable=self.mode,
            value="static",
            command=self.on_mode_change
        ).grid(row=0, column=0, sticky='w', pady=4)

        ttk.Label(
            mode_frame,
            text="Используется, когда зарядный порт BMW i3 открыт, но зарядка ещё не началась.\n"
                 "Свет горит ровным цветом без анимации.",
            foreground="lightgray", font=("Segoe UI", 9)
        ).grid(row=1, column=0, sticky='w', padx=20, pady=(0, 10))

        ttk.Radiobutton(
            mode_frame,
            text="⚡ Идёт зарядка — анимация (LEDpatterns1)",
            variable=self.mode,
            value="charging",
            command=self.on_mode_change
        ).grid(row=2, column=0, sticky='w', pady=4)

        ttk.Label(
            mode_frame,
            text="Используется во время зарядки. Свет плавно дышит (как в вашем примере).\n"
                 "Генерируется полноценный 47-байтный временной паттерн.",
            foreground="lightgray", font=("Segoe UI", 9)
        ).grid(row=3, column=0, sticky='w', padx=20)

        # Color palette
        color_frame = ttk.LabelFrame(scrollable_frame, text="🎨 Выберите цвет (как в Paint)", padding=10)
        color_frame.pack(padx=20, pady=10, fill='x')

        palette_frame = ttk.Frame(color_frame)
        palette_frame.pack()

        for i, color in enumerate(PAINT_COLORS):
            row = i // 8
            col = i % 8
            btn = tk.Button(
                palette_frame,
                bg=color,
                width=3,
                height=1,
                relief='raised',
                command=lambda c=color, idx=i: self.select_palette_color(c, idx)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            if i == 30:  # pinkish
                btn.config(relief='sunken')
                self.rgb = (255, 100, 200)

        # Manual color picker
        gradient_frame = ttk.Frame(color_frame)
        gradient_frame.pack(pady=10)
        ttk.Label(gradient_frame, text="Или выберите цвет вручную:", foreground="white").pack(side='left')
        ttk.Button(gradient_frame, text="Выбрать цвет...", command=self.choose_color).pack(side='left', padx=10)

        # Preview
        self.color_preview = tk.Canvas(color_frame, width=40, height=40, bg='#FF64C8', highlightthickness=1, highlightbackground='#444')
        self.color_preview.pack(pady=5)

        # Generate button
        self.generate_button = ttk.Button(scrollable_frame, text="Сгенерировать паттерны", command=self.generate_patterns)
        self.generate_button.pack(pady=15)

        # Output
        out_frame = ttk.Frame(scrollable_frame)
        out_frame.pack(fill='x', padx=20)

        ttk.Label(out_frame, text="📤 Результаты:", font=("Segoe UI", 11, "bold"), foreground="cyan").pack(anchor='w', pady=(10,5))

        ttk.Label(out_frame, text="LEDpatterns2 (статический, 22 байта):", foreground="lightblue").pack(anchor='w')
        self.text2 = tk.Text(out_frame, height=2, bg="#252526", fg="white", font=("Consolas", 10), relief='flat')
        self.text2.pack(fill='x', pady=5)

        ttk.Label(out_frame, text="LEDpatterns1 (анимация, 47 байт):", foreground="lightgreen").pack(anchor='w')
        self.text1 = tk.Text(out_frame, height=3, bg="#252526", fg="white", font=("Consolas", 10), relief='flat')
        self.text1.pack(fill='x', pady=5)

        btns = ttk.Frame(out_frame)
        btns.pack(anchor='e', pady=5)
        ttk.Button(btns, text="Копировать LEDpatterns2", command=lambda: self.copy_text(self.text2)).pack(side='left', padx=5)
        ttk.Button(btns, text="Копировать LEDpatterns1", command=lambda: self.copy_text(self.text1)).pack(side='left', padx=5)

        footer = ttk.Label(
            scrollable_frame,
            text="© 2026 JluceHok_u3_MuHcka | For BMW i3 (2013–2021) Enthusiasts",
            font=("Segoe UI", 9), foreground="gray", background="#0f0f0f"
        )
        footer.pack(side='bottom', pady=10)

        self.on_mode_change()

    def on_mode_change(self):
        text = "Сгенерировать статический цвет (LEDpatterns2)" if self.mode.get() == "static" else "Сгенерировать анимацию (LEDpatterns1)"
        self.generate_button.config(text=text)

    def select_palette_color(self, color_hex, index):
        self.selected_color_index = index
        self.rgb = self.hex_to_rgb(color_hex)
        self.color_preview.config(bg=color_hex)

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor="#FF64C8")[1]
        if color:
            self.rgb = self.hex_to_rgb(color)
            self.color_preview.config(bg=color)

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def generate_patterns(self):
        r, g, b = self.rgb
        try:
            pat2 = generate_ledpatterns2(r, g, b)
            self.text2.delete(1.0, tk.END)
            self.text2.insert(tk.END, pat2)

            if self.mode.get() == "charging":
                pat1 = generate_breathing(r, g, b)
                self.text1.delete(1.0, tk.END)
                self.text1.insert(tk.END, pat1)
            else:
                self.text1.delete(1.0, tk.END)
                self.text1.insert(tk.END, "<режим зарядки не выбран>")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def copy_text(self, widget):
        try:
            content = widget.get(1.0, tk.END).strip()
            if content and not content.startswith("<"):
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
                messagebox.showinfo("✅ Готово", "Паттерн скопирован!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BMWi3LEDGenerator(root)
    root.mainloop()
