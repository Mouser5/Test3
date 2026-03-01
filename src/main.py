from game import Game
from view import ConsoleView, ConsoleColor
from cards import ActionCard, ActionType, EquipmentType, PathCard


def interactive_loop(game: Game, view: ConsoleView):
    while True:
        if game.is_game_over():
            view.print_message("\n" + "=" * 50)
            view.print_message("ИГРА ОКОНЧЕНА!")
            view.print_board(game)
            scores = game.calculate_scores()
            print(f"ИТОГОВЫЙ СЧЕТ: Игрок 0: {scores[0]}, Игрок 1: {scores[1]}")
            break

        view.print_message("\n" + "=" * 50)
        view.print_board(game)

        curr_p = game.current_player
        hand = game.hands[curr_p]

        view.print_hand(curr_p, hand)

        print("\nДействия:")
        print("1. Сыграть карту")
        print("2. Сбросить карты (1-2 шт)")
        print("3. Экстренная починка (сбросить 2 карты чтобы починить предмет)")
        print("4. Выход")

        choice = input("\nВыбор: ").strip()
        if choice == '4': break

        if choice == '1':
            try:
                c_idx = int(input("Введите номер карты из руки: "))-1
                card = hand[c_idx]

                if isinstance(card, PathCard) or (
                        isinstance(card, ActionCard) and card.action_type in [ActionType.KEY, ActionType.ROCKFALL]):
                    # Карта требует координат поля
                    coords = input("Введите координаты (x y): ").split()
                    x, y = int(coords[0]), int(coords[1])

                    rot = False
                    if isinstance(card, PathCard):
                        rot_input = input("Повернуть карту? (y/n): ").strip().lower()
                        rot = rot_input == 'y'

                    result = game.play_turn(c_idx, x=x, y=y, rotate_before_playing=rot)

                elif isinstance(card, ActionCard) and card.action_type in [ActionType.SABOTAGE, ActionType.REPAIR]:
                    # Карта играется на игрока
                    t_id = int(input("Укажите цель (номер игрока 0 или 1): "))
                    result = game.play_turn(c_idx, target_player=t_id)
                else:
                    continue

                if result.success:
                    view.print_message(result.message)
                    if result.revealed_gold: view.print_message(f"✨ ЗОЛОТО НАЙДЕНО: {result.revealed_gold} слитков! ✨")
                else:
                    view.print_message(result.message, is_error=True)

            except Exception as e:
                view.print_message(f"Ошибка ввода: {e}", is_error=True)

        elif choice == '2':
            try:
                indices = [int(i) for i in input("Номера карт через пробел: ").split()]
                res = game.discard_cards(curr_p, indices)
                if not res.success: view.print_message(res.message, is_error=True)
            except:
                view.print_message("Неверный ввод.", is_error=True)

        elif choice == '3':
            try:
                indices = [int(i) for i in input("Укажите 2 номера карт для сброса: ").split()]
                print("Какой предмет чиним? 1 - Лампа, 2 - Вагонетка, 3 - Кирка")
                eq_map = {'1': EquipmentType.LAMP, '2': EquipmentType.CART, '3': EquipmentType.PICKAXE}
                eq_choice = input("Выбор: ").strip()

                if eq_choice in eq_map:
                    res = game.discard_two_to_repair(curr_p, indices, eq_map[eq_choice])
                    if res.success:
                        view.print_message(res.message)
                    else:
                        view.print_message(res.message, is_error=True)
                else:
                    view.print_message("Неверный предмет.", is_error=True)
            except:
                view.print_message("Неверный ввод.", is_error=True)


if __name__ == "__main__":
    g = Game()
    v = ConsoleView()
    interactive_loop(g, v)