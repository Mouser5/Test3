import uuid
import sys
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
import traceback


@dataclass
class UserSession:
    session_id: str
    uploaded_code: Optional[str] = None
    agent_class: Optional[type] = None
    agent_module_name: Optional[str] = None
    validation_errors: list = field(default_factory=list)
    validation_success: bool = False


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = UserSession(session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[UserSession]:
        return self._sessions.get(session_id)

    def store_uploaded_code(self, session_id: str, code: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.uploaded_code = code
        session.validation_success = False
        session.validation_errors = []
        return True

    def load_agent_from_code(
        self, session_id: str, code: str
    ) -> tuple[Optional[type], list[str]]:
        module_name = f"user_agent_{session_id.replace('-', '_').replace(' ', '_')}"

        try:
            if module_name in sys.modules:
                del sys.modules[module_name]

            import random
            import math

            exec_globals = {
                "__name__": module_name,
                "random": random,
                "math": math,
            }
            exec(compile(code, f"<user_agent_{session_id}>", "exec"), exec_globals)

            for name in exec_globals:
                obj = exec_globals[name]
                if isinstance(obj, type) and hasattr(obj, "choose_action"):
                    agent_class = obj
                    return agent_class, []

            return None, [
                "Не найден класс агента.",
                "Класс должен иметь метод choose_action(game).",
            ]

        except SyntaxError as e:
            error_msg = f"Синтаксическая ошибка (строка {e.lineno}): {e.msg}"
            return None, [error_msg]
        except Exception as e:
            error_msg = f"Ошибка при загрузке кода: {str(e)}\n{traceback.format_exc()}"
            return None, [error_msg]

    def _find_agent_class(self, module) -> Optional[type]:
        for name in dir(module):
            obj = getattr(module, name)
            if not isinstance(obj, type):
                continue

            if hasattr(obj, "choose_action") and callable(
                getattr(obj, "choose_action")
            ):
                import inspect

                sig = inspect.signature(obj.choose_action)
                params = list(sig.parameters.keys())
                if len(params) >= 1 and "game" in params:
                    return obj

        return None

    def create_agent_instance(self, session_id: str, player_id: int) -> Optional[Any]:
        session = self.get_session(session_id)
        if not session or not session.agent_class:
            return None

        try:
            return session.agent_class(player_id)
        except Exception:
            return None

    def clear_session(self, session_id: str):
        session = self.get_session(session_id)
        if session and session.agent_module_name:
            if session.agent_module_name in sys.modules:
                del sys.modules[session.agent_module_name]

        if session_id in self._sessions:
            del self._sessions[session_id]


session_manager = SessionManager()
