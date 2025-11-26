# 🦊 ISTA RegFox  
**Windows Registry Manager for BMW ISTA/Rheingold**

> Safely toggle programming mode • Full backup control • Standalone .exe  
> Безопасное управление режимом программирования • Полный контроль бэкапов • Автономный .exe

<div align="center">

[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-blue?logo=windows)]()
[![Release](https://img.shields.io/badge/Download-ISTA--RegFox--V1.0-green?logo=github)](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/ISTA-RegFox-V1.0)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](https://github.com/MrKarpovich/fox-engineering-bavaria/blob/main/LICENSE)

[🇷🇺 Русский](#russian) • [🇬🇧 English](#english)

</div>

---

<a id="russian"></a>
## 🇷🇺 Русский

### 💡 Что это?
**ISTA RegFox** — это автономное приложение для Windows, которое позволяет **безопасно включать и выключать режим программирования в BMW ISTA/Rheingold**, работая напрямую с реестром Windows.  
Все изменения **автоматически сохраняются**, и вы всегда можете **вернуться к любому состоянию** — даже к исходному!

### 🔧 Возможности
- ✅ Автоматическое обнаружение всех версий ISTA (новые и старые)  
- ✅ Активация/деактивация режима программирования в один клик  
- ✅ Указание версии ISTA и пути к `PSdZData`  
- ✅ **Автоматические бэкапы** при каждом изменении (`ДДММГГГГ_ЧЧММСС.json`)  
- ✅ Защита от сохранения дублирующихся состояний  
- ✅ Хранение до **1000 бэкапов** (старые удаляются по FIFO)  
- ✅ **Исходное состояние** (первый запуск) защищено от удаления  
- ✅ Ручной импорт и экспорт конфигураций в **JSON**  
- ✅ Полный откат к любому бэкапу или исходному состоянию  
- ✅ Красивый и интуитивный графический интерфейс  
- ✅ Работает как **автономный .exe** — все данные хранятся рядом с программой  
- ✅ Использует только встроенные библиотеки Python — **ничего дополнительно устанавливать не нужно**

### ⚙️ Использование
1. **Запустите программу от имени администратора**
2. При первом запуске автоматически сохранится **исходное состояние реестра**
3. Используйте кнопки:  
   - «Сохранить настройки в файл» — экспорт в JSON  
   - «Загрузить настройки из файла» — импорт из JSON  
   - «Активировать режим программирования» — включить с указанием версии и пути  
   - «Деактивировать режим программирования» — выключить режим  
   - «Возврат к исходному состоянию» — управление бэкапами и откат

### 📥 Скачать
👉 **[Скачать ISTA-RegFox-V1.0.exe](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/ISTA-RegFox-V1.0)**

### ⚠️ Важно!
Инструмент **изменяет системный реестр Windows**.  
Используйте **на свой страх и риск**.  
Автор **не несёт ответственности** за повреждение системы или оборудования.  
❗ **Рекомендуется создать точку восстановления системы перед первым использованием.**

---

<a id="english"></a>
## 🇬🇧 English

### 💡 What is it?
**ISTA RegFox** is a standalone Windows application that lets you **safely activate and deactivate programming mode in BMW ISTA/Rheingold** by directly editing the Windows Registry.  
All changes are **automatically backed up**, and you can always **restore any state** — even the original one!

### 🔧 Features
- ✅ Automatic detection of all ISTA versions (new and legacy)  
- ✅ One-click activation/deactivation of programming mode  
- ✅ Specify ISTA version and `PSdZData` path  
- ✅ **Automatic backups** on every change (`DDMMYYYY_HHMMSS.json`)  
- ✅ Protection against duplicate registry states  
- ✅ Stores up to **1000 backups** (old ones deleted via FIFO)  
- ✅ **Initial state** (first launch) is protected from deletion  
- ✅ Manual import/export of configurations in **JSON**  
- ✅ Full rollback to any backup or initial state  
- ✅ Beautiful and intuitive GUI  
- ✅ Runs as a **standalone .exe** — all data stored next to the executable  
- ✅ Uses only built-in Python libraries — **no additional installation required**

### ⚙️ Usage
1. **Run the program as Administrator**
2. On first launch, the **original registry state is automatically saved**
3. Use the buttons:  
   - "Save settings to a file" — export to JSON  
   - "Load settings from a file" — import from JSON  
   - "Activate programming mode" — enable with version and path  
   - "Deactivate programming mode" — disable mode  
   - "Return to initial state" — manage backups and rollback

### 📥 Download
👉 **[Download ISTA-RegFox-V1.0.exe](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/ISTA-RegFox-V1.0)**

### ⚠️ Important!
This tool **modifies the Windows system registry**.  
Use **at your own risk**.  
The author **is not liable** for any system or hardware damage.  
❗ **We strongly recommend creating a system restore point before first use.**

---

🦊 **Created with love for BMW engineers | Fox Engineering Bavaria**
