from game import Game
from view import ConsoleView
from cards import ActionCardTemplate, ActionType, EquipmentType, PathCardTemplate
from actions import (
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
)
from registry import REGISTRY


def interactive_loop(game: Game, view: ConsoleView):
    while True:
        if game.is_game_over():
            view.print_message("\n" + "=" * 50)
            view.print_message("ИГРА ОКОНЧЕНА!")
            view.print_board(game.state)
            scores = game.calculate_scores()
            print(f"ИТОГОВЫЙ СЧЕТ: Игрок 0: {scores[0]}, Игрок 1: {scores[1]}")
            break

        view.print_message("\n" + "=" * 50)
        view.print_board(game.state)
        view.print_hand(game.state)

        print("\nДействия:")
        print("1. Сыграть карту")
        print("2. Сбросить карты (1-2 шт)")
        print("3. Экстренная починка (сбросить 2 карты)")
        print("4. Выход")

        choice = input("\nВыбор: ").strip()
        if choice == "4":
            break

        if choice == "1":
            try:
                c_idx = int(input("Введите номер карты из руки: "))
                p_id = game.state.current_player_id
                t_id = game.state.players[p_id].hand[c_idx]
                tpl = REGISTRY.get(t_id)

                action = None
                if isinstance(tpl, PathCardTemplate) or (
                    isinstance(tpl, ActionCardTemplate)
                    and tpl.action_type
                    in [ActionType.KEY, ActionType.ROCKFALL, ActionType.MAP]
                ):
                    coords = input("Введите координаты поля (x y): ").split()
                    x, y = int(coords[0]), int(coords[1])
                    rot = False
                    if isinstance(tpl, PathCardTemplate):
                        rot = input("Повернуть карту? (y/n): ").strip().lower() == "y"

                    if isinstance(tpl, PathCardTemplate):
                        action = ActionBuild(
                            template_id=t_id, x=x, y=y, is_rotated_180=rot
                        )
                    else:
                        action = ActionPlayBoardUtility(template_id=t_id, x=x, y=y)

                elif isinstance(tpl, ActionCardTemplate) and tpl.action_type in [
                    ActionType.SABOTAGE,
                    ActionType.REPAIR,
                ]:
                    t_target = int(input("Укажите цель (номер игрока 0 или 1): "))
                    action = ActionPlayPlayerUtility(
                        template_id=t_id, target_player_id=t_target
                    )
                else:
                    continue

                success, msg, rev_gold = game.step(action)
                if success:
                    view.print_message(msg)
                    if rev_gold:
                        view.print_message(f"✨ ЗОЛОТО НАЙДЕНО: {rev_gold} слитков! ✨")
                else:
                    view.print_message(msg, is_error=True)

            except Exception as e:
                view.print_message(f"Ошибка: {e}", is_error=True)

        elif choice == "2":
            try:
                indices = [int(i) for i in input("Номера карт через пробел: ").split()]
                p_id = game.state.current_player_id
                templates = [game.state.players[p_id].hand[i] for i in indices]

                action = ActionDiscard(templates=templates)
                success, msg, _ = game.step(action)
                if not success:
                    view.print_message(msg, is_error=True)
            except Exception as e:
                view.print_message(f"Ошибка ввода: {e}", is_error=True)

        elif choice == "3":
            try:
                indices = [int(i) for i in input("Укажите 2 номера карт: ").split()]
                print("Какой предмет чиним? 1 - Лампа, 2 - Вагонетка, 3 - Кирка")
                eq_map = {
                    "1": EquipmentType.LAMP,
                    "2": EquipmentType.CART,
                    "3": EquipmentType.PICKAXE,
                }
                eq_choice = input("Выбор: ").strip()

                if eq_choice in eq_map:
                    p_id = game.state.current_player_id
                    templates = [game.state.players[p_id].hand[i] for i in indices]

                    action = ActionDiscard(
                        templates=templates, repair_equipment=eq_map[eq_choice]
                    )
                    success, msg, _ = game.step(action)
                    if success:
                        view.print_message(msg)
                    else:
                        view.print_message(msg, is_error=True)
            except Exception as e:
                view.print_message(f"Ошибка ввода: {e}", is_error=True)


if __name__ == "__main__":
    g = Game()
    v = ConsoleView()
    interactive_loop(g, v)
