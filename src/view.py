from cards import (
    GoldCardTemplate,
    DoorCardTemplate,
    LadderCardTemplate,
    ActionCardTemplate,
    ActionType,
    PathCardTemplate,
)
from state import MatchState, PlacedCard
from registry import REGISTRY
from board import BoardEngine


class ConsoleColor:
    BLUE, GREEN, YELLOW, RED, CYAN, RESET = (
        "\033[94m",
        "\033[92m",
        "\033[93m",
        "\033[91m",
        "\033[96m",
        "\033[0m",
    )


class ConsoleView:
    @staticmethod
    def get_color(owner_id: int) -> str:
        if owner_id == 0:
            return ConsoleColor.BLUE
        if owner_id == 1:
            return ConsoleColor.GREEN
        return ConsoleColor.RESET

    @staticmethod
    def render_placed_card(placed: PlacedCard) -> str:
        tpl = REGISTRY.get(placed.template_id)
        color = ConsoleView.get_color(placed.owner_id)

        if isinstance(tpl, GoldCardTemplate):
            if placed.is_revealed:
                return f"{color}${ConsoleColor.YELLOW}{tpl.gold_value}{color}${ConsoleColor.RESET}"
            return f"{color} ? {ConsoleColor.RESET}"

        if isinstance(tpl, DoorCardTemplate):
            if placed.is_locked:
                return f"{color}▐█▌{ConsoleColor.RESET}"
            return f"{color}▐ {ConsoleColor.RESET}▌{ConsoleColor.RESET}"

        if isinstance(tpl, LadderCardTemplate):
            return f"{color} # {ConsoleColor.RESET}"

        if isinstance(tpl, PathCardTemplate):
            mask = 0
            # Инвертируем направления для отрисовки, если карта повернута
            up = tpl.openings.down if placed.is_rotated_180 else tpl.openings.up
            down = tpl.openings.up if placed.is_rotated_180 else tpl.openings.down
            left = tpl.openings.right if placed.is_rotated_180 else tpl.openings.left
            right = tpl.openings.left if placed.is_rotated_180 else tpl.openings.right

            if up:
                mask += 8
            if down:
                mask += 4
            if left:
                mask += 2
            if right:
                mask += 1
            symbols = {
                0: " ? ",
                1: "  ╺",
                2: "╸  ",
                3: " ═ ",
                4: " ╻ ",
                5: " ┏ ",
                6: " ┓ ",
                7: " ┳ ",
                8: " ╹ ",
                9: " ┗ ",
                10: " ┛ ",
                11: " ┻ ",
                12: " ║ ",
                13: " ┣ ",
                14: " ┫ ",
                15: " ╬ ",
            }
            return f"{color}{symbols.get(mask, ' ? ')}{ConsoleColor.RESET}"
        return " . "

    @staticmethod
    def render_template_only(t_id: str) -> str:
        # Для отрисовки руки (карта еще не на поле)
        tpl = REGISTRY.get(t_id)
        if isinstance(tpl, ActionCardTemplate):
            if tpl.action_type == ActionType.KEY:
                return f"{ConsoleColor.CYAN} KEY {ConsoleColor.RESET}"
            if tpl.action_type == ActionType.ROCKFALL:
                return f"{ConsoleColor.RED} Х {ConsoleColor.RESET}"
            if tpl.action_type == ActionType.MAP:
                return f"{ConsoleColor.YELLOW} MAP {ConsoleColor.RESET}"
            if tpl.action_type == ActionType.SABOTAGE:
                return f"{ConsoleColor.RED}[-{tpl.equipment_type.value}-]{ConsoleColor.RESET}"
            if tpl.action_type == ActionType.REPAIR:
                return f"{ConsoleColor.GREEN}[+{tpl.equipment_type.value}+]{ConsoleColor.RESET}"
        # Для путей используем логику отрисовки PlacedCard без поворота
        return ConsoleView.render_placed_card(PlacedCard(template_id=t_id))

    @staticmethod
    def print_board(state: MatchState):
        print("\nПоле:")
        min_x, max_x, min_y, max_y = -3, 3, -10, 1

        # ⬇️ ИСПРАВЛЕНИЕ: k уже кортеж (x, y)
        for k in state.board.keys():
            x, y = k  # ⬇️ Просто распаковка кортежа
            min_x, max_x = min(min_x, x - 1), max(max_x, x + 1)
            min_y, max_y = min(min_y, y - 1), max(max_y, y + 1)

        header = "    "
        for x in range(min_x, max_x + 1):
            header += f"{x:^5}" if len(str(x)) == 1 else f"{x:^4} "
        print(header)
        print("    " + "_" * (len(header) - 4))

        for y in range(max_y, min_y - 1, -1):
            line = f"{y:2} |" if len(str(y)) <= 2 else f"{y:2}|"
            for x in range(min_x, max_x + 1):
                # ⬇️ ИСПРАВЛЕНИЕ: k теперь кортеж
                k = (x, y)
                placed = state.board.get(k)
                if placed:
                    line += f" {ConsoleView.render_placed_card(placed)} "
                else:
                    line += "  .  "
            print(line)

        print("\nСтатус игроков:")
        for p_id, p_state in state.players.items():
            color = ConsoleView.get_color(p_id)
            status = (
                f"{ConsoleColor.RED}СЛОМАНО: {', '.join([eq.value for eq in p_state.broken_equipments])}{ConsoleColor.RESET}"
                if p_state.broken_equipments
                else f"{ConsoleColor.GREEN}ОК{ConsoleColor.RESET}"
            )
            print(f"{color}Игрок {p_id}:{ConsoleColor.RESET} {status}")
        print("\n")

    @staticmethod
    def print_hand(state: MatchState):
        p_id = state.current_player_id
        color = ConsoleView.get_color(p_id)
        print(f"{color}ХОД ИГРОКА {p_id} {ConsoleColor.RESET}")
        print("Ваша рука:")
        for i, t_id in enumerate(state.players[p_id].hand):
            tpl = REGISTRY.get(t_id)
            print(f"  {i}: [{tpl.name}] {ConsoleView.render_template_only(t_id)}")

    @staticmethod
    def print_message(msg: str, is_error=False):
        color = ConsoleColor.RED if is_error else ConsoleColor.YELLOW
        print(f"{color}{msg}{ConsoleColor.RESET}")
