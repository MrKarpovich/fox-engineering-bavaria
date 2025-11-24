# PSDZData Incremental Updater

## 🇷🇺 Русский

Устали скачивать 300 ГБ `psdzdata` при каждом обновлении BMW ISTA/E-Sys?  
Этот инструмент позволяет **сравнить две версии** `psdzdata` и создать **минимальное обновление**, содержащее только изменённые файлы.

### 🔧 Возможности
- ✅ Только встроенные библиотеки Python — **никаких зависимостей**
- ✅ Готовый `.exe` — работает на любом Windows **без установки Python**
- ✅ Графический интерфейс с кнопками и прогресс-баром
- ✅ Сравнение по SHA-256 — 100% надёжность
- ✅ Не трогает исходные папки — только чтение и копирование
- ✅ Поддержка длинных путей на Windows

### 🚀 Как использовать
1. Для первого запуска: Нажмите **«1. Просканировать psdzdata»** → создайте `.json` вашей текущей версии, назовите её к примеру 2022-11 и отправьте его человеку с полной датой. Для сервера тоже самое, это ваша последняя дата будет.
2. Нажмите **«2. Создать python_psdzdata»** → укажите:
   - `.json` старой версии (клиента),
   - `.json` новой версии (последняя),
   - папку с **полной новой версией** `psdzdata`,
   - папку для сохранения результата.
3. Скопируйте папку `python_psdzdata` поверх старой `psdzdata` на любом ПК для обновления, готово! Не нужно заново скачивать по 300 гигов.

> 💡 Совет: один раз создайте `.json` для новой версии — и делитесь им с сообществом! Все смогут обновляться без 300 ГБ.

---

## 🇬🇧 English

Tired of re-downloading 300 GB of `psdzdata` every time BMW ISTA/E-Sys releases a new version?  
This tool lets you **compare two versions** of `psdzdata` and generate a **minimal update** containing only changed files.

### 🔧 Features
- ✅ Pure standard Python libraries — **no external dependencies**
- ✅ Standalone `.exe` — runs on any Windows **without Python installed**
- ✅ GUI with buttons and progress bar
- ✅ SHA-256 based comparison — 100% reliability
- ✅ Never modifies source folders — read-only + copy
- ✅ Long path support on Windows

### 🚀 How to use
1. Click **«1. Scan psdzdata»** → create a `.json` snapshot of your current version.
2. Click **«2. Create python_psdzdata»** → select:
   - Old version `.json` (yours),
   - New version `.json` (downloaded or created),
   - Folder with the **full new version** of `psdzdata`,
   - Output folder for the update.
3. Copy the `python_psdzdata` folder over your old `psdzdata` on any machine.

> 💡 Tip: Create a `.json` for the new version once — and share it with the community! Everyone can update without 300 GB downloads.

---

### 📜 Лицензия / License
Distributed under the **MIT License** — see [`LICENSE`](./LICENSE) for details.

> ⚠️ This tool does **not contain or distribute BMW software or data**. It only works with `psdzdata` already present on your system.
