import random
import time
import logging
import traceback
from typing import Optional

from game import Game
from actions import AgentAction
from view import ConsoleView

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


def run_visual_match():
    """Запускает одну партию между двумя случайными ботами с выводом в консоль."""
    logger.info("=== ЗАПУСК ВИЗУАЛЬНОГО МАТЧА ===")
    game = Game()
    view = ConsoleView()
    agents = {0: RandomAgent(0), 1: RandomAgent(1)}

    view.print_message("=== СТАРТ ПАРТИИ БОТОВ ===")
    view.print_board(game.state)

    turn_count = 0
    try:
        while not game.is_game_over():
            curr_p = game.state.current_player_id
            agent = agents[curr_p]

            action = agent.choose_action(game)
            if not action:
                view.print_message(
                    f"У игрока {curr_p} нет легальных ходов!", is_error=True
                )
                break

            success, msg, rev_gold = game.step(action)
            turn_count += 1

            if not success:
                # Такого происходить не должно, так как мы выбираем из легальных ходов
                logger.error(
                    f"Легальный ход был отклонен движком! Действие: {action.model_dump_json()} | Причина: {msg}"
                )

            if turn_count % 10 == 0 or rev_gold is not None or "Обвал" in msg:
                view.print_message(
                    f"Ход {turn_count}: Игрок {curr_p} выполнил {action.type}"
                )
                if msg:
                    view.print_message(f"> {msg}")
                if rev_gold:
                    view.print_message(f"✨ НАЙДЕНО ЗОЛОТО: {rev_gold} ✨")
                view.print_board(game.state)
                time.sleep(0.3)

        scores = game.calculate_scores()
        view.print_message("\n=== ИГРА ОКОНЧЕНА ===")
        view.print_board(game.state)
        print(f"Сделано ходов: {turn_count}")
        print(f"ИТОГОВЫЙ СЧЕТ: Игрок 0: {scores[0]}, Игрок 1: {scores[1]}")
        logger.info(f"Матч успешно завершен за {turn_count} ходов. Счет: {scores}")

    except Exception:
        print("\n[!] ПРОИЗОШЕЛ КРАШ! Проверьте agent_debug.log")
        logger.critical("КРАШ ВО ВРЕМЯ ИГРОВОГО ЦИКЛА!")
        logger.critical(traceback.format_exc())
        logger.critical(f"STATE DUMP: {game.state.model_dump_json()}")


def run_benchmark(num_games: int = 1000):
    """
    Запускает тысячи партий. При ошибке ловит её, сохраняет данные и останавливает бенчмарк.
    """
    print(f"\nЗапуск бенчмарка: {num_games} партий...")
    logger.info(f"=== ЗАПУСК БЕНЧМАРКА НА {num_games} ПАРТИЙ ===")
    agents = {0: RandomAgent(0), 1: RandomAgent(1)}

    start_time = time.perf_counter()
    total_turns = 0
    games_completed = 0

    for game_idx in range(num_games):
        game = Game()
        try:
            while not game.is_game_over():
                curr_p = game.state.current_player_id
                action = agents[curr_p].choose_action(game)
                if not action:
                    break

                success, msg, _ = game.step(action)
                if not success:
                    logger.error(
                        f"Game {game_idx}: Ход отклонен: {msg} | Action: {action.model_dump_json()}"
                    )

                total_turns += 1
            games_completed += 1

            if games_completed % 100 == 0:
                logger.info(f"Прогресс: сыграно {games_completed}/{num_games} партий.")

        except Exception:
            print(
                f"\n[!] КРАШ НА ПАРТИИ #{game_idx}! Бенчмарк остановлен. Логи сохранены в agent_debug.log"
            )
            logger.critical(
                f"КРАШ НА ПАРТИИ #{game_idx} (Ход матча: {game.state.turn_number})"
            )
            logger.critical(traceback.format_exc())
            logger.critical(f"STATE DUMP: {game.state.model_dump_json()}")
            break  # Прерываем бенчмарк при первой же ошибке

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    tps = total_turns / elapsed if elapsed > 0 else 0
    gps = games_completed / elapsed if elapsed > 0 else 0

    print("-" * 30)
    print(f"Сыграно партий:     {games_completed}")
    print(f"Всего сделано ходов: {total_turns}")
    print(f"Время выполнения:   {elapsed:.3f} сек")
    print("-" * 30)
    print(f"Ходов в секунду (TPS):   {tps:.0f}")
    print(f"Партий в секунду (GPS):  {gps:.0f}")
    print("-" * 30)
    logger.info(f"Бенчмарк завершен. TPS: {tps:.0f}, GPS: {gps:.0f}")


if __name__ == "__main__":
    # Для отладки конкретных ходов раскомментируйте строку ниже:
    # logger.setLevel(logging.DEBUG)

    # Режим 1: Посмотреть, как боты играют одну партию
    # run_visual_match()

    # Режим 2: Проверить реальную скорость оптимизированного движка
    run_benchmark(1000)
