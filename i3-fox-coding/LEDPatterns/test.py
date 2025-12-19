"""
BMW LED Pattern Designer — 2026 Edition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tool for generating LED control patterns for BMW i-series charging port lighting.

Author: JluceHok_u3_MuHcka
Year: 2026
License: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import sys

# === OPTIONAL DEPENDENCY: Pillow for advanced UI ===
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk, ImageDraw

    PIL_AVAILABLE = True
except ImportError:
    pass

# === BMW-APPROVED LED PROFILES (from real patterns) ===

BASE_RED_PROFILE_8 = [0x00, 0x0C, 0x17, 0x3A, 0x73, 0xAD, 0xE6, 0xFF]
BASE_GREEN_PROFILE_7 = [0x00, 0x0D, 0x1A, 0x40, 0x80, 0xBF, 0xFF]
BASE_BLUE_PROFILE_7 = [0x00, 0x0A, 0x14, 0x32, 0x64, 0x96, 0xC8]

# Breathing animation (your peach → pink → purple style)
BASE_RED_PULSE_24 = [
    0x00, 0x0A, 0x14, 0x1E, 0x3C, 0x46, 0x50, 0x5A,
    0x64, 0x6E, 0x82, 0x96, 0xFF, 0xF8, 0xE5, 0xC8,
    0x60, 0x44, 0x2D, 0x1D, 0x11, 0x0A, 0x03, 0x01
]
BASE_GREEN_STATIC_6 = [0x0D, 0x1A, 0x40, 0x80, 0xBF, 0xFF]
BASE_BLUE_PULSE_14 = [
    0x00, 0x03, 0x06, 0x0A, 0x14, 0x1E, 0x28,
    0x28, 0x1E, 0x14, 0x0A, 0x06, 0x03, 0x00
]

# Fast blink pattern
BLINK_PATTERN = [0xFF, 0xFF, 0x00, 0x00]


def hsv_to_rgb(h, s, v):
    """Convert HSV (0–1) to RGB (0–255)."""
    if s == 0.0:
        return (int(v * 255),) * 3
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    vals = [
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    ]
    r, g, b = vals[i]
    return int(r * 255), int(g * 255), int(b * 255)


def scale_profile(profile, max_val):
    """Scale profile to target max value."""
    if not profile:
        return []
    factor = max_val / 255.0
    return [min(255, int(round(v * factor))) for v in profile]


def generate_ledpatterns2(r, g, b):
    """Static pattern (22 bytes)."""
    red = scale_profile(BASE_RED_PROFILE_8, r)
    green = scale_profile(BASE_GREEN_PROFILE_7, g)
    blue = scale_profile(BASE_BLUE_PROFILE_7, b)
    result = red + green + blue
    return ', '.join(f'{x:02X}' for x in result)


def generate_breathing(r, g, b):
    """Smooth breathing (47 bytes)."""
    header = [0x14, 0x96]
    red_pulse = scale_profile(BASE_RED_PULSE_24, r)
    sep = [0x00]
    green_static = scale_profile(BASE_GREEN_STATIC_6, g)
    blue_pulse = scale_profile(BASE_BLUE_PULSE_14, b)
    result = header + red_pulse + sep + green_static + blue_pulse
    return ', '.join(f'{x:02X}' for x in result)


def generate_blinking(r, g, b):
    """Fast blinking (47 bytes)."""
    red_blink = (BLINK_PATTERN * 6)[:24]
    red = [min(255, int(v * r / 255)) for v in red_blink]
    sep = [0x00]
    green_static = scale_profile(BASE_GREEN_STATIC_6, g)
    blue_blink = (BLINK_PATTERN * 4)[:14]
    blue = [min(255, int(v * b / 255)) for v in blue_blink]
    result = [0x0A, 0x64] + red + sep + green_static + blue
    return ', '.join(f'{x:02X}' for x in result)


# === MAIN APPLICATION ===

class BMWLEDGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("BMW LED Pattern Designer — 2026")
        self.root.geometry("920x800")
        self.root.configure(bg="#0f0f0f")

        # State
        self.hue = 0.0
        self.saturation = 0.8
        self.value = 0.9
        self.rgb = hsv_to_rgb(self.hue, self.saturation, self.value)
        self.mode = tk.StringVar(value="charging")
        self.anim_mode = tk.StringVar(value="breathing")

        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabelframe", background="#1e1e1e", foreground="white")
        style.configure("TLabelframe.Label", background="#1e1e1e", foreground="cyan", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", background="#0078D4", foreground="white", font=("Segoe UI", 10))

        # Header
        header = ttk.Label(self.root, text="🔧 BMW i-Series LED Pattern Designer",
                           font=("Segoe UI", 18, "bold"), foreground="cyan", background="#0f0f0f")
        header.pack(pady=10)

        # === MODE SELECTION ===
        mode_frame = ttk.LabelFrame(self.root, text="Где будет использоваться ваш свет?", padding=12)
        mode_frame.pack(padx=20, pady=10, fill='x')

        ttk.Radiobutton(
            mode_frame,
            text="🔌 Порт открыт — статический цвет (LEDpatterns2)",
            variable=self.mode,
            value="static",
            command=self.on_mode_change
        ).pack(anchor='w', pady=4)

        ttk.Label(
            mode_frame,
            text="Используется, когда зарядный порт BMW открыт, но зарядка ещё не началась.\n"
                 "Свет горит ровным цветом без анимации.",
            foreground="lightgray", font=("Segoe UI", 9)
        ).pack(anchor='w', padx=20, pady=(0, 10))

        ttk.Radiobutton(
            mode_frame,
            text="⚡ Идёт зарядка — анимация (LEDpatterns1)",
            variable=self.mode,
            value="charging",
            command=self.on_mode_change
        ).pack(anchor='w', pady=4)

        ttk.Label(
            mode_frame,
            text="Используется во время зарядки. Свет может дышать, моргать или переливаться.\n"
                 "Генерируется полноценный 47-байтный временной паттерн.",
            foreground="lightgray", font=("Segoe UI", 9)
        ).pack(anchor='w', padx=20)

        # === COLOR PICKER ===
        color_frame = ttk.LabelFrame(self.root, text="🎨 Выберите цвет", padding=10)
        color_frame.pack(padx=20, pady=10, fill='x')

        if PIL_AVAILABLE:
            picker = ttk.Frame(color_frame)
            picker.pack()
            self.canvas_hsv = tk.Canvas(picker, width=260, height=260, bg='black', highlightthickness=0)
            self.canvas_hsv.grid(row=0, column=0, padx=5)
            self.canvas_hsv.bind("<Button-1>", self.on_hsv_click)

            self.canvas_sv = tk.Canvas(picker, width=160, height=160, bg='black', highlightthickness=0)
            self.canvas_sv.grid(row=0, column=1, padx=5)
            self.canvas_sv.bind("<Button-1>", self.on_sv_click)

            self.preview_canvas = tk.Canvas(picker, width=50, height=50, bg='#2d2d2d', highlightthickness=1,
                                            highlightbackground='#444')
            self.preview_canvas.grid(row=0, column=2, padx=5)
        else:
            fallback = ttk.Frame(color_frame)
            fallback.pack()
            self.r_var = tk.IntVar(value=255)
            self.g_var = tk.IntVar(value=100)
            self.b_var = tk.IntVar(value=200)
            for i, (name, var, col) in enumerate(
                    [('R', self.r_var, 'red'), ('G', self.g_var, 'lime'), ('B', self.b_var, 'cyan')]):
                ttk.Label(fallback, text=name, foreground=col).grid(row=i, column=0)
                ttk.Scale(fallback, from_=0, to=255, variable=var, orient='horizontal', length=250).grid(row=i,
                                                                                                         column=1,
                                                                                                         padx=10)
                ttk.Label(fallback, textvariable=var).grid(row=i, column=2)

        # === ANIMATION MODE (only for charging) ===
        self.anim_frame = ttk.LabelFrame(self.root, text="🌀 Режим анимации (только при зарядке)", padding=10)
        anim_content = ttk.Frame(self.anim_frame)
        anim_content.pack()
        ttk.Radiobutton(anim_content, text="Плавное дыхание", variable=self.anim_mode, value="breathing").pack(
            side='left', padx=10)
        ttk.Radiobutton(anim_content, text="Быстрое моргание", variable=self.anim_mode, value="blinking").pack(
            side='left', padx=10)
        self.anim_frame.pack(padx=20, pady=10, fill='x')

        # Generate button
        self.generate_button = ttk.Button(self.root, text="Сгенерировать паттерны для зарядки",
                                          command=self.generate_patterns)
        self.generate_button.pack(pady=15)

        # Output
        out_frame = ttk.Frame(self.root)
        out_frame.pack(fill='x', padx=20)

        ttk.Label(out_frame, text="📤 Результаты:", font=("Segoe UI", 11, "bold"), foreground="cyan").pack(anchor='w',
                                                                                                          pady=(10, 5))

        ttk.Label(out_frame, text="LEDpatterns2 (статический, 22 байта):", foreground="lightblue").pack(anchor='w')
        self.text2 = tk.Text(out_frame, height=2, bg="#252526", fg="white", font=("Consolas", 10), relief='flat')
        self.text2.pack(fill='x', pady=5)

        ttk.Label(out_frame, text="LEDpatterns1 (анимация, 47 байт):", foreground="lightgreen").pack(anchor='w')
        self.text1 = tk.Text(out_frame, height=3, bg="#252526", fg="white", font=("Consolas", 10), relief='flat')
        self.text1.pack(fill='x', pady=5)

        btns = ttk.Frame(out_frame)
        btns.pack(anchor='e', pady=5)
        ttk.Button(btns, text="Копировать LEDpatterns2", command=lambda: self.copy_text(self.text2)).pack(side='left',
                                                                                                          padx=5)
        ttk.Button(btns, text="Копировать LEDpatterns1", command=lambda: self.copy_text(self.text1)).pack(side='left',
                                                                                                          padx=5)

        # Footer
        footer = ttk.Label(
            self.root,
            text="© 2026 JluceHok_u3_MuHcka | For BMW i4 / iX / i7 Enthusiasts",
            font=("Segoe UI", 9), foreground="gray", background="#0f0f0f"
        )
        footer.pack(side='bottom', pady=10)

        self.on_mode_change()  # initial UI state

    # === UI CALLBACKS ===
    def on_mode_change(self):
        mode = self.mode.get()
        if mode == "static":
            self.anim_frame.pack_forget()
            self.generate_button.config(text="Сгенерировать статический цвет (LEDpatterns2)")
        else:
            self.anim_frame.pack(padx=20, pady=10, fill='x')
            self.generate_button.config(text="Сгенерировать анимацию зарядки (LEDpatterns1)")

    def draw_hsv_wheel(self):
        if not PIL_AVAILABLE:
            return
        img = Image.new('RGB', (260, 260), 'black')
        draw = ImageDraw.Draw(img)
        cx, cy, r = 130, 130, 120
        for angle in range(360):
            rad = math.radians(angle)
            x = cx + r * math.cos(rad)
            y = cy + r * math.sin(rad)
            hue = angle / 360.0
            rgb = hsv_to_rgb(hue, 1.0, 1.0)
            draw.line([(cx, cy), (x, y)], fill=rgb, width=2)
        mr = 110
        mx = cx + mr * math.cos(self.hue * 2 * math.pi)
        my = cy + mr * math.sin(self.hue * 2 * math.pi)
        draw.ellipse((mx - 4, my - 4, mx + 4, my + 4), outline='white', width=2)
        self.hsv_img = ImageTk.PhotoImage(img)
        self.canvas_hsv.create_image(0, 0, anchor='nw', image=self.hsv_img)

    def draw_sv_gradient(self):
        if not PIL_AVAILABLE:
            return
        img = Image.new('RGB', (160, 160), 'black')
        draw = ImageDraw.Draw(img)
        for y in range(160):
            for x in range(160):
                s = x / 160.0
                v = 1.0 - y / 160.0
                rgb = hsv_to_rgb(self.hue, s, v)
                draw.point((x, y), fill=rgb)
        sx = int(self.saturation * 160)
        sy = int((1.0 - self.value) * 160)
        draw.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), outline='white', width=2)
        self.sv_img = ImageTk.PhotoImage(img)
        self.canvas_sv.create_image(0, 0, anchor='nw', image=self.sv_img)

    def on_hsv_click(self, event):
        cx, cy = 130, 130
        dx, dy = event.x - cx, event.y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if 20 < dist < 120:
            angle = math.atan2(dy, dx)
            if angle < 0:
                angle += 2 * math.pi
            self.hue = angle / (2 * math.pi)
            self.update_preview()

    def on_sv_click(self, event):
        if 0 <= event.x <= 160 and 0 <= event.y <= 160:
            self.saturation = event.x / 160.0
            self.value = 1.0 - event.y / 160.0
            self.update_preview()

    def update_preview(self):
        if PIL_AVAILABLE:
            self.rgb = hsv_to_rgb(self.hue, self.saturation, self.value)
            hex_color = '#{:02X}{:02X}{:02X}'.format(*self.rgb)
            self.preview_canvas.delete("fill")
            self.preview_canvas.create_rectangle(2, 2, 48, 48, fill=hex_color, outline='', tags="fill")
            self.draw_hsv_wheel()
            self.draw_sv_gradient()
        else:
            self.rgb = (self.r_var.get(), self.g_var.get(), self.b_var.get())

    def generate_patterns(self):
        r, g, b = self.rgb
        try:
            # Always generate static (for reference)
            pat2 = generate_ledpatterns2(r, g, b)
            self.text2.delete(1.0, tk.END)
            self.text2.insert(tk.END, pat2)

            # Generate animation only if in charging mode
            if self.mode.get() == "charging":
                anim = self.anim_mode.get()
                if anim == "breathing":
                    pat1 = generate_breathing(r, g, b)
                else:
                    pat1 = generate_blinking(r, g, b)
                self.text1.delete(1.0, tk.END)
                self.text1.insert(tk.END, pat1)
            else:
                self.text1.delete(1.0, tk.END)
                self.text1.insert(tk.END, "<режим зарядки не выбран>")

        except Exception as e:
            messagebox.showerror("Ошибка генерации", str(e))

    def copy_text(self, widget):
        try:
            content = widget.get(1.0, tk.END).strip()
            if content and not content.startswith("<"):
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
                messagebox.showinfo("✅ Готово", "Паттерн скопирован в буфер обмена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать:\n{e}")


# === LAUNCH ===
if __name__ == "__main__":
    root = tk.Tk()
    app = BMWLEDGenerator(root)
    root.mainloop()
