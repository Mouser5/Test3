import random
import time
import logging
import traceback
from typing import Callable, Dict, Any, Tuple, Optional

from game import Game
from actions import AgentAction

# Предполагается, что у всех твоих агентов есть метод choose_action(game)
# и они принимают player_id в конструкторе.

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Arena")


class Arena:
    def __init__(self, agent1_name: str, agent1_factory: Callable[[int], Any],
                 agent2_name: str, agent2_factory: Callable[[int], Any]):
        """
        Фабрики (factory) — это функции, которые возвращают экземпляр агента по его ID.
        Пример: lambda p_id: RandomAgent(player_id=p_id)
        """
        self.a1_name = agent1_name
        self.a1_factory = agent1_factory
        self.a2_name = agent2_name
        self.a2_factory = agent2_factory

        self.stats = {
            self.a1_name: {"wins": 0, "gold": 0, "crashes": 0, "time_spent": 0.0, "moves_made": 0},
            self.a2_name: {"wins": 0, "gold": 0, "crashes": 0, "time_spent": 0.0, "moves_made": 0},
            "draws": 0
        }

    def play_match(self, seed: int, p0_name: str, p0_factory: Callable, p1_name: str, p1_factory: Callable) -> Optional[
        Dict]:
        """Проводит один изолированный матч."""

        # 1. ЖЕСТКАЯ ФИКСАЦИЯ СИДА.
        # Колода, раздача и золото будут абсолютно одинаковыми для этого seed.
        random.seed(seed)

        try:
            game = Game()
        except Exception as e:
            logger.error(f"Ошибка при инициализации игры (seed {seed}): {e}")
            return None

        agent0 = p0_factory(0)
        agent1 = p1_factory(1)
        agents = {0: agent0, 1: agent1}
        names = {0: p0_name, 1: p1_name}

        while not game.is_game_over():
            curr_p = game.state.current_player_id
            active_agent = agents[curr_p]
            active_name = names[curr_p]

            start_time = time.perf_counter()
            try:
                # Запрашиваем ход у агента
                action = active_agent.choose_action(game)
            except Exception as e:
                logger.error(f"[!] КРАШ БОТА {active_name} (seed {seed}):\n{traceback.format_exc()}")
                self.stats[active_name]["crashes"] += 1
                # Техническое поражение
                winner = 1 - curr_p
                return {"winner": names[winner], "scores": {0: 0, 1: 0}, "crash": True}

            move_time = time.perf_counter() - start_time
            self.stats[active_name]["time_spent"] += move_time
            self.stats[active_name]["moves_made"] += 1

            if action is None:
                # Если бот вернул None (нет ходов), нужно принудительно пропустить ход.
                # В текущей реализации game.py нужно чтобы шаг как-то завершился.
                # Если у тебя еще нет ActionPass, бот должен хотя бы сбросить карту.
                # Для защиты арены:
                logger.warning(f"Бот {active_name} вернул None. Завершаем матч техническим поражением.")
                winner = 1 - curr_p
                return {"winner": names[winner], "scores": {0: 0, 1: 0}, "crash": True}

            success, msg, _ = game.step(action)
            if not success:
                logger.error(f"Бот {active_name} попытался сделать нелегальный ход: {msg}")
                self.stats[active_name]["crashes"] += 1
                winner = 1 - curr_p
                return {"winner": names[winner], "scores": {0: 0, 1: 0}, "crash": True}

        # Матч завершен штатно
        scores = game.calculate_scores()

        if scores[0] > scores[1]:
            winner = p0_name
        elif scores[1] > scores[0]:
            winner = p1_name
        else:
            winner = "Draw"

        return {"winner": winner, "scores": {p0_name: scores[0], p1_name: scores[1]}, "crash": False}

    def run_tournament(self, num_seeds: int):
        """
        Запускает турнир на num_seeds уникальных раскладах.
        Для каждого расклада играется 2 матча (Зеркальная смена сторон).
        Итого сыграно будет num_seeds * 2 партий.
        """
        logger.info(f"=== ЗАПУСК АРЕНЫ: {self.a1_name} vs {self.a2_name} ===")
        logger.info(f"Семян (Seeds): {num_seeds}. Всего партий: {num_seeds * 2}")

        for i in range(num_seeds):
            # Генерируем случайный сид для этой пары игр
            # Используем системный random, чтобы сиды были разными в разных итерациях
            match_seed = random.randrange(1000000, 9999999)

            # Матч 1: Агент 1 (Игрок 0) vs Агент 2 (Игрок 1)
            res1 = self.play_match(match_seed, self.a1_name, self.a1_factory, self.a2_name, self.a2_factory)
            if res1:
                self._process_result(res1)

            # Матч 2: Агент 2 (Игрок 0) vs Агент 1 (Игрок 1)
            # Благодаря match_seed доска и колода будут АБСОЛЮТНО ТЕМИ ЖЕ
            res2 = self.play_match(match_seed, self.a2_name, self.a2_factory, self.a1_name, self.a1_factory)
            if res2:
                self._process_result(res2)

            if (i + 1) % 10 == 0 or (i + 1) == num_seeds:
                logger.info(f"Прогресс: сыграно {(i + 1) * 2} / {num_seeds * 2} партий...")

            self.print_results()

    def _process_result(self, res: Optional[Dict]):
        if not res or res.get("crash", False):
            return  # Очки при краше не начисляем

        if res["winner"] == "Draw":
            self.stats["draws"] += 1
        else:
            self.stats[res["winner"]]["wins"] += 1

        for name, score in res["scores"].items():
            self.stats[name]["gold"] += score

    def print_results(self):
        total_games = self.stats[self.a1_name]["wins"] + self.stats[self.a2_name]["wins"] + self.stats["draws"]

        print("\n" + "=" * 50)
        print(" " * 15 + "ИТОГИ ТУРНИРА")
        print("=" * 50)

        for name in [self.a1_name, self.a2_name]:
            s = self.stats[name]
            win_rate = (s["wins"] / total_games * 100) if total_games > 0 else 0
            avg_gold = (s["gold"] / total_games) if total_games > 0 else 0
            avg_time = (s["time_spent"] / s["moves_made"] * 1000) if s["moves_made"] > 0 else 0

            print(f"АГЕНТ: {name}")
            print(f"  Побед:       {s['wins']} ({win_rate:.1f}%)")
            print(f"  Ср. золото:  {avg_gold:.2f} за игру")
            print(f"  Ср. время:   {avg_time:.2f} мс / ход")
            if s["crashes"] > 0:
                print(f"  КРАШЕЙ:      {s['crashes']} (Агент выдал ошибку или неверный ход!)")
            print("-" * 50)

        print(f"НИЧЬИХ: {self.stats['draws']}")
        print("=" * 50 + "\n")


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===
if __name__ == "__main__":
    from random_agent import RandomAgent
    from mcts_agent import MCTSAgent

    # Пример 1: MCTS vs Random
    arena = Arena(
        agent1_name="MCTS_Agent",
        agent1_factory=lambda p_id: MCTSAgent(
            player_id=p_id,
            time_limit=0.3
            # max_iterations=100,
            # max_playouts_per_node=2
        ),

        agent2_name="Random_Agent",
        agent2_factory=lambda p_id: RandomAgent(player_id=p_id)
    )

    # Запуск 1 seed (2 партии) для быстрого теста
    arena.run_tournament(num_seeds=10)
