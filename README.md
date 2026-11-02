# Telegram Video Starter

Самостоятельная мастерская вертикальных видео про Telegram и коллекционные подарки.
Кадры создаются Python-кодом; монтаж и экспорт — через FFmpeg.
Это основа для нового автора со своими референсами и визуальным стилем.

Начните с [START_HERE.md](START_HERE.md). Установка — [docs/SETUP.md](docs/SETUP.md).
Инструкции для любой нейросети — [AGENTS.md](AGENTS.md).

В комплекте: техническое ядро анимации, получение данных и Lottie/TGS подарков,
субтитры, необязательная озвучка Fish Audio, рекламная пауза RubUp, шаблон ролика,
проверки и переносимый навык [telegram-video](.agents/skills/telegram-video/SKILL.md).
Единственные медиа: актуальный рекламный баннер и пять начертаний SF Pro Text.
Другие материалы новый автор добавляет сам.

```sh
python -m pip install -r requirements.txt
python -B engine/tools/doctor.py
python -B engine/tools/verify_project.py --distribution
python -B engine/tools/new_project.py 01-topic
python -B projects/01-topic/render.py --frames 0,180,360
```

FFmpeg и ffprobe должны быть доступны в PATH. Полную сборку запускают после
хайлайтов и слова автора «собирай». Без нового ключа Fish Audio работа продолжается
без дикторской озвучки; собственный звук рекламного баннера сохраняется.

Ничего не опубликовано автоматически. Папка готова к созданию нового репозитория.
Зависимости и медиа не получают новую лицензию от включения в комплект:
см. [THIRD_PARTY.md](THIRD_PARTY.md).
