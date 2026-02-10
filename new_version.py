from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import random
from enum import Enum

# Цвета ANSI
BLUE   = "\033[94m"
GREEN  = "\033[92m"
BROWN  = "\033[38;5;94m"   # коричневый для знака ?
YELLOW = "\033[93m"        # для золота, если захочешь выделить
RESET  = "\033[0m"


class PlayerColor(Enum):
    BLUE = "B"
    GREEN = "G"


class Direction(Enum):
    UP    = ( 0,  1)
    DOWN  = ( 0, -1)
    LEFT  = (-1,  0)
    RIGHT = ( 1,  0)


@dataclass
class CardOpenings:
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

    def get_opening(self, dir: Direction) -> bool:
        return getattr(self, dir.name.lower())


@dataclass
class TunnelCard:
    name: str
    openings: CardOpenings
    owner: Optional[PlayerColor] = None
    is_door: Optional[PlayerColor] = None
    has_troll: bool = False
    gold: int = 0

    def __str__(self):
        mask = 0
        if self.openings.up:    mask += 8
        if self.openings.down:  mask += 4
        if self.openings.left:  mask += 2
        if self.openings.right: mask += 1

        symbols = {
            0: "?", 1: "╺", 2: "╸", 3: "═", 4: "╻",
            5: "┏", 6: "┓", 7: "┳", 8: "╹", 9: "┗",
            10: "┛", 11: "┻", 12: "║", 13: "┣", 14: "┫", 15: "╬",
        }
        base = symbols.get(mask, "?")

        # Если это закрытая цель
        if self.name.startswith("Goal") and mask == 0:
            return f"{BROWN}?{RESET}"

        # Определяем цвет игрока для самого символа туннеля
        color = ""
        if self.owner == PlayerColor.BLUE:
            color = BLUE
        elif self.owner == PlayerColor.GREEN:
            color = GREEN

        # Формируем итоговую строку: Цвет + Символ + Спец-значки
        char = f"{color}{base}{RESET}"

        # Добавляем значок двери или тролля рядом, если они есть
        if self.is_door:
            char = f"{char}{self.is_door.value}"
        if self.has_troll:
            char = f"{char}T"
        if self.gold > 0:
            char = f"{char}{YELLOW}${RESET}"

        return char


class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], TunnelCard] = {}

    def place_card(self, x: int, y: int, card: TunnelCard):
        self.grid[(x, y)] = card

    def get_card(self, x: int, y: int) -> Optional[TunnelCard]:
        return self.grid.get((x, y))

    # Переносим логику "противоположного направления" в обычный метод
    def _get_opposite(self, d: Direction) -> Direction:
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        return opposites[d]

    def is_connected_to_start(self, x: int, y: int, player: PlayerColor) -> bool:
        queue = [(x, y)]
        visited = {(x, y)}  # СРАЗУ помечаем начальную точку

        while queue:
            cx, cy = queue.pop(0)
            card = self.get_card(cx, cy)
            if not card: continue

            # Если дошли до своего старта - успех
            if card.name.startswith("Start") and card.owner == player:
                return True

            for d in Direction:
                # Если у текущей карты в этом направлении дырка
                if card.openings.get_opening(d):
                    dx, dy = d.value
                    nx, ny = cx + dx, cy + dy

                    if (nx, ny) not in visited:
                        ncard = self.get_card(nx, ny)
                        if ncard:
                            # Если у соседа есть ответная дырка
                            if ncard.openings.get_opening(self._get_opposite(d)):
                                visited.add((nx, ny))  # ПОМЕЧАЕМ ТУТ
                                queue.append((nx, ny))
        return False

    def is_move_valid(self, x: int, y: int, new_card: TunnelCard, player: PlayerColor) -> bool:
        if (x, y) in self.grid:
            return False

        has_neighbor = False
        for d in Direction:
            dx, dy = d.value
            nx, ny = x + dx, y + dy
            neigh = self.get_card(nx, ny)

            if neigh:
                has_neighbor = True
                my_open = new_card.openings.get_opening(d)

                # НОВОЕ: Если сосед - это закрытая цель, мы не проверяем стыковку туннелей,
                # так как цель "проявляется" только при контакте.
                if neigh.name.startswith("Goal") and sum(
                        [neigh.openings.up, neigh.openings.down, neigh.openings.left, neigh.openings.right]) == 0:
                    continue  # Просто разрешаем приставить любую карту к закрытой цели

                n_open = neigh.openings.get_opening(self._get_opposite(d))
                if my_open != n_open:
                    print(
                        f"(!) Конфликт: на {d.name} у тебя {'путь' if my_open else 'стена'}, а у соседа {'путь' if n_open else 'стена'}")
                    return False

                if neigh.is_door and my_open and neigh.is_door != player:
                    return False

        if not has_neighbor:
            return False

        self.grid[(x, y)] = new_card
        connected = self.is_connected_to_start(x, y, player)
        del self.grid[(x, y)]
        return connected

class Game:
    def __init__(self):
        self.board = GameBoard()
        self.current_player = PlayerColor.BLUE
        self.scores = {PlayerColor.BLUE: 0, PlayerColor.GREEN: 0}
        self.deck: List[TunnelCard] = []
        self.hands: Dict[PlayerColor, List[TunnelCard]] = {PlayerColor.BLUE: [], PlayerColor.GREEN: []}

        self._setup_board()
        self._create_deck()
        self._deal_cards()

    def _setup_board(self):
        start_b = TunnelCard("Start Blue", CardOpenings(True,True,True,True), owner=PlayerColor.BLUE)
        start_g = TunnelCard("Start Green", CardOpenings(True,True,True,True), owner=PlayerColor.GREEN)
        self.board.place_card(-4, 0, start_b)
        self.board.place_card( 4, 0, start_g)

        goal_data = [
            (-5, 3, None),
            (-3, 2, None),
            (-1, 1, PlayerColor.BLUE),
            ( 1, 0, None),
            ( 3, 1, None),
            ( 5, 2, PlayerColor.GREEN),
        ]
        for x, gold, door in goal_data:
            card = TunnelCard(f"Goal ${gold}", CardOpenings(False,False,False,False))
            card.gold = gold
            card.is_door = door
            self.board.place_card(x, -3, card)

    def _create_deck(self):
        types = [
            ("Vert",   CardOpenings(True, True, False, False), 10),
            ("Horiz",  CardOpenings(False, False, True, True), 10),
            ("L┗",     CardOpenings(True, False, True, False), 6),
            ("L┛",     CardOpenings(True, False, False, True), 6),
            ("L┏",     CardOpenings(False, True, True, False), 6),
            ("L┓",     CardOpenings(False, True, False, True), 6),
            ("Cross",  CardOpenings(True, True, True, True), 6),
        ]
        for name, op, cnt in types:
            for _ in range(cnt):
                self.deck.append(TunnelCard(name, op))
        random.shuffle(self.deck)

    def _deal_cards(self):
        for p in [PlayerColor.BLUE, PlayerColor.GREEN]:
            for _ in range(6):
                if self.deck:
                    self.hands[p].append(self.deck.pop())

    def show_hand(self):
        p = self.current_player
        print(f"\nРука {p.value} ({'Синий' if p==PlayerColor.BLUE else 'Зелёный'}):")
        for i, card in enumerate(self.hands[p]):
            print(f"  {i:2d}  {str(card):<8}  {card.name}")

    def play_tunnel(self, card_idx: int, x: int, y: int):
        hand = self.hands[self.current_player]
        if not (0 <= card_idx < len(hand)):
            print("Нет такой карты в руке.")
            return

        card = hand[card_idx]

        if self.board.is_move_valid(x, y, card, self.current_player):
            # 1. Ставим карту
            card.owner = self.current_player
            self.board.place_card(x, y, card)
            print(f"→ Положили карту на ({x}, {y})")

            # 2. Проверка открытия целей
            for d in Direction:
                dx, dy = d.value
                nx, ny = x + dx, y + dy
                neighbor = self.board.get_card(nx, ny)

                if neighbor and neighbor.name.startswith("Goal"):
                    # Проверяем, смотрит ли туннель нашей карты на цель
                    if card.openings.get_opening(d):
                        # Если цель еще не открыта (у неё все выходы False)
                        if not any([neighbor.openings.up, neighbor.openings.down,
                                    neighbor.openings.left, neighbor.openings.right]):

                            print(f"{YELLOW}*** ОТКРЫТА ЦЕЛЬ НА ({nx}, {ny})! ***{RESET}")
                            neighbor.openings = CardOpenings(True, True, True, True)

                            if neighbor.gold > 0:
                                print(f"{YELLOW}Вы нашли {neighbor.gold} самородка(ов)!{RESET}")
                                self.scores[self.current_player] += neighbor.gold
                            else:
                                print("Здесь ничего нет, кроме туннеля.")

            # 3. Обновляем руку
            hand.pop(card_idx)
            if self.deck:
                hand.append(self.deck.pop())

            # 4. Передаем ход
            self._next_turn()
        else:
            print("Нельзя поставить сюда.")

    def _next_turn(self):
        self.current_player = PlayerColor.GREEN if self.current_player == PlayerColor.BLUE else PlayerColor.BLUE
        print(f"\nХодит: {self.current_player.value}")

    def _next_turn(self):
        self.current_player = PlayerColor.GREEN if self.current_player == PlayerColor.BLUE else PlayerColor.BLUE
        print(f"\nХодит: {self.current_player.value}")

    def print_board(self):
        if not self.board.grid:
            print("Поле пустое")
            return

        # Находим границы поля
        xs = [p[0] for p in self.board.grid.keys()]
        ys = [p[1] for p in self.board.grid.keys()]

        min_x = min(xs) - 1
        max_x = max(xs) + 1
        min_y = min(ys) - 1
        max_y = max(ys) + 1

        # Вспомогательная функция для подсчета ВИДИМЫХ символов (без ANSI кодов)
        import re
        def visible_len(s):
            return len(re.sub(r'\033\[[0-9;]*m', '', s))

        # Функция для правильного центрирования текста с ANSI кодами
        def center_ansi(s, width):
            v_len = visible_len(s)
            padding = width - v_len
            if padding <= 0: return s
            left = padding // 2
            right = padding - left
            return " " * left + s + " " * right

        CELL_WIDTH = 7  # Увеличил ширину для комфортного чтения
        print("\nПоле:")

        # 1. Заголовок координат X
        header = "      "
        for x in range(min_x, max_x + 1):
            header += f"{x:^{CELL_WIDTH}}"
        print(header)

        # 2. Разделитель
        print("      " + "─" * ((max_x - min_x + 1) * CELL_WIDTH))

        # 3. Отрисовка строк
        for y in range(max_y, min_y - 1, -1):
            # Номер строки Y
            line = f"{y:>4} │"

            for x in range(min_x, max_x + 1):
                card = self.board.get_card(x, y)
                if card:
                    # Получаем строковое представление карты
                    s = str(card).strip()

                    # Если это цель в скобках [?], убираем скобки для красоты внутри ячейки
                    if s.startswith('[') and s.endswith(']'):
                        s = s[1:-1].strip()

                    # Центрируем с учетом невидимых символов
                    content = center_ansi(s, CELL_WIDTH - 2)
                    cell = f"[{content}]"
                else:
                    # Пустая клетка
                    content = center_ansi(".", CELL_WIDTH - 2)
                    cell = f" {content} "

                line += cell

            print(line)

        print("      " + "─" * ((max_x - min_x + 1) * CELL_WIDTH))
        print()


# ── Консольный игровой цикл ────────────────────────────────────────
def play_game():
    g = Game()
    print("Добро пожаловать в упрощённую «Гномы-вредители: Дуэль»")
    print("Команды:")
    print("  b          — показать поле")
    print("  h          — показать руку текущего игрока")
    print("  p idx x y  — сыграть карту №idx на координаты x y")
    print("  q          — выход\n")

    while True:
        cmd = input("> ").strip().lower().split()

        if not cmd:
            continue

        if cmd[0] == "q":
            print("Игра завершена.")
            break

        elif cmd[0] == "b":
            g.print_board()

        elif cmd[0] == "h":
            g.show_hand()

        elif cmd[0] == "p" and len(cmd) == 4:
            try:
                idx = int(cmd[1])
                x = int(cmd[2])
                y = int(cmd[3])
                g.play_tunnel(idx, x, y)
                g.print_board()
                g.show_hand()
            except ValueError:
                print("Неверный формат. Пример: p 0 -3 -1")

        else:
            print("Неизвестная команда. Попробуйте b, h, p idx x y, q")


if __name__ == "__main__":
    play_game()