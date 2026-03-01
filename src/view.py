from typing import List
from cards import Card, PathCard, StartCard, GoldCard, DoorCard, LadderCard, ActionCard, ActionType
from game import Game


class ConsoleColor:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'


class ConsoleView:
    @staticmethod
    def get_color_for_owner(owner_id: int) -> str:
        if owner_id == 0: return ConsoleColor.BLUE
        if owner_id == 1: return ConsoleColor.GREEN
        return ConsoleColor.RESET

    @staticmethod
    def render_card(card: Card) -> str:
        color = ConsoleView.get_color_for_owner(card.owner_id)

        if isinstance(card, GoldCard):
            if card.is_revealed:
                return f"{color}${ConsoleColor.YELLOW}{card.gold_value}{color}${ConsoleColor.RESET}"
            return f"{color} ? {ConsoleColor.RESET}"

        if isinstance(card, ActionCard):
            if card.action_type == ActionType.KEY: return f"{ConsoleColor.CYAN} KEY {ConsoleColor.RESET}"
            if card.action_type == ActionType.ROCKFALL: return f"{ConsoleColor.RED} Х {ConsoleColor.RESET}"

        if isinstance(card, DoorCard):
            if card.is_locked:
                return f"{color}▐█▌{ConsoleColor.RESET}"
            else:
                return f"{color}▐ {ConsoleColor.RESET}▌{ConsoleColor.RESET}"

        if isinstance(card, LadderCard):
            return f"{color} # {ConsoleColor.RESET}"

        if isinstance(card, PathCard):
            mask = 0
            if card.openings.up: mask += 8
            if card.openings.down: mask += 4
            if card.openings.left: mask += 2
            if card.openings.right: mask += 1

            symbols = {
                0: " ? ", 1: "  ╺", 2: "╸  ", 3: " ═ ",
                4: " ╻ ", 5: " ┏ ", 6: " ┓ ", 7: " ┳ ",
                8: " ╹ ", 9: " ┗ ", 10: " ┛ ", 11: " ┻ ",
                12: " ║ ", 13: " ┣ ", 14: " ┫ ", 15: " ╬ ",
            }
            symbol = symbols.get(mask, " ? ")
            return f"{color}{symbol}{ConsoleColor.RESET}"

        return " . "

    @staticmethod
    def print_board(game: Game):
        print("\nПоле:")
        min_x, max_x = -3, 3
        min_y, max_y = -10, 1

        keys = game.board.grid.keys()
        if keys:
            xs, ys = [k[0] for k in keys], [k[1] for k in keys]
            min_x, max_x = min(min_x, min(xs) - 1), max(max_x, max(xs) + 1)
            min_y, max_y = min(min_y, min(ys) - 1), max(max_y, max(ys) + 1)

        header = "    "
        for x in range(min_x, max_x + 1):
            header += f"{x:^5}" if len(str(x)) == 1 else f"{x:^4} "
        print(header)
        print("    " + "_" * (len(header) - 4))

        for y in range(max_y, min_y - 1, -1):
            line = f"{y:2} |" if len(str(y)) <= 2 else f"{y:2}|"
            for x in range(min_x, max_x + 1):
                card = game.board.get_card(x, y)
                if card:
                    line += f" {ConsoleView.render_card(card)} "
                else:
                    line += "  .  "
            print(line)
        print("\n")

    @staticmethod
    def print_hand(player_id: int, hand: List[Card]):
        color = ConsoleView.get_color_for_owner(player_id)
        print(f"{color}\nХОД ИГРОКА {player_id} {ConsoleColor.RESET} ")
        print("Ваша рука:")
        for i, c in enumerate(hand):
            print(f"  {i+1}: [{c.name}] {ConsoleView.render_card(c)}")

    @staticmethod
    def print_message(msg: str, is_error=False):
        color = ConsoleColor.RED if is_error else ConsoleColor.YELLOW
        print(f"{color}{msg}{ConsoleColor.RESET}")