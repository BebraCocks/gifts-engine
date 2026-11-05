# Конвейер и интерфейсы

Кадр: `render_at(content_t) -> numpy uint8 (1920,1080,3)`.
Номер кадра: `i`, время выхода: `i/60`.
`banner.Breaks` переводит выходное время в время содержания и вставляет рекламу.
Одни и те же остановки/скорость должны использоваться в рендере и аудио.

| Модуль | Что использовать |
|---|---|
| `paths` | пути относительно корня, FFmpeg/ffprobe из PATH или окружения |
| `fx` | smooth, spring, bump, keys, catmull, remap, warp, over, текст и маски |
| `captions` | оценка времён слов, align/retime, субтитры |
| `layout` | контуры текста, центрирование, аудит полей и перекрытий |
| `raster` | необязательный растеризатор треугольников; моделей в комплекте нет |
| `gifts_api` | данные, PNG, JSON/TGS и паттерны подарков по сети |
| `lottie` | метаданные и RGBA-кадр полного цикла; ограниченный кэш памяти |
| `sound`, `voice` | декодирование, нормализация, огибающие, границы речи |
| `sfxkit` | SFX из `input/sfx/` по ролям, без повторов внутри ролика и между роликами, файлы для прослушивания |
| `banner` | прозрачный баннер, временная карта, пауза, звук, duck |
| `frames` | стопкадры, воркеры, экспорт изображения, прогресс |

`templates/project/` — полный контракт одного ролика: `script.py`, `config.py`,
`timeline.py`, `words.py`, `events.py`, `render.py`, `audio.py`, `STORYBOARD.md`.
Шаблон оценивает длительности без диктора. Если выбраны все `voice/LNN.wav`,
используются их реальные длительности; временные якоря потом проверяются.
Для длинных видео добавьте рекламную остановку в середину каждой минуты.
`Breaks.auto` помогает выбрать паузы; не ставьте рекламу внутрь слова.

## Команды

```sh
python -B engine/tools/new_project.py 01-topic
python -B engine/gifts_api.py "Gift Name" --models 3 --anim
python -B engine/tools/lottie_strip.py cycle.png "Gift Name/Model Name" --n 12
python -B projects/01-topic/render.py --frames 0,180,360
python -B engine/layout.py projects/01-topic
python -B projects/01-topic/audio.py          # mix.wav + review/sfx_only.mp3, mix.mp3, sfx_cues.txt
python -B engine/tools/sfx_catalog.py --audition whoosh
python -B engine/tools/verify_project.py
```

Имена Gift Name и Model Name заменяются фактическими именами из API.
Хайлайты из `projects/01-topic/build/review/` показываются автору картинками,
а `sfx_only.mp3`, `mix.mp3` и `sfx_cues.txt` оттуда же отправляются файлами для прослушивания.
Только после **«собирай»**, с собственной визуальной концепцией и `STYLE_READY=True`:

```sh
python -B engine/tools/build.py projects/01-topic --approved --name topic_v1
```

Финал — `renders/01-topic/topic_v1.mp4`. Код не перезаписывает финал с тем же именем.
`build.py` проверяет параметры и полностью декодирует файл. После этого требуются
просмотр движения и прослушивание микса. Отчёт о них заполняет автор или агент
с фактическим доступом к воспроизведению.

Кэш скачанных подарков/декодированного баннера — `.cache/`; его нет в поставке.
SFX по умолчанию — пак Botanica V4 в `input/sfx/` (в Git, см. [SFX.md](SFX.md)).
Новые референсы, модели и музыка добавляются отдельно в `input/` и исключены из Git.
Входные WAV и оплаченные дубли сохраняются локально, резервируются отдельно.

## Принципы более сложной анимации

Вход/удар/раскрытие привязываются к словам через `wt()`; аудио и картинка используют
одну карту событий. У пружин есть затухание; у камеры — непрерывная скорость;
у объектов — иерархия планов. Необязательные DOF, motion blur, time-remap, маски,
траектории и пространственные сцены выбираются по задаче. Методика в навыке
[telegram-video](../.agents/skills/telegram-video/SKILL.md), раздел «Модули».
