# GnomesDSL

DSL парсер для игры "Гномы-вредители: Дуэль".

Пакет предоставляет классы для кодирования игрового состояния в DSL-формат,
декодирования DSL-строк в действия игрока, и валидации ходов.

## Установка

```bash
pip install gnomes-dsl
```

## Использование

```python
from gnomes_dsl import (
    DSLEncoder, DSLDecoder, DSLActionValidator,
    DSLPlayerAction, DSLOperation,
    ActionBuild, ActionDiscard,
    AgentAction, EquipmentType,
)

# Кодирование состояния
encoder = DSLEncoder(game_state_dict, player_id=0)
dsl_string = encoder.encode_state()

# Декодирование действия
decoder = DSLDecoder(dsl_string, game_state_dict, player_id=0)
action = decoder.parse_action()

# Валидация
validator = DSLActionValidator(game_state_dict, player_id=0)
is_valid, msg = validator.is_action_valid(action)
```
