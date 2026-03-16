import sys
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import Game
from actions import (
    AgentAction,
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
)
from registry import REGISTRY
from random_agent import RandomAgent
from heuristic_agent import HeuristicAgent, SmartAgent
from view import ConsoleView


BUILTIN_AGENTS = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,
    "smart": SmartAgent,
}


@dataclass
class GameLog:
    turn_number: int
    round_number: int
    player_id: int
    action_type: str
    action_description: str
    message: str
    gold_found: Optional[int] = None


@dataclass
class SingleGameResult:
    winner: Optional[int]
    winner_name: str
    total_scores: Dict[int, int]
    turns: int
    errors: List[str]
    logs: List[GameLog] = field(default_factory=list)
    round_scores: List[Dict[int, int]] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    wins: Dict[str, int]
    total_games: int
    total_turns: int
    total_errors: int
    elapsed_time: float
    games_per_second: float
    turns_per_second: float


def _format_action(action: AgentAction, game: Game) -> str:
    tpl_id = getattr(action, "template_id", None)
    tpl = REGISTRY.get(tpl_id) if tpl_id else None
    tpl_name = tpl.name if tpl else tpl_id

    if isinstance(action, ActionBuild):
        rot = " (повёрнута)" if action.is_rotated_180 else ""
        return f"ПОСТРОЙКА: {tpl_name} на ({action.x}, {action.y}){rot}"
    elif isinstance(action, ActionPlayBoardUtility):
        return f"ДЕЙСТВИЕ: {tpl_name} на ({action.x}, {action.y})"
    elif isinstance(action, ActionPlayPlayerUtility):
        target = action.target_player_id
        return f"ДЕЙСТВИЕ: {tpl_name} на игрока {target}"
    elif isinstance(action, ActionDiscard):
        if action.repair_equipment:
            return f"СБРОС + ПОЧИНКА: {action.repair_equipment.value}"
        return f"СБРОС: {len(action.templates)} карт"
    return str(action.type)


def run_single_game(
    agent1_class: type,
    agent2_class: type,
    agent1_name: str = "Агент 1",
    agent2_name: str = "Агент 2",
    verbose: bool = True,
) -> SingleGameResult:
    game = Game()
    agents = {
        0: agent1_class(0),
        1: agent2_class(1),
    }

    logs: List[GameLog] = []
    errors: List[str] = []
    round_scores: List[Dict[int, int]] = []
    turn_count = 0

    while not game.is_game_over():
        while not game.is_round_over():
            curr_p = game.state.current_player_id
            agent = agents[curr_p]

            try:
                action = agent.choose_action(game)
                if not action:
                    logs.append(
                        GameLog(
                            turn_number=turn_count,
                            round_number=game.state.round_number,
                            player_id=curr_p,
                            action_type="skip",
                            action_description="Нет легальных ходов",
                            message="Пропуск хода",
                        )
                    )
                    game.state.current_player_id = 1 - curr_p
                    continue

                success, msg, rev_gold = game.step(action)
                turn_count += 1

                agent_name = agent1_name if curr_p == 0 else agent2_name
                action_desc = _format_action(action, game)

                logs.append(
                    GameLog(
                        turn_number=turn_count,
                        round_number=game.state.round_number,
                        player_id=curr_p,
                        action_type=action.type,
                        action_description=action_desc,
                        message=msg,
                        gold_found=rev_gold,
                    )
                )

                if not success:
                    error_msg = f"Ход отклонён: {msg}"
                    errors.append(error_msg)
                    raise RuntimeError(error_msg)

            except Exception as e:
                error_msg = (
                    f"Ошибка агента {curr_p}: {str(e)}\n{traceback.format_exc()}"
                )
                errors.append(error_msg)
                return SingleGameResult(
                    winner=None,
                    winner_name="ОШИБКА",
                    total_scores=game.state.total_scores.copy(),
                    turns=turn_count,
                    errors=errors,
                    logs=logs,
                    round_scores=round_scores,
                )

        round_ended, round_score = game.check_round_end()
        if round_ended and round_score:
            round_scores.append(round_score.copy())

    total_scores = game.state.total_scores
    winner = None
    winner_name = "Ничья"

    if total_scores[0] > total_scores[1]:
        winner = 0
        winner_name = agent1_name
    elif total_scores[1] > total_scores[0]:
        winner = 1
        winner_name = agent2_name

    return SingleGameResult(
        winner=winner,
        winner_name=winner_name,
        total_scores=total_scores,
        turns=turn_count,
        errors=errors,
        logs=logs,
        round_scores=round_scores,
    )


def run_benchmark(
    agent1_class: type,
    agent2_class: type,
    num_games: int,
    agent1_name: str = "Агент 1",
    agent2_name: str = "Агент 2",
) -> BenchmarkResult:
    start_time = time.perf_counter()
    total_turns = 0
    total_errors = 0
    wins = {agent1_name: 0, agent2_name: 0, "draw": 0}

    for game_idx in range(num_games):
        game = Game()
        agents = {
            0: agent1_class(0),
            1: agent2_class(1),
        }

        try:
            while not game.is_game_over():
                while not game.is_round_over():
                    curr_p = game.state.current_player_id
                    try:
                        action = agents[curr_p].choose_action(game)
                        if not action:
                            game.state.current_player_id = 1 - curr_p
                            continue

                        success, msg, _ = game.step(action)
                        if not success:
                            total_errors += 1
                        total_turns += 1
                    except Exception:
                        total_errors += 1
                        game.state.current_player_id = 1 - game.state.current_player_id

                game.check_round_end()

            total_scores = game.state.total_scores
            if total_scores[0] > total_scores[1]:
                wins[agent1_name] += 1
            elif total_scores[1] > total_scores[0]:
                wins[agent2_name] += 1
            else:
                wins["draw"] += 1

        except Exception:
            total_errors += 1

    elapsed = time.perf_counter() - start_time
    tps = total_turns / elapsed if elapsed > 0 else 0
    gps = num_games / elapsed if elapsed > 0 else 0

    return BenchmarkResult(
        wins=wins,
        total_games=num_games,
        total_turns=total_turns,
        total_errors=total_errors,
        elapsed_time=elapsed,
        games_per_second=gps,
        turns_per_second=tps,
    )


def get_board_ascii(game: Game) -> str:
    view = ConsoleView()
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        view.print_board(game.state)

    return f.getvalue()
