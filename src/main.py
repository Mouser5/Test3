from game import Game
from src.cards import ConsoleColor


def interactive_loop(game: Game):
    while True:
        print("\n" + "=" * 50)
        game.print_state()

        curr_p = game.current_player
        hand = game.hands[curr_p]

        print(f"{game.player_colors[curr_p]}\nХОД ИГРОКА {curr_p} {ConsoleColor.RESET} ")
        print("Ваша рука:")
        for i, c in enumerate(hand):
            print(f"  {i}: [{c.name}] {c}")

        print("\nВыберите действие:")
        print("1. Построить туннель")
        print("2. Использовать карту действия (Ключ)")
        print("3. Сбросить карты (1-2 шт)")
        print("4. Выход")

        choice = input("\nВаш выбор: ").strip().lower()

        if choice == '4': break

        # --- 1. ТУННЕЛЬ ---
        if choice == '1':
            try:
                coords = input("Введите (x y): ").split()
                x, y = int(coords[0]), int(coords[1])
                moves = game.get_possible_moves_at(x, y)

                # Фильтруем только туннели (не ключи)
                tunnel_moves = [m for m in moves if not hand[m[0]].is_key]

                if not tunnel_moves:
                    print("Нет подходящих туннелей для этой клетки.")
                    continue

                for i, (h_idx, card_obj, rot) in enumerate(tunnel_moves):
                    print(f"  {i + 1}: {card_obj.name} {'(ПОВЕРНУТ)' if rot else ''} {card_obj}")

                c_idx = int(input("Выберите вариант: ")) - 1
                h_idx, _, rot = tunnel_moves[c_idx]
                game.play_turn(h_idx, x, y, rotate_before_playing=rot)
            except Exception as e:
                print(f"Ошибка: {e}")

        # --- 2. ДЕЙСТВИЕ ---
        elif choice == '2':
            # Ищем ключи в руке
            actions = [(i, c) for i, c in enumerate(hand) if c.is_key or c.is_rockfall]
            if not actions:
                print("У вас нет карт действий!")
                continue

            for i, (h_idx, c) in enumerate(actions):
                print(f"  {i + 1}: {c.name}")

            try:
                k_choice = int(input("Выберите карту: ")) - 1
                h_idx = actions[k_choice][0]
                coords = input("Введите координаты (x y): ").split()
                x, y = int(coords[0]), int(coords[1])
                if game.play_action_card(h_idx, x, y):
                    print("Нельзя применить здесь!")
            except:
                print("Ошибка ввода.")

        # --- 3. СБРОС ---
        elif choice == '3':
            try:
                indices_str = input("Введите номера карт через пробел (напр. '0 2'): ").split()
                indices = [int(i) for i in indices_str]
                if 1 <= len(indices) <= 2:
                    game.discard_cards(curr_p, indices)
                    print(f"Карты {indices} сброшены. Вы добрали новые.")
                else:
                    print("Можно сбросить только 1 или 2 карты.")
            except:
                print("Неверные индексы.")


if __name__ == "__main__":
    g = Game()
    interactive_loop(g)