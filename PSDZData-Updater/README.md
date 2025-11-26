# 📦 PSDZData Incremental Updater  
**Update BMW psdzdata without 300 GB downloads!**  

> Compare two versions • Generate minimal delta • Standalone .exe for Windows  
> Сравните две версии • Создайте минимальное обновление • Автономный .exe для Windows

<div align="center">

[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-blue?logo=windows)]()
[![Release](https://img.shields.io/badge/Download-PSDZData--Updater--v1.0-green?logo=github)](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/PSDZData-Updater-v1.0)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](./LICENSE)

[🇷🇺 Русский](#%EF%B8%8F-русский) • [🇬🇧 English](#%EF%B8%8F-english)

</div>

---

## 🇷🇺 Русский

### 💡 Устали скачивать 300 ГБ?
Каждое обновление ISTA/E-Sys требует заново скачивать **сотни гигабайт** `psdzdata`?  
**PSDZData Incremental Updater** решает эту проблему: он **сравнивает две версии** и создаёт **минимальное обновление**, содержащее **только изменённые файлы**.

### 🔧 Возможности
- ✅ Только встроенные библиотеки Python — **никаких зависимостей**
- ✅ Готовый **`.exe`** — работает на любом Windows **без установки Python**
- ✅ Графический интерфейс с кнопками и прогресс-баром
- ✅ Сравнение по **SHA-256** — 100% надёжность
- ✅ **Не трогает исходные папки** — только чтение и копирование
- ✅ Поддержка **длинных путей** на Windows

### 🚀 Как использовать
1. Нажмите **«1. Просканировать psdzdata»** → создайте `.json` вашей текущей версии (например, `2024-11.json`)  
2. Нажмите **«2. Создать python_psdzdata»** → укажите:  
   - `.json` старой версии (вашей),  
   - `.json` новой версии (от админа или сообщества),  
   - папку с **полной новой версией** `psdzdata`,  
   - папку для сохранения результата.  
3. Скопируйте папку `python_psdzdata` **поверх старой `psdzdata`** на любом ПК → обновление готово!

> 💡 **Совет**: один раз создайте `.json` для новой версии — и делитесь им! Всё сообщество сможет обновляться без 300 ГБ.

### 📥 Скачать
👉 **[Скачать PSDZData-Updater-v1.0.exe](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/PSDZData-Updater-v1.0)**

> ⚠️ **Важно**: этот инструмент **не содержит и не распространяет** официальные данные BMW. Он работает **только с `psdzdata`, уже имеющимся на вашем компьютере**.

---

## 🇬🇧 English

### 💡 Tired of 300 GB downloads?
Does every ISTA/E-Sys update force you to re-download **hundreds of gigabytes** of `psdzdata`?  
**PSDZData Incremental Updater** solves this: it **compares two versions** and generates a **minimal update** containing **only changed files**.

### 🔧 Features
- ✅ Pure standard Python libraries — **no external dependencies**
- ✅ Standalone **`.exe`** — runs on any Windows **without Python installed**
- ✅ GUI with buttons and progress bar
- ✅ **SHA-256** based comparison — 100% reliability
- ✅ **Never modifies source folders** — read-only + safe copy
- ✅ Full **long path support** on Windows

### 🚀 How to use
1. Click **«1. Scan psdzdata»** → create a `.json` snapshot of your current version (e.g. `2024-11.json`)  
2. Click **«2. Create python_psdzdata»** → select:  
   - Old version `.json` (yours),  
   - New version `.json` (from admin or community),  
   - Folder with the **full new version** of `psdzdata`,  
   - Output folder for the update.  
3. Copy the `python_psdzdata` folder **over your old `psdzdata`** on any machine → update complete!

> 💡 **Tip**: Generate a `.json` for the new version once — and share it! The entire community can update instantly.

### 📥 Download
👉 **[Download PSDZData-Updater-v1.0.exe](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/PSDZData-Updater-v1.0)**

> ⚠️ **Note**: This tool **does not include or distribute** BMW software or data. It only works with `psdzdata` **already present on your system**.

---

### 📜 License
Distributed under the **[MIT License](./LICENSE)**.

🦊 **Created with love for BMW engineers | Fox Engineering Bavaria**
