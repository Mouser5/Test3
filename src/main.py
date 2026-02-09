from game import Game


def interactive_loop(game: Game):
    while True:
        print("\n" + "=" * 50)
        game.print_state()

        hand = game.hands[game.current_player]
        print(f"\nРука Игрока {game.current_player}:")
        hand_display = " | ".join([f"{i}: {c.name} {c}" for i, c in enumerate(hand)])
        print(hand_display)

        command = input("\nВведите координаты (x y) для хода или 'q' для выхода: ").strip().lower()

        if command == 'q':
            break

        try:
            x, y = map(int, command.split())

            moves = game.get_possible_moves_at(x, y)

            if not moves:
                print("Нет подходящих карт для этой клетки.")
                continue

            print(f"\nДоступные варианты хода в ({x}, {y}):")
            for i, (hand_idx, card_obj, needs_rotation) in enumerate(moves):
                rot_text = " (ПОВЕРНУТЬ)" if needs_rotation else ""
                print(f"  Вариант {i+1}: Карта №{hand_idx} [{card_obj.name}]{rot_text} -> {card_obj}")

            choice = input("Выберите номер ВАРИАНТА (не карты): ")
            if choice.isdigit():
                choice_idx = int(choice)
                if 0 <= choice_idx < len(moves):
                    hand_idx, _, needs_rotation = moves[choice_idx-1]

                    game.play_turn(hand_idx, x, y, rotate_before_playing=needs_rotation)
                else:
                    print("Неверный номер варианта.")

        except ValueError:
            print("Ошибка ввода. Формат: x y")


if __name__ == "__main__":
    game = Game()
    interactive_loop(game)