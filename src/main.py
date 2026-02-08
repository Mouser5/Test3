from game import Game


def interactive_loop(game: Game):
    """Интерактивный цикл для ручного тестирования."""
    while True:
        print("\n" + "=" * 50)
        game.print_state()

        hand = game.hands[game.current_player]
        print(f"\nИгрок {game.current_player}, ваша рука:")
        for i, card in enumerate(hand):
            print(f"  [{i}] {card.name:12} {card}")

        command = input("\nВвод (x y) для проверки, 'auto' для теста, 'q' выход: ").strip().lower()

        if command == 'q':
            break

        if command == 'auto':
            run_auto_test(game)
            continue

        try:
            x, y = map(int, command.split())

            # 1. Сначала проверяем, что сюда можно поставить
            available = game.check_possible_moves_at(x, y)

            # 2. Если есть варианты, предлагаем выбрать
            if available:
                choice = input("Номер карты для хода (или Enter для отмены): ")
                if choice.isdigit():
                    idx = int(choice)
                    # Простая проверка, есть ли такой индекс в доступных
                    if any(a[0] == idx for a in available):
                        game.play_turn(idx, x, y)
                    else:
                        print("Эту карту нельзя сюда поставить!")
        except ValueError:
            print("Ошибка ввода. Используйте формат: x y")


def run_auto_test(game: Game):
    print("\n--- Запуск авто-теста ---")
    # Тест 1: Неверный ход (Стена в Туннель)
    print("Попытка: Вертикальная карта справа от старта (ошибка)")
    v_idx = next((i for i, c in enumerate(game.hands[game.current_player]) if c.name == "Vertical"), -1)
    if v_idx != -1:
        game.play_turn(v_idx, 1, 0)

    # Тест 2: Верный ход
    print("Попытка: Горизонтальная карта справа от старта (успех)")
    h_idx = next((i for i, c in enumerate(game.hands[game.current_player]) if c.name == "Horizontal"), -1)
    if h_idx != -1:
        game.play_turn(h_idx, 1, 0)


if __name__ == "__main__":
    game = Game()
    interactive_loop(game)