import random
import logging
import traceback
from typing import Optional

from game import Game
from actions import AgentAction

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
# Логи будут писаться в файл agent_debug.log, чтобы не засорять консоль
logging.basicConfig(
    filename="agent_debug.log",
    level=logging.INFO,  # Измените на DEBUG для записи каждого хода
    format="%(asctime)s | %(levelname)s | %(message)s",
    filemode="w",  # Перезаписывать лог при каждом запуске
)
logger = logging.getLogger(__name__)


class RandomAgent:
    """
    Случайный агент с поддержкой логирования выбора действий.
    """

    def __init__(self, player_id: int):
        self.player_id = player_id

    def choose_action(self, game: Game) -> Optional[AgentAction]:
        try:
            legal_actions = game.get_legal_actions()

            if not legal_actions:
                logger.warning(f"Игрок {self.player_id}: Нет легальных ходов.")
                return None

            action = random.choice(legal_actions)
            logger.debug(
                f"Игрок {self.player_id} выбрал действие: {action.model_dump_json()}"
            )
            return action

        except Exception as e:
            logger.critical(
                f"Критическая ошибка при генерации ходов игрока {self.player_id}!"
            )
            logger.critical(traceback.format_exc())
            # Сохраняем стейт, на котором сломался генератор ходов
            logger.critical(f"STATE DUMP: {game.state.model_dump_json()}")
            raise e
