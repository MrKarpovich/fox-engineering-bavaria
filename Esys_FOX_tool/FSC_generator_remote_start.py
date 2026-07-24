from __future__ import annotations

import hashlib
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk


# ==============================================================================
# 1. CRYPTOGRAPHIC CORE (Decoupled mathematical logic)
# ==============================================================================

class CryptoCore:
    """Isolated cryptographic operations for RSA E=3 suffix forgery."""

    E = 3
    SIGNATURE_LEN = 0x80

    N_RAW_LE = bytes.fromhex(
        "03 F8 69 D6 55 B1 80 74 21 3D A6 2C AD C6 17 EC "
        "BB 84 C1 71 EC B8 13 97 3E 1F 34 D8 4B 9B 18 8E "
        "1F F2 59 AF 0F 80 EC 3B BD 43 DF B1 90 E2 6F AC "
        "38 97 59 3C E1 57 10 67 54 A4 29 1B D0 3B C9 7D "
        "11 A6 9D D7 38 97 CE 1D D3 54 5E A6 2A 2A F5 1A "
        "AB DA DD 75 0A AB 69 57 CE 41 B0 E5 07 69 F3 F3 "
        "9C 84 36 3F 57 4C EA 92 78 C2 35 64 5B 07 72 80 "
        "79 10 53 6D 5C F9 8C F7 1F 3B EF 8C D4 90 70 F5"
    )
    N = int.from_bytes(N_RAW_LE, "little")

    @staticmethod
    def floor_cuberoot(value: int) -> int:
        if value < 0:
            raise ValueError("Cube root input must be non-negative")
        lo, hi = 0, 1 << ((value.bit_length() + 2) // 3)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if mid * mid * mid <= value:
                lo = mid
            else:
                hi = mid - 1
        return lo

    @staticmethod
    def ceil_cuberoot(value: int) -> int:
        root = CryptoCore.floor_cuberoot(value)
        return root if root * root * root == value else root + 1

    @staticmethod
    def odd_cube_root_mod_2_128(value: int) -> int:
        modulus = 1 << 128
        value %= modulus
        if not value & 1:
            raise ValueError("Value must be odd for modular cube root")
        inverse_of_three = pow(3, -1, 1 << 126)
        root = pow(value, inverse_of_three, modulus)
        if pow(root, 3, modulus) != value:
            raise AssertionError("Internal modular cube-root failure")
        return root

    @classmethod
    def forge_suffix_only_signature(cls, digest: bytes) -> tuple[bytes, int, bytes]:
        if len(digest) != 16:
            raise ValueError("MD5 digest must be exactly 16 bytes")

        modulus_128 = 1 << 128
        digest_int = int.from_bytes(digest, "big")

        for quotient in range(256):
            target_low = (digest_int + quotient * cls.N) % modulus_128
            if not target_low & 1:
                continue

            residue = cls.odd_cube_root_mod_2_128(target_low)
            lower = cls.ceil_cuberoot(quotient * cls.N)
            upper = cls.floor_cuberoot((quotient + 1) * cls.N - 1)

            if residue > upper:
                continue

            lift = (upper - residue) // modulus_128
            candidate = residue + lift * modulus_128

            if candidate < lower or candidate >= cls.N:
                continue

            recovered_int = pow(candidate, cls.E, cls.N)
            recovered = recovered_int.to_bytes(cls.SIGNATURE_LEN, "big")

            if recovered[-16:] != digest:
                continue

            signature = candidate.to_bytes(cls.SIGNATURE_LEN, "big")
            return signature, quotient, recovered

        raise RuntimeError("Could not construct a suffix-only signature")


# ==============================================================================
# 2. FSC BUILDER (Business logic, decoupled from UI)
# ==============================================================================

class FSCBuilder:
    """Handles template loading and FSC binary construction."""

    BODY_LEN = 0x3C
    SIGNATURE_LEN = 0x80
    VIN_OFFSET = 0x1A
    VIN_LEN = 7
    APPID_OFFSET = 0x02

    TEMPLATE_BODY = bytes.fromhex(
        "01 01 01 7C 00 01 20 20 37 37 33 34 38 37 01 20 "
        "30 30 30 30 30 30 30 1D 61 01 39 4A 32 39 34 33 "
        "36 01 00 00 00 00 00 00 00 00 00 04 02 32 30 "
        "32 36 30 31 30 31 31 30 30 30 5A 00"
    )

    KNOWN_SUFFIX_ONLY_SIGNATURE = bytes.fromhex(
        "16 DC 66 62 4B 4D 8C 57 94 0C 5F 9D 13 70 5F 08 "
        "BE A5 C5 19 88 AA D3 3C 3C CF 6C CF D0 07 0C A1 "
        "33 26 D3 1A D0 C2 6A 0E 44 0D C1"
    )

    BUILTIN_TEMPLATE = (
            TEMPLATE_BODY
            + b"\x00"
            + b"\x00" * (SIGNATURE_LEN - len(KNOWN_SUFFIX_ONLY_SIGNATURE))
            + KNOWN_SUFFIX_ONLY_SIGNATURE
    )

    ALL_APPIDS = (
        0x01A4, 0x01AB, 0x01AC, 0x01AF, 0x01C1, 0x01DE, 0x01E2,
        0x01E3, 0x01E4, 0x01E8, 0x01EC, 0x01EE, 0x01EF, 0x01F0,
        0x01F1, 0x01F2, 0x007B, 0x017C, 0x0095, 0x0180, 0x0188,
    )

    def __init__(self, template_path: Path | None = None):
        self.template = self._load_template(template_path)

    def _load_template(self, path: Path | None) -> bytearray:
        data = self.BUILTIN_TEMPLATE if path is None else path.read_bytes()
        expected = self.BODY_LEN + self.SIGNATURE_LEN
        if len(data) < expected:
            raise ValueError(f"Template is {len(data)} bytes; need at least {expected} bytes")
        return bytearray(data[:self.BODY_LEN] + data[-self.SIGNATURE_LEN:])

    def build_single(self, vin7: bytes, appid: int) -> tuple[bytes, str]:
        output = bytearray(self.template)
        output[self.APPID_OFFSET: self.APPID_OFFSET + 2] = appid.to_bytes(2, "big")
        output[self.VIN_OFFSET: self.VIN_OFFSET + self.VIN_LEN] = vin7

        digest = hashlib.md5(output[:self.BODY_LEN]).digest()
        signature, quotient, _ = CryptoCore.forge_suffix_only_signature(digest)
        output[-self.SIGNATURE_LEN:] = signature

        # Self-check (weak validation)
        stored_signature = int.from_bytes(output[-self.SIGNATURE_LEN:], "big")
        checked = pow(stored_signature, CryptoCore.E, CryptoCore.N).to_bytes(self.SIGNATURE_LEN, "big")
        if checked[-16:] != digest:
            raise AssertionError("Generated FSC failed the vulnerable-verifier self-check")

        return bytes(output), digest.hex().upper()


# ==============================================================================
# 3. GUI APPLICATION (Modern, thread-safe, aesthetically pleasing)
# ==============================================================================

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("🦊 BMW FSC Generator MDG1")
        self.geometry("600x500")
        self.minsize(550, 450)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State variables
        self.output_dir = Path.cwd()
        self.is_processing = False

        self._setup_logging()
        self._build_ui()
        self.logger.info("Application initialized. Ready.")

    def _setup_logging(self):
        self.logger = logging.getLogger("FSC_Generator")
        self.logger.setLevel(logging.INFO)
        # Custom handler to route logs to the GUI text box
        self.log_handler = GUITextHandler(self)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        self.log_handler.setFormatter(formatter)
        self.logger.addHandler(self.log_handler)

    def _build_ui(self):
        padding = {"padx": 20, "pady": 10}

        # Title
        self.lbl_title = ctk.CTkLabel(self, text="🦊 Генератор FSC кодов MDG1", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(**padding)

        # VIN Input Frame
        frame_vin = ctk.CTkFrame(self)
        frame_vin.pack(fill="x", **padding)

        self.lbl_vin_full = ctk.CTkLabel(frame_vin, text="Полный VIN (минимум 7 символов):")
        self.lbl_vin_full.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.entry_vin = ctk.CTkEntry(frame_vin, width=300, placeholder_text="Например: WBY1Z210XGVA12345")
        self.entry_vin.grid(row=0, column=1, padx=10, pady=10)
        self.entry_vin.bind("<KeyRelease>", self._on_vin_input)

        self.lbl_vin_extracted = ctk.CTkLabel(frame_vin, text="Извлеченные последние 7 символов: ---",
                                              text_color="gray")
        self.lbl_vin_extracted.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        # Folder Selection Frame
        frame_folder = ctk.CTkFrame(self)
        frame_folder.pack(fill="x", **padding)

        self.lbl_folder = ctk.CTkLabel(frame_folder, text="Папка для сохранения:")
        self.lbl_folder.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.entry_folder = ctk.CTkEntry(frame_folder, width=300, state="readonly")
        self.entry_folder.grid(row=0, column=1, padx=10, pady=10)
        self.entry_folder.insert(0, str(self.output_dir))

        self.btn_browse = ctk.CTkButton(frame_folder, text="Обзор...", width=100, command=self._browse_folder)
        self.btn_browse.grid(row=0, column=2, padx=10, pady=10)

        # Action Button
        self.btn_generate = ctk.CTkButton(self, text="Сгенерировать FSC", font=("Roboto", 16, "bold"),
                                          fg_color="#28a745", hover_color="#218838", command=self._start_generation)
        self.btn_generate.pack(**padding)

        # Log Output Frame
        frame_log = ctk.CTkFrame(self)
        frame_log.pack(fill="both", expand=True, **padding)

        self.txt_log = ctk.CTkTextbox(frame_log, font=("Consolas", 12), state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=10)

    def _on_vin_input(self, event=None):
        raw_vin = self.entry_vin.get().strip().upper()
        if len(raw_vin) >= 7:
            vin7 = raw_vin[-7:]
            if vin7.isalnum():
                self.lbl_vin_extracted.configure(text=f"Извлеченные последние 7 символов: {vin7}", text_color="#28a745")
                return
        self.lbl_vin_extracted.configure(text="Извлеченные последние 7 символов: --- (некорректный ввод)",
                                         text_color="#dc3545")

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir)
        if folder:
            self.output_dir = Path(folder)
            self.entry_folder.configure(state="normal")
            self.entry_folder.delete(0, tk.END)
            self.entry_folder.insert(0, str(self.output_dir))
            self.entry_folder.configure(state="readonly")

    def _start_generation(self):
        if self.is_processing:
            return

        raw_vin = self.entry_vin.get().strip().upper()
        if len(raw_vin) < 7 or not raw_vin[-7:].isalnum():
            messagebox.showerror("Ошибка", "Введите корректный VIN (минимум 7 буквенно-цифровых символов).")
            return

        vin7 = raw_vin[-7:].encode("ascii")
        target_folder = self.output_dir / vin7.decode("ascii")

        self.is_processing = True
        self.btn_generate.configure(state="disabled", text="Генерация...")
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", tk.END)
        self.logger.info(f"Начало генерации для VIN-7: {vin7.decode('ascii')}")
        self.logger.info(f"Целевая папка: {target_folder}")

        # Run in a separate thread to prevent GUI freezing (Memory 3 compliance)
        thread = threading.Thread(target=self._generation_worker, args=(vin7, target_folder), daemon=True)
        thread.start()

    def _generation_worker(self, vin7: bytes, target_folder: Path):
        try:
            target_folder.mkdir(parents=True, exist_ok=True)
            builder = FSCBuilder()
            success_count = 0

            for appid in FSCBuilder.ALL_APPIDS:
                try:
                    output_bytes, digest_hex = builder.build_single(vin7, appid)
                    filename = f"FSC_{vin7.decode('ascii')}_{appid:04x}.fsc"
                    filepath = target_folder / filename
                    filepath.write_bytes(output_bytes)
                    success_count += 1
                    # Thread-safe GUI update
                    self.after(0, lambda f=filename, d=digest_hex: self.logger.info(f"✓ Создан: {f} (MD5: {d})"))
                except Exception as e:
                    self.after(0, lambda err=str(e): self.logger.error(f"Ошибка генерации: {err}"))

            self.after(0, lambda: self.logger.info(f"✅ Успешно завершено! Сгенерировано файлов: {success_count}"))
            self.after(0, lambda: messagebox.showinfo("Успех",
                                                      f"Успешно создано {success_count} файлов в папке:\n{target_folder}"))

        except Exception as e:
            self.after(0, lambda: self.logger.error(f"Критическая ошибка: {e}"))
            self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        self.is_processing = False
        self.btn_generate.configure(state="normal", text="Сгенерировать все AppID")

    def append_log(self, message: str):
        """Thread-safe method to append text to the log textbox."""
        self.txt_log.configure(state="normal")
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state="disabled")


class GUITextHandler(logging.Handler):
    """Custom logging handler that routes logs to the CTkTextbox."""

    def __init__(self, gui_app: AppGUI):
        super().__init__()
        self.gui_app = gui_app

    def emit(self, record):
        log_entry = self.format(record)
        self.gui_app.append_log(log_entry)


# ==============================================================================
# 4. ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()
