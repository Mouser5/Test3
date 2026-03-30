# Гномы-вредители: Дуэль

Карточная игра для двух игроков с механикой прокладки туннелей и сбора золота.

## Описание проекта

Реализация настольной игры "Гномы-вредители: Дуэль" на Python с использованием:
- **FastAPI** - REST API для игры ботов
- **Streamlit** - веб-интерфейс
- **PostgreSQL** - хранение пользователей и истории игр
- **Docker** - контейнеризация и изоляция ботов

---

## Быстрый старт

```bash
# Запуск всех сервисов
docker compose up --build -d

# Сервисы:
# - Web UI:    http://localhost:8501
# - API:       http://localhost:8000
# - Swagger:   http://localhost:8000/docs
# - PostgreSQL: localhost:5111 (5432 inside container)
```

---

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Game Web      │     │    Game API     │     │   PostgreSQL    │
│  (Streamlit)    │────▶│    (FastAPI)    │────▶│    (БД)         │
│    :8501        │     │     :8000       │     │    :5432        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                  │
                                  ▼ (webhook)
                         ┌─────────────────┐
                         │  Bot Container  │
                         │ (изолированный) │
                         │     :8001       │
                         └─────────────────┘
```

---

## API Документация

### Swagger UI

Полная документация доступна по адресу: http://localhost:8000/docs

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/health` | Проверка здоровья API |
| POST | `/games` | Создать новую игру |
| GET | `/games/{game_id}` | Получить состояние игры |
| GET | `/games/{game_id}/state` | Получить полное состояние для обоих игроков |
| GET | `/games/{game_id}/legal-actions` | Получить легальные ходы |
| POST | `/games/{game_id}/action` | Совершить ход |

### Примеры использования API

#### Создание игры

```bash
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{
    "bot1_code": "import random\\nclass Bot:\\n    def __init__(self, player_id):\\n        self.player_id = player_id\\n    def choose_action(self, game):\\n        return random.choice(game.get_legal_actions()) if game.get_legal_actions() else None",
    "bot2_code": "import random\\nclass Bot:\\n    def __init__(self, player_id):\\n        self.player_id = player_id\\n    def choose_action(self, game):\\n        return random.choice(game.get_legal_actions()) if game.get_legal_actions() else None"
  }'
```

#### Получение состояния игры

```bash
curl http://localhost:8000/games/{game_id}
```

#### Совершение хода

```bash
curl -X POST http://localhost:8000/games/{game_id}/action \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": 0,
    "action": {
      "type": "build",
      "template_id": "tunnel_corner",
      "x": 0,
      "y": -1,
      "is_rotated_180": false
    }
  }'
```

### Формат состояния игры

```json
{
  "game_id": "uuid",
  "player_id": 0,
  "round": 1,
  "turn": 1,
  "current_player": 0,
  "scores": {"0": 0, "1": 0},
  "hand": ["tunnel_corner", "act_key", "ladder"],
  "broken_equipments": [],
  "known_secrets": [],
  "legal_actions": [
    {"type": "build", "template_id": "tunnel_corner", "x": 0, "y": -1, "is_rotated_180": false},
    {"type": "discard", "templates": ["tunnel_corner"]}
  ],
  "is_game_over": false
}
```

---

## Веб-интерфейс

### Регистрация и вход

1. Откройте http://localhost:8501
2. Зарегистрируйте нового пользователя
3. Войдите в систему

### Загрузка ботов

1. Перейдите на вкладку "Мои боты"
2. Введите название бота
3. Вставьте код Python класса с методом `choose_action(game)`
4. Нажмите "Загрузить"

### Запуск игры

1. Выберите бота из списка
2. Выберите противника (RandomAgent, HeuristicAgent, SmartAgent)
3. Нажмите "Запустить игру"

---

## Структура проекта

```
VKRtemp/
├── README.md                  # Документация
├── requirements.txt           # Зависимости Python
├── Dockerfile                 # Docker-образ
├── docker-compose.yml         # Docker Compose конфигурация
└── src/
    ├── main.py                # Интерактивная игра (CLI)
    ├── game.py                # Игровой движок
    ├── board.py               # Валидация и BFS
    ├── cards.py               # Шаблоны карт
    ├── actions.py             # Типы действий
    ├── state.py               # Состояние игры
    ├── registry.py            # Реестр шаблонов
    ├── view.py                # Консольный интерфейс
    ├── random_agent.py       # Случайный бот
    ├── heuristic_agent.py     # Умный бот
    ├── web/
    │   ├── app.py            # Streamlit приложение
    │   ├── api.py            # FastAPI сервер
    │   ├── init_db.py        # Инициализация БД
    │   ├── auth.py           # Аутентификация
    │   ├── models.py         # Модели SQLAlchemy
    │   ├── schemas.py        # Pydantic схемы
    │   ├── bot_crud.py      # CRUD для ботов
    │   ├── docker_manager.py # Управление Docker
    │   └── game_proxy.py    # Прокси для ботов
    ├── bot-container/
    │   ├── Dockerfile        # Образ для бота
    │   └── bot_server.py    # HTTP сервер бота
    └── docs/
        ├── agent_interface.puml
        ├── game_actions.puml
        └── example_robot.py
```

---

## Создание своего робота

### Требования к классу агента

Ваш робот должен быть реализован как Python-класс:

```python
class MyRobot:
    def __init__(self, player_id: int):
        self.player_id = player_id
    
    def choose_action(self, game):
        legal_actions = game.get_legal_actions()
        if not legal_actions:
            return None
        # Ваша логика выбора хода
        return legal_actions[0]
```

### Доступные методы game

- `game.get_legal_actions()` - получить список легальных ходов
- `game.get_hand()` - получить свои карты
- `game.get_scores()` - получить текущий счёт
- `game.get_current_player()` - узнать чей ход
- `game.is_game_over()` - проверить окончена ли игра

### Доступные типы действий

| Тип | Описание | Параметры |
|-----|---------|-----------|
| `build` | Построить туннель/дверь/лестницу | `template_id, x, y, is_rotated_180` |
| `play_board` | Ключ/Обвал/Карта сокровищ | `template_id, x, y` |
| `play_player` | Поломка/Починка | `template_id, target_player_id` |
| `discard` | Сброс карт | `templates, repair_equipment` |

### Примеры ботов

См. `src/docs/example_robot.py`

---

## Правила игры

1. **Цель** - набрать больше золота чем противник
2. **Ходы** - построить туннель/лестницу/дверь или использовать карту действия
3. **Ограничение** - нельзя строить со сломанными инструментами
4. **Золото** - раскрывается при примыкании к карте с выходом
5. **Инструменты** - Лампа, Вагонетка, Кирка (все должны работать для строительства)
6. **Конец игры** - всё золото раскрыто или колода и руки пусты

---

## Консольный запуск

```bash
cd src

# Интерактивная игра (человек)
python3 main.py

# 1 игра двух ботов
python3 main.py --bot-vs-bot --bot1 random --bot2 heuristic

# N игр (бенчмарк)
python3 main.py --benchmark 100 --bot1 heuristic --bot2 random
```

---

## Тесты производительности

- Игра стабильно работает без ошибок
- HeuristicAgent выигрывает ~87% матчей против RandomAgent
- Среднее количество ходов до победы: 40-80
