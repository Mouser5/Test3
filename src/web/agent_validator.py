import inspect
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    class_name: Optional[str] = None
    has_choose_action: bool = False
    has_player_id_param: bool = False


class AgentValidator:
    REQUIRED_METHOD = "choose_action"
    REQUIRED_PARAM = "game"

    @classmethod
    def validate_agent_class(cls, agent_class: type) -> ValidationResult:
        errors = []
        warnings = []

        class_name = agent_class.__name__

        if not hasattr(agent_class, cls.REQUIRED_METHOD):
            errors.append(
                f"Класс '{class_name}' не имеет метода '{cls.REQUIRED_METHOD}'"
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                class_name=class_name,
                has_choose_action=False,
            )

        choose_action = getattr(agent_class, cls.REQUIRED_METHOD)

        if not callable(choose_action):
            errors.append(
                f"'{cls.REQUIRED_METHOD}' должен быть методом, а не атрибутом"
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                class_name=class_name,
                has_choose_action=False,
            )

        try:
            sig = inspect.signature(choose_action)
            params = list(sig.parameters.keys())

            if cls.REQUIRED_PARAM not in params and len(params) < 2:
                errors.append(
                    f"Метод '{cls.REQUIRED_METHOD}' должен принимать параметр 'game'"
                )
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    class_name=class_name,
                    has_choose_action=True,
                    has_player_id_param=False,
                )

        except (ValueError, TypeError) as e:
            errors.append(f"Не удалось проверить сигнатуру метода: {e}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                class_name=class_name,
                has_choose_action=True,
            )

        try:
            sig_init = inspect.signature(agent_class.__init__)
            init_params = list(sig_init.parameters.keys())

            if "player_id" not in init_params and "self" in init_params:
                if len(init_params) < 2:
                    warnings.append(
                        "Рекомендуется, чтобы __init__ принимал player_id: int"
                    )
        except Exception:
            pass

        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings,
            class_name=class_name,
            has_choose_action=True,
            has_player_id_param=True,
        )

    @classmethod
    def validate_code_string(cls, code: str) -> Tuple[bool, List[str]]:
        errors = []

        try:
            compile(code, "<validation>", "exec")
        except SyntaxError as e:
            errors.append(f"Синтаксическая ошибка (строка {e.lineno}): {e.msg}")
            return False, errors

        if "def choose_action" not in code and "choose_action" not in code:
            errors.append("Код не содержит метод 'choose_action'")
            return False, errors

        if "class " not in code:
            errors.append("Код не содержит определения класса")
            return False, errors

        return True, errors

    @classmethod
    def validate_agent_class_from_code(cls, code: str) -> ValidationResult:
        import types
        import random
        import math
        import sys

        errors = []
        warnings = []

        module_name = "temp_validation_module"
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]

            module = types.ModuleType(module_name)
            sys.modules[module_name] = module

            exec_globals = {
                "__name__": module_name,
                "random": random,
                "math": math,
            }
            exec(compile(code, "<bot_code>", "exec"), exec_globals)

            agent_class = None
            for name in exec_globals:
                obj = exec_globals[name]
                if isinstance(obj, type) and hasattr(obj, "choose_action"):
                    agent_class = obj
                    break

            if agent_class is None:
                return ValidationResult(
                    is_valid=False,
                    errors=["Не найден класс агента с методом choose_action"],
                    warnings=[],
                )

            result = cls.validate_agent_class(agent_class)
            return result

        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Синтаксическая ошибка (строка {e.lineno}): {e.msg}"],
                warnings=[],
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Ошибка при загрузке кода: {str(e)}"],
                warnings=[],
            )
        finally:
            if module_name in sys.modules:
                del sys.modules[module_name]

    @classmethod
    def get_agent_requirements_text(cls) -> str:
        return """
## Требования к классу агента

Ваш робот должен быть реализован как Python-класс со следующими характеристиками:

### Обязательные элементы:

1. **Конструктор** — должен принимать `player_id: int`:
```python
def __init__(self, player_id: int):
    self.player_id = player_id
```

2. **Метод `choose_action`** — принимает объект игры и возвращает действие:
```python
def choose_action(self, game: Game) -> Optional[AgentAction]:
    # Ваш код здесь
    pass
```

### Доступные типы действий:

| Класс | Описание | Параметры |
|-------|----------|-----------|
| `ActionBuild` | Построить туннель/дверь/лестницу | `template_id, x, y, is_rotated_180` |
| `ActionPlayBoardUtility` | Сыграть карту на поле (ключ/обвал/карта) | `template_id, x, y` |
| `ActionPlayPlayerUtility` | Сыграть карту на игрока (поломка/починка) | `template_id, target_player_id` |
| `ActionDiscard` | Сбросить карты | `templates, repair_equipment` |

### Пример минимального робота:

```python
import random

class MyAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id
    
    def choose_action(self, game):
        legal_actions = game.get_legal_actions()
        if not legal_actions:
            return None
        return random.choice(legal_actions)
```

### Важно:
- Используйте `game.get_legal_actions()` для получения списка легальных ходов
- Возвращайте `None` если нет доступных ходов
- Не изменяйте состояние игры напрямую!
"""


validator = AgentValidator()
