import random
import math
import time
import logging
import traceback
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

from game import Game
from actions import AgentAction
from determinizer import Determinizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MCTSNode:
    action: Optional[AgentAction] = None
    parent: Optional['MCTSNode'] = None
    children: Dict[str, 'MCTSNode'] = field(default_factory=dict)

    visits: int = 0
    reward_p0: float = 0.0  # Накопленная награда для Игрока 0
    reward_p1: float = 0.0  # Накопленная награда для Игрока 1

    # Игрок, который должен выбрать СЛЕДУЮЩЕЕ действие из этого узла (чьи дети)
    active_player: int = 0

    def ucb_score(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float('inf')

        # Кто выбирает ход из этого узла? Родитель!
        # Значит, оцениваем узел с точки зрения родительского игрока.
        if self.parent.active_player == 0:
            exploitation = self.reward_p0 / self.visits
        else:
            exploitation = self.reward_p1 / self.visits

        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def backprop(self, r0: float, r1: float):
        self.visits += 1
        self.reward_p0 += r0
        self.reward_p1 += r1
        if self.parent:
            self.parent.backprop(r0, r1)


class MCTSAgent:
    def __init__(self, player_id: int, time_limit: float = 0.5, exploration_constant: float = 1.414):
        self.player_id = player_id
        self.time_limit = time_limit
        self.exploration_constant = exploration_constant
        self.root: Optional[MCTSNode] = None

    def choose_action(self, game: Game) -> Optional[AgentAction]:
        try:
            legal_actions = game.get_legal_actions()
            if not legal_actions:
                return None
            if len(legal_actions) == 1:
                return legal_actions[0]

            # Корень дерева - это текущее состояние игры
            self.root = MCTSNode(active_player=game.state.current_player_id)
            self._mcts_search(game)

            best_action = self._select_best_action()
            return best_action if best_action else random.choice(legal_actions)

        except Exception as e:
            logger.error(f"Ошибка в MCTS: {e}\n{traceback.format_exc()}")
            return random.choice(game.get_legal_actions())

    def _mcts_search(self, game: Game) -> None:
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < self.time_limit:
            # 0. DETERMINIZATION: Создаем один "параллельный мир" на всю итерацию
            sim_game = self._clone_game(game)
            sim_game.state = Determinizer.create_random_hypothesis(sim_game.state, self.player_id)

            node = self.root

            # 1. SELECTION & EXPANSION
            # Спускаемся по дереву, пока не найдем нераскрытый узел или конец игры
            while not sim_game.is_game_over():
                actions = sim_game.get_legal_actions()
                if not actions:
                    break

                # Ищем действия, которых еще нет в дереве (неисследованные)
                untried = [a for a in actions if str(a) not in node.children]

                if untried:
                    # EXPANSION: Расширяем дерево одним новым узлом
                    action = random.choice(untried)
                    sim_game.step(action)
                    next_player = sim_game.state.current_player_id

                    child = MCTSNode(action=action, parent=node, active_player=next_player)
                    node.children[str(action)] = child
                    node = child
                    break  # Переходим к симуляции из нового узла
                else:
                    # SELECTION: Все легальные действия (в этой гипотезе!) уже в дереве
                    legal_children = [node.children[str(a)] for a in actions]
                    node = max(legal_children, key=lambda c: c.ucb_score(self.exploration_constant))
                    sim_game.step(node.action)

            # 2. SIMULATION: Быстрый случайный плейаут до конца игры
            r0, r1 = self._simulate_playout(sim_game)

            # 3. BACKPROPAGATION: Обновляем статистику вверх по дереву
            node.backprop(r0, r1)

    def _simulate_playout(self, game: Game) -> Tuple[float, float]:
        step_count = 0
        while not game.is_game_over() and step_count < 100:
            actions = game.get_legal_actions()
            if not actions: break

            # Умная эвристика O(1): Чаще строим пути, реже сбрасываем
            build_actions = [a for a in actions if a.type == "build"]
            utility_actions = [a for a in actions if a.type in ["play_board_utility", "play_player_utility"]]

            rnd = random.random()
            if build_actions and rnd < 0.50:
                action = random.choice(build_actions)
            elif utility_actions and rnd < 0.80:
                action = random.choice(utility_actions)
            else:
                action = random.choice(actions)

            game.step(action)
            step_count += 1

        scores = game.calculate_scores()
        gold_0 = scores[0]
        gold_1 = scores[1]

        # Базовая победа: 1.0, Поражение: -1.0
        if gold_0 > gold_1:
            r0, r1 = 1.0, -1.0
        elif gold_0 < gold_1:
            r0, r1 = -1.0, 1.0
        else:
            r0, r1 = 0.0, 0.0

        # Reward Shaping: Отрыв по золоту и бонус за изучение секретов
        margin = (gold_0 - gold_1) / 20.0
        r0 += margin
        r1 -= margin

        # Микро-бонус за использование Карты сокровищ (даже если проиграли)
        r0 += len(game.state.players[0].known_secrets) * 0.05
        r1 += len(game.state.players[1].known_secrets) * 0.05

        return r0, r1

    def _select_best_action(self) -> Optional[AgentAction]:
        if not self.root or not self.root.children: return None
        # Ищем самого "жирного" ребенка (наиболее посещаемого)
        best_node = max(self.root.children.values(), key=lambda node: node.visits)
        return best_node.action

    def _clone_game(self, game: Game) -> Game:
        cloned_game = Game.__new__(Game)
        cloned_game.state = game.state.clone()
        cloned_game.board_engine = game.board_engine
        cloned_game.start_positions = game.start_positions
        return cloned_game


if __name__ == "__main__":
    from random_agent import RandomAgent
    from arena import Arena

    arena = Arena(
        agent1_name="MCTS_Agent",
        agent1_factory=lambda p_id: MCTSAgent(player_id=p_id, time_limit=0.7),
        agent2_name="Random_Agent",
        agent2_factory=lambda p_id: RandomAgent(player_id=p_id)
    )
    arena.run_tournament(num_seeds=10)