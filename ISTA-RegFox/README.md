# ISTA RegFox 🦊  
[🇷🇺 Русский] Управление реестром Windows для BMW ISTA.

Этот инструмент позволяет безопасно активировать и деактивировать режим программирования в BMW ISTA/Rheingold, работая напрямую с реестром Windows. Все изменения сохраняются, и при необходимости можно вернуться к любому предыдущему состоянию — включая исходное.

## 🔧 Возможности

- Автоматическое обнаружение всех версий ISTA (новые и старые)
- Активация и деактивация режима программирования
- Указание версии ISTA и пути к PSdZData
- Автоматические бэкапы при каждом изменении (формат: ДДММГГГГ_ЧЧММСС.json)
- Защита от сохранения дублирующихся состояний
- Хранение до 1000 бэкапов (старые удаляются по FIFO)
- Исходное состояние (первый запуск) защищено от удаления
- Ручной импорт и экспорт конфигураций в формате JSON
- Полный откат к любому бэкапу или исходному состоянию
- Красивый и интуитивный графический интерфейс
- Работает как автономный .exe — все данные хранятся рядом с программой
- Использует только встроенные библиотеки Python — ничего дополнительно устанавливать не нужно

## ⚙️ Использование

1. Запустите программу от имени администратора.
2. При первом запуске автоматически сохранится исходное состояние реестра.
3. Используйте кнопки:
   - «Сохранить настройки в файл» — экспорт в JSON
   - «Загрузить настройки из файла» — импорт из JSON
   - «Активировать режим программирования» — включить режим с настройкой версии и пути
   - «Деактивировать режим программирования» — выключить режим
   - «Возврат к исходному состоянию» — управление всеми бэкапами и откат

## ⚠️ Важно! ⚠️

Инструмент изменяет системный реестр Windows.  
Используйте на свой страх и риск.  
Автор не несёт ответственности за повреждение системы или оборудования.  
Рекомендуется создавать резервную копию системы перед первым использованием.

---

# ISTA RegFox 🦊  
[🇬🇧 English] Windows Registry management for BMW ISTA.

This tool allows you to safely activate and deactivate programming mode in BMW ISTA/Rheingold by working directly with the Windows Registry. All changes are saved, and if necessary, you can return to any previous state, including the original one.

## 🔧 Features

- Automatic detection of all ISTA versions (new and old)
- Activation and deactivation of the programming mode
- Specifying the ISTA version and the path to PSdZData
- Automatic backups with each change (format: DDMMGGGG_HMMSS.json)
- Protection against saving duplicate states
- Storage of up to 1000 backups (old ones are deleted by FIFO)
- The initial state (first launch) is protected from deletion
- Manual import and export of configurations in JSON format
- Full rollback to any backup or initial state
- Beautiful and intuitive graphical interface
- Works as a standalone .exe — all data is stored next to the program
- Uses only built—in Python libraries - you don't need to install anything extra

## ⚙️ Usage

1. Run the program as an administrator.
2. The initial state of the registry will be automatically saved on the first startup.
3. Use the buttons:
- "Save settings to a file" — export to JSON
- "Download settings from a file" — Import from JSON
- "Activate programming mode" — enable the mode with version and path settings
   - "Deactivate programming mode" — turn off the mode
- "Return to the initial state" — manage all backups and rollback

## ⚠️ Important! ⚠️

The tool modifies the Windows system registry.  
Use it at your own risk.  
The author is not responsible for damage to the system or equipment.  
It is recommended to create a backup copy of the system before using it for the first time.
