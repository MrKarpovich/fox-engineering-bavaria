# 🦊 **E-Sys FoxData**  
### Admin GUI + Telegram Bot for Instant psdzdata File Delivery  

> **Have a full `psdzdata`? Help your team or friends get the exact files they need — instantly via Telegram.**  

<div align="center">

[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-blue?logo=windows)]()
[![Release](https://img.shields.io/github/v/release/MrKarpovich/fox-engineering-bavaria?label=latest%20release&color=green)](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)]()

[🇷🇺 Русский](#-русский) • [🇺🇸 English](#-english)

</div>

---

## 🇷🇺 Русский
> **Есть полная `psdzdata`? Помогите своей команде или друзьям получать нужные файлы — мгновенно через Telegram.**
### 💡 Что это?
**E-Sys FoxData** — это **однофайловое Windows-приложение**, которое позволяет **владельцу полной `psdzdata`** легко и безопасно раздавать недостающие файлы (например, `CAFD_00001234_001_000_021`) **своим коллегам, друзьям или клиентам** через **Telegram-бота**.

Вы **запускаете приложение у себя**, настраиваете один раз — и все готово! Пользователи просто пишут боту названия файлов → вы подтверждаете → архив отправляется автоматически.  
**Никаких рисков: клиенты не видят вашу папку, не загружают ничего, работают только с вашим индексом.**

---

### 🤖 Попробуйте прямо сейчас!
Мы запустили **демо-бота** для тестирования:  
👉 **[@Esys_FoxDataBot](https://t.me/Esys_FoxDataBot)**

> ⚠️ **Важно**: бот доступен временно. После теста **мы рекомендуем запустить своего бота** (бесплатно и навсегда!) с помощью `E-Sys FoxData.exe`.  
> 🗣️ **Интерфейс — на русском**, но вы можете использовать **встроенный переводчик Telegram** (удерживайте сообщение → «Перевести»).

---

### 🚀 Основные возможности
- ✅ **Графический интерфейс (PyQt6)** — настройка путей, генерация индекса с прогрессом  
- ✅ **Telegram-бот (aiogram 3.22)** — поиск по админскому индексу, отправка архивов  
- ✅ **Автоматическое разбиение** на части ≤ **800 МБ** (ограничение Telegram)  
- ✅ **Персональные папки** для каждого пользователя → автоочистка после отправки  
- ✅ Встроенные команды: `/help`, `/faq`, ссылка на поддержку  
- ✅ **Один .exe-файл** — не нужен Python, не требуется установка  

---

### 📥 Как начать?
1. Перейдите в **[Релизы (Releases)](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/V1.0)**
2. Скачайте **`E-Sys FoxData.exe`** (50 МБ)
3. Запустите → укажите:
   - Путь к вашей **полной папке `psdzdata`**
   - Папку для временных файлов (`output_base`)
   - Telegram-токен (получите у [@BotFather](https://t.me/BotFather))
4. Нажмите **«Сохранить и запустить бота»** → готово!

> 💡 **Требуется**: Windows 10/11, доступ к `psdzdata`, учётная запись Telegram.

---

### 📬 Поддержка
Вопросы, предложения, помощь? Пишите:  
👉 **[@JluceHok_u3_MuHcka](https://t.me/JluceHok_u3_MuHcka)**

---

## 🇺🇸 English

### 💡 What is it?
**E-Sys FoxData** is a **single-file Windows application** that lets **owners of a full `psdzdata` archive** easily and securely deliver missing files (e.g. `CAFD_00001234_001_000_021`) to their **team, friends, or clients** via a **Telegram bot**.

You run the app **on your machine**, configure it once — and you're done! Users just message the bot with file names → you approve → archive is sent automatically.  
**No risks: clients never see your folder, upload nothing, and only query your index.**

---

### 🤖 Try it now!
We’ve launched a **demo bot** for testing:  
👉 **[@Esys_FoxDataBot](https://t.me/Esys_FoxDataBot)**

> ⚠️ **Note**: this bot is **temporary**. After testing, **we strongly recommend running your own bot** (free & permanent!) using `E-Sys FoxData.exe`.  
> 🗣️ **Interface is in Russian**, but you can use **Telegram’s built-in translator** (long-press message → “Translate”).

---

### 🚀 Key Features
- ✅ **Admin GUI (PyQt6)** — configure paths, generate index with progress & hashing  
- ✅ **Telegram Bot (aiogram 3.22)** — search by admin index, send archives  
- ✅ **Auto-split** into parts ≤ **800 MB** (Telegram limit)  
- ✅ **Per-user folders** → auto cleanup after delivery  
- ✅ Built-in commands: `/help`, `/faq`, support contact  
- ✅ **Single .exe file** — no Python, no installation needed  

---

### 📥 How to start?
1. Go to **[Releases](https://github.com/MrKarpovich/fox-engineering-bavaria/releases/tag/V1.0)**
2. Download **`E-Sys FoxData.exe`** (50 MB)
3. Run → configure:
   - Path to your **full `psdzdata` folder**
   - Output folder (`output_base`)
   - Telegram bot token (get from [@BotFather](https://t.me/BotFather))
4. Click **“Save and launch bot”** → done!

> 💡 **Requirements**: Windows 10/11, access to `psdzdata`, Telegram account.

---

### 📬 Support
Questions or feedback? Contact the developer:  
👉 **[@JluceHok_u3_MuHcka](https://t.me/JluceHok_u3_MuHcka)**

---

🦊 **Created with love for engineers | Fox Engineering Bavaria**
