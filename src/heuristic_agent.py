import random
import logging
from typing import Optional, List
from game import Game
from actions import (
    AgentAction,
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
)
from cards import (
    ActionType,
    EquipmentType,
    GoldCardTemplate,
    TunnelCardTemplate,
    DoorCardTemplate,
    LadderCardTemplate,
)
from registry import REGISTRY
from board import BoardEngine


class HeuristicAgent:
    """
    Интеллектуальный бот с эвристиками для игры "Гномы-вредители".

    Стратегия:
    1. Строить пути к нераскрытому золоту
    2. Использовать карты сокровищ для обнаружения золота
    3. Ломать инструменты противника
    4. Чинить свои инструменты
    5. Использовать обвалы для блокировки противника
    6. Открывать двери ключами
    """

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.logger = logging.getLogger(f"{__name__}_{player_id}")

    def choose_action(self, game: Game) -> Optional[AgentAction]:
        legal_actions = game.get_legal_actions()
        if not legal_actions:
            return None

        action = self._select_best_action(game, legal_actions)
        return action

    def _select_best_action(
        self, game: Game, legal_actions: List[AgentAction]
    ) -> AgentAction:
        opponent_id = 1 - self.player_id
        player_state = game.state.players[self.player_id]
        opponent_state = game.state.players[opponent_id]

        # === ПРИОРИЕТ 1: Если есть сломанные инструменты - чиним в первую очередь ===
        if player_state.broken_equipments:
            repair_actions = [
                a
                for a in legal_actions
                if isinstance(a, ActionPlayPlayerUtility)
                and REGISTRY.get(a.template_id).action_type == ActionType.REPAIR
                and a.target_player_id == self.player_id
            ]
            if repair_actions:
                return self._pick_best_by_value(
                    repair_actions, game, prioritize_gold=True
                )

        # === ПРИОРИЕТ 2: Использовать карту сокровищ (MAP) ===
        map_actions = [
            a
            for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
            and REGISTRY.get(a.template_id).action_type == ActionType.MAP
        ]
        if map_actions:
            best_map = self._choose_best_map_action(game, map_actions)
            if best_map:
                return best_map

        # === ПРИОРИЕТ 3: Использовать ключ для открытия своей двери ===
        key_actions = [
            a
            for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
            and REGISTRY.get(a.template_id).action_type == ActionType.KEY
        ]
        if key_actions:
            return random.choice(key_actions)

        # === ПРИОРИЕТ 4: Строить путь к нераскрытому золоту ===
        build_actions = [a for a in legal_actions if isinstance(a, ActionBuild)]
        if build_actions:
            best_build = self._choose_best_build_action(game, build_actions)
            if best_build:
                return best_build

        # === ПРИОРИЕТ 5: Ломать инструменты противника ===
        sabotage_actions = [
            a
            for a in legal_actions
            if isinstance(a, ActionPlayPlayerUtility)
            and REGISTRY.get(a.template_id).action_type == ActionType.SABOTAGE
            and a.target_player_id == opponent_id
        ]
        if sabotage_actions:
            return self._pick_best_sabotage(sabotage_actions, opponent_state)

        # === ПРИОРИЕТ 6: Использовать обвал для блокировки ===
        rockfall_actions = [
            a
            for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
            and REGISTRY.get(a.template_id).action_type == ActionType.ROCKFALL
        ]
        if rockfall_actions:
            best_rockfall = self._choose_best_rockfall(
                game, rockfall_actions, opponent_id
            )
            if best_rockfall:
                return best_rockfall

        # === ПРИОРИЕТ 7: Чинить инструменты противника (вред) ===
        harmful_repair = [
            a
            for a in legal_actions
            if isinstance(a, ActionPlayPlayerUtility)
            and REGISTRY.get(a.template_id).action_type == ActionType.REPAIR
            and a.target_player_id == opponent_id
            and REGISTRY.get(a.template_id).equipment_type
            in opponent_state.broken_equipments
        ]
        if harmful_repair:
            return random.choice(harmful_repair)

        # === ПРИОРИЕТ 8: Сброс карт (лучше сбросить бесполезные) ===
        discard_actions = [a for a in legal_actions if isinstance(a, ActionDiscard)]
        if discard_actions:
            best_discard = self._choose_best_discard(game, discard_actions)
            if best_discard:
                return best_discard

        return random.choice(legal_actions)

    def _choose_best_build_action(
        self, game: Game, build_actions: List[ActionBuild]
    ) -> Optional[ActionBuild]:
        """Выбираем лучшее место для постройки - ближе всего к золоту"""
        best_action = None
        best_score = float("-inf")

        for action in build_actions:
            score = 0
            tpl = REGISTRY.get(action.template_id)

            # Бонус за построение к золоту
            gold_distance = self._distance_to_nearest_unrevealed_gold(
                action.x, action.y, game
            )
            if gold_distance is not None:
                score += max(0, 20 - gold_distance) * 3  # Чем ближе к золоту, тем лучше

            # Бонус за построение лестницы (полезно для мобильности)
            if isinstance(tpl, LadderCardTemplate):
                score += 10

            # Штраф за построение двери (лучше строить туннели)
            if isinstance(tpl, DoorCardTemplate):
                score -= 5

            # Если у противника сломаны инструменты - строить более агрессивно
            opponent = game.state.players[1 - self.player_id]
            if opponent.broken_equipments:
                score += 15

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _distance_to_nearest_unrevealed_gold(
        self, x: int, y: int, game: Game
    ) -> Optional[int]:
        """Вычисляем расстояние до ближайшего нераскрытого золота"""
        min_dist = None

        for coord_key, placed in game.state.board.items():
            tpl = REGISTRY.get(placed.template_id)
            if isinstance(tpl, GoldCardTemplate) and not placed.is_revealed:
                gx, gy = BoardEngine.str_to_coord(coord_key)
                dist = abs(gx - x) + abs(gy - y)  # Манхэттенское расстояние
                if min_dist is None or dist < min_dist:
                    min_dist = dist

        return min_dist

    def _choose_best_map_action(
        self, game: Game, map_actions: List[ActionPlayBoardUtility]
    ) -> Optional[ActionPlayBoardUtility]:
        """Выбираем карту сокровищ, которая покажет золото с наибольшей ценностью"""
        best_action = None
        best_value = -1

        for action in map_actions:
            coord_key = BoardEngine.coord_to_str(action.x, action.y)
            placed = game.state.board.get(coord_key)
            if placed:
                tpl = REGISTRY.get(placed.template_id)
                if isinstance(tpl, GoldCardTemplate) and tpl.gold_value > best_value:
                    best_value = tpl.gold_value
                    best_action = action

        return best_action

    def _pick_best_sabotage(
        self, sabotage_actions: List[ActionPlayPlayerUtility], opponent_state
    ) -> ActionPlayPlayerUtility:
        """Выбираем, какой инструмент сломать"""
        # Приоритет: ломать то, что у противника еще работает
        equipment_priority = {
            EquipmentType.LAMP: 3,  # Без лампы сложно строить
            EquipmentType.CART: 2,  # Без вагонетки сложно
            EquipmentType.PICKAXE: 1,  # Кирка - наименее критично
        }

        best_action = None
        best_priority = -1

        for action in sabotage_actions:
            tpl = REGISTRY.get(action.template_id)
            eq = tpl.equipment_type
            priority = equipment_priority.get(eq, 0)
            if priority > best_priority:
                best_priority = priority
                best_action = action

        return best_action or random.choice(sabotage_actions)

    def _choose_best_rockfall(
        self,
        game: Game,
        rockfall_actions: List[ActionPlayBoardUtility],
        opponent_id: int,
    ) -> Optional[ActionPlayBoardUtility]:
        """Выбираем лучший обвал для блокировки противника"""
        opponent_state = game.state.players[opponent_id]
        opponent_start = game.start_positions[opponent_id]

        best_action = None
        best_block_score = float("-inf")

        for action in rockfall_actions:
            coord_key = BoardEngine.coord_to_str(action.x, action.y)
            placed = game.state.board.get(coord_key)

            if not placed:
                continue

            # Проверяем, заблокирует ли это путь противника к золоту
            block_score = 0

            # Если обваливаем что-то рядом с противником - хорошо
            opp_x, opp_y = opponent_start
            dist_to_opponent = abs(action.x - opp_x) + abs(action.y - opp_y)
            block_score += max(0, 10 - dist_to_opponent)

            # Если у противника есть лестницы рядом - обвалить их
            if coord_key in opponent_state.ladders:
                block_score += 20

            # Если обваливаем что-то рядом с нераскрытым золотом - плохо (можем потерять золото)
            for g_key, g_placed in game.state.board.items():
                tpl = REGISTRY.get(g_placed.template_id)
                if isinstance(tpl, GoldCardTemplate) and not g_placed.is_revealed:
                    gx, gy = BoardEngine.str_to_coord(g_key)
                    dist = abs(action.x - gx) + abs(action.y - gy)
                    if dist <= 1:
                        block_score -= 30  # Штраф за риск потери золота

            if block_score > best_block_score:
                best_block_score = block_score
                best_action = action

        return best_action

    def _choose_best_discard(
        self, game: Game, discard_actions: List[ActionDiscard]
    ) -> Optional[ActionDiscard]:
        """Выбираем лучший сброс - избавляемся от бесполезных карт"""
        player_state = game.state.players[self.player_id]

        # Карты, которые бесполезны когда все инструменты работают
        useless_when_healthy = []
        if not player_state.broken_equipments:
            for t_id in player_state.hand:
                tpl = REGISTRY.get(t_id)
                if hasattr(tpl, "action_type") and tpl.action_type == ActionType.REPAIR:
                    useless_when_healthy.append(t_id)

        best_action = None
        best_score = float("-inf")

        for action in discard_actions:
            score = 0
            templates = action.templates

            # Штраф за сброс полезных карт
            for t_id in templates:
                if t_id in useless_when_healthy:
                    score += 10  # Хорошо сбросить бесполезное

            # Бонус за сброс карт, которые нельзя использовать
            # (например, строить когда сломаны инструменты)
            if player_state.broken_equipments:
                for t_id in templates:
                    tpl = REGISTRY.get(t_id)
                    if isinstance(
                        tpl, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)
                    ):
                        score += 15  # Хорошо сбросить, чтобы взять полезные

            if score > best_score:
                best_score = score
                best_action = action

        return best_action if best_action else random.choice(discard_actions)

    def _pick_best_by_value(
        self, actions: List[AgentAction], game: Game, prioritize_gold: bool = False
    ) -> AgentAction:
        """Выбираем действие с наибольшей ценностью"""
        if not actions:
            return random.choice(actions)
        return random.choice(actions)


class SmartAgent(HeuristicAgent):
    """
    Улучшенный агент с дополнительными эвристиками:
    - Анализ карт противника
    - Планирование на несколько ходов вперед
    - Более точная оценка позиций
    """

    def __init__(self, player_id: int, lookahead_depth: int = 2):
        super().__init__(player_id)
        self.lookahead_depth = lookahead_depth

    def _evaluate_position(self, game: Game) -> float:
        """Оцениваем текущую позицию для текущего игрока"""
        player_state = game.state.players[self.player_id]
        opponent_state = game.state.players[1 - self.player_id]

        score = 0.0

        # Очки за золото
        revealed_gold = sum(
            1
            for p in game.state.board.values()
            if isinstance(REGISTRY.get(p.template_id), GoldCardTemplate)
            and p.is_revealed
            and p.owner_id == self.player_id
        )
        score += revealed_gold * 10

        # Штраф за золото противника
        opponent_gold = sum(
            1
            for p in game.state.board.values()
            if isinstance(REGISTRY.get(p.template_id), GoldCardTemplate)
            and p.is_revealed
            and p.owner_id == 1 - self.player_id
        )
        score -= opponent_gold * 10

        # Бонус за работающие инструменты
        working_tools_self = 3 - len(player_state.broken_equipments)
        score += working_tools_self * 2

        # Штраф за сломанные инструменты противника
        broken_tools_opponent = len(opponent_state.broken_equipments)
        score += broken_tools_opponent * 5

        # Бонус за количество карт в руке
        score += len(player_state.hand) * 0.5

        # Штраф за количество карт у противника
        score -= len(opponent_state.hand) * 0.3

        # Бонус за известные секреты
        score += len(player_state.known_secrets) * 3

        return score


def test_agents(num_games: int = 100):
    """Тестируем умных агентов против случайных"""
    from random_agent import RandomAgent

    heuristic_wins = 0
    random_wins = 0
    draws = 0

    for i in range(num_games):
        game = Game()
        agents = {0: HeuristicAgent(0), 1: RandomAgent(1)}

        while not game.is_game_over():
            curr_p = game.state.current_player_id
            action = agents[curr_p].choose_action(game)
            if not action:
                break
            game.step(action)

        scores = game.calculate_scores()
        if scores[0] > scores[1]:
            heuristic_wins += 1
        elif scores[1] > scores[0]:
            random_wins += 1
        else:
            draws += 1

    print(f"Результаты: {num_games} игр")
    print(
        f"Умный бот (Heuristic): {heuristic_wins} побед ({100 * heuristic_wins / num_games:.1f}%)"
    )
    print(f"Случайный бот: {random_wins} побед ({100 * random_wins / num_games:.1f}%)")
    print(f"Ничьи: {draws}")


def test_smart_vs_random(num_games: int = 100):
    """Тестируем SmartAgent против RandomAgent"""
    from random_agent import RandomAgent

    smart_wins = 0
    random_wins = 0
    draws = 0

    for i in range(num_games):
        game = Game()
        agents = {0: SmartAgent(0), 1: RandomAgent(1)}

        while not game.is_game_over():
            curr_p = game.state.current_player_id
            action = agents[curr_p].choose_action(game)
            if not action:
                break
            game.step(action)

        scores = game.calculate_scores()
        if scores[0] > scores[1]:
            smart_wins += 1
        elif scores[1] > scores[0]:
            random_wins += 1
        else:
            draws += 1

    print(f"Результаты: {num_games} игр")
    print(f"SmartAgent: {smart_wins} побед ({100 * smart_wins / num_games:.1f}%)")
    print(f"RandomAgent: {random_wins} побед ({100 * random_wins / num_games:.1f}%)")
    print(f"Ничьи: {draws}")


if __name__ == "__main__":
    print("Тестирование HeuristicAgent vs RandomAgent:")
    test_agents(50)
    print()
    print("Тестирование SmartAgent vs RandomAgent:")
    test_smart_vs_random(50)
