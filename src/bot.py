# bot.py
import random
from typing import List, Tuple, Optional, Dict, Any
from cards import PathCard, ActionCard, ActionType, EquipmentType, LadderCard, DoorCard, GoldCard, StartCard
from game import Game, TurnResult


class BotPlayer:
    """
    Простой бот, который делает случайные допустимые ходы.
    """
    
    def __init__(self, player_id: int, game: Game):
        self.player_id = player_id
        self.game = game
        
        # Возможные направления для поиска соседних клеток
        self.directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    def make_move(self) -> Dict[str, Any]:
        """
        Основной метод, который бот вызывает для совершения хода.
        Возвращает словарь с параметрами хода для передачи в game.play_turn()
        """
        hand = self.game.hands[self.player_id]
        
        if not hand:
            # Если карт нет, сбрасываем случайные (хотя их и нет)
            return self._emergency_discard()
        
        # Проверяем, сломан ли инвентарь
        if self.game.broken_equipments[self.player_id]:
            # Если инвентарь сломан, пробуем починить
            return self._try_repair_or_discard()
        
        # Пробуем разные типы ходов в случайном порядке
        move_attempts = [
            self._try_play_path_card,
            self._try_play_action_card_on_board,
            self._try_play_action_card_on_player,
            self._try_discard
        ]
        
        random.shuffle(move_attempts)
        
        for attempt in move_attempts:
            move_data = attempt()
            if move_data:
                return move_data
        
        # Если ничего не получилось, просто сбрасываем карты
        return self._emergency_discard()
    
    def _try_play_path_card(self) -> Optional[Dict[str, Any]]:
        """Пытается случайно разместить карту туннеля на поле"""
        hand = self.game.hands[self.player_id]
        path_cards = [i for i, card in enumerate(hand) if isinstance(card, PathCard) 
                     and not isinstance(card, ActionCard)]
        
        if not path_cards:
            return None
        
        # Находим все пустые клетки рядом с существующими картами
        empty_positions = self._find_empty_adjacent_positions()
        
        if not empty_positions:
            return None
        
        # Пробуем разные комбинации карт и позиций
        random.shuffle(path_cards)
        random.shuffle(empty_positions)
        
        for card_idx in path_cards:
            card = hand[card_idx]
            
            for x, y in empty_positions:
                # Пробуем без поворота
                if self.game.board.is_move_valid(x, y, card, 
                                                self.game.start_positions[self.player_id], 
                                                self.player_id):
                    return {
                        'card_idx': card_idx,
                        'x': x,
                        'y': y,
                        'rotate_before_playing': False
                    }
                
                # Если карту можно повернуть, пробуем с поворотом
                rotated_card = card.get_rotated_copy()
                if self.game.board.is_move_valid(x, y, rotated_card,
                                                self.game.start_positions[self.player_id],
                                                self.player_id):
                    return {
                        'card_idx': card_idx,
                        'x': x,
                        'y': y,
                        'rotate_before_playing': True
                    }
        
        return None
    
    def _try_play_action_card_on_board(self) -> Optional[Dict[str, Any]]:
        """Пытается сыграть карту действия на поле (ключ или обвал)"""
        hand = self.game.hands[self.player_id]
        
        # Ищем карты действий для поля
        action_indices = []
        for i, card in enumerate(hand):
            if isinstance(card, ActionCard) and card.action_type in [ActionType.KEY, ActionType.ROCKFALL]:
                action_indices.append(i)
        
        if not action_indices:
            return None
        
        random.shuffle(action_indices)
        
        for card_idx in action_indices:
            card = hand[card_idx]
            
            # Находим все клетки с картами на поле
            board_positions = list(self.game.board.grid.keys())
            random.shuffle(board_positions)
            
            for x, y in board_positions:
                target_card = self.game.board.get_card(x, y)
                
                # Для ключа: ищем закрытые двери не своего цвета
                if card.action_type == ActionType.KEY:
                    if (isinstance(target_card, DoorCard) and 
                        target_card.is_locked and 
                        target_card.door_owner_id != self.player_id):
                        
                        if self.game.board.is_move_valid(x, y, card,
                                                        self.game.start_positions[self.player_id],
                                                        self.player_id):
                            return {
                                'card_idx': card_idx,
                                'x': x,
                                'y': y
                            }
                
                # Для обвала: нельзя уничтожать стартовые клетки и золото
                elif card.action_type == ActionType.ROCKFALL:
                    if not isinstance(target_card, (StartCard, GoldCard)):
                        if self.game.board.is_move_valid(x, y, card,
                                                        self.game.start_positions[self.player_id],
                                                        self.player_id):
                            return {
                                'card_idx': card_idx,
                                'x': x,
                                'y': y
                            }
        
        return None
    
    def _try_play_action_card_on_player(self) -> Optional[Dict[str, Any]]:
        """Пытается сыграть карту действия на игрока (поломка/починка)"""
        hand = self.game.hands[self.player_id]
        
        # Ищем карты поломки/починки
        action_indices = []
        for i, card in enumerate(hand):
            if isinstance(card, ActionCard) and card.action_type in [ActionType.SABOTAGE, ActionType.REPAIR]:
                action_indices.append(i)
        
        if not action_indices:
            return None
        
        # Определяем противника
        opponent_id = 1 - self.player_id
        
        random.shuffle(action_indices)
        
        for card_idx in action_indices:
            card = hand[card_idx]
            
            if card.action_type == ActionType.SABOTAGE:
                # Пытаемся сломать предмет у противника, если он еще не сломан
                eq = card.equipment_type
                if eq and eq not in self.game.broken_equipments[opponent_id]:
                    return {
                        'card_idx': card_idx,
                        'target_player': opponent_id
                    }
            
            elif card.action_type == ActionType.REPAIR:
                # Пытаемся починить свой сломанный предмет
                eq = card.equipment_type
                if eq and eq in self.game.broken_equipments[self.player_id]:
                    return {
                        'card_idx': card_idx,
                        'target_player': self.player_id
                    }
        
        return None
    
    def _try_repair_or_discard(self) -> Dict[str, Any]:
        """Когда инвентарь сломан: пробует починить или сбрасывает карты"""
        broken_eq = list(self.game.broken_equipments[self.player_id])
        
        if broken_eq:
            # Пробуем найти две карты для экстренной починки
            eq_to_repair = broken_eq[0]
            
            # Пытаемся найти карту ремонта в руке
            hand = self.game.hands[self.player_id]
            repair_cards = []
            other_cards = []
            
            for i, card in enumerate(hand):
                if (isinstance(card, ActionCard) and 
                    card.action_type == ActionType.REPAIR and 
                    card.equipment_type == eq_to_repair):
                    repair_cards.append(i)
                else:
                    other_cards.append(i)
            
            # Если есть карта ремонта, используем её
            if repair_cards:
                return {
                    'card_idx': repair_cards[0],
                    'target_player': self.player_id
                }
            
            # Иначе пробуем сбросить 2 карты для ремонта
            if len(other_cards) >= 2:
                return {
                    'action': 'discard_for_repair',
                    'card_indices': other_cards[:2],
                    'equip_type': eq_to_repair
                }
        
        # Если ничего не вышло, просто сбрасываем карты
        return self._emergency_discard()
    
    def _try_discard(self) -> Optional[Dict[str, Any]]:
        """Пытается сбросить 1-2 карты"""
        hand = self.game.hands[self.player_id]
        
        if len(hand) >= 1:
            num_to_discard = random.randint(1, min(2, len(hand)))
            indices = random.sample(range(len(hand)), num_to_discard)
            
            return {
                'action': 'discard',
                'card_indices': indices
            }
        
        return None
    
    def _emergency_discard(self) -> Dict[str, Any]:
        """Экстренный сброс, когда ничего другого не осталось"""
        hand = self.game.hands[self.player_id]
        
        if hand:
            num_to_discard = min(2, len(hand))
            indices = list(range(num_to_discard))
            
            return {
                'action': 'discard',
                'card_indices': indices
            }
        
        return {'action': 'pass'}
    
    def _find_empty_adjacent_positions(self) -> List[Tuple[int, int]]:
        """Находит все пустые клетки, соседние с существующими картами"""
        occupied = set(self.game.board.grid.keys())
        empty_adjacent = set()
        
        for x, y in occupied:
            for dx, dy in self.directions:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in occupied:
                    empty_adjacent.add((nx, ny))
        
        # Убираем стартовые позиции
        empty_adjacent.discard(self.game.start_positions[0])
        empty_adjacent.discard(self.game.start_positions[1])
        
        return list(empty_adjacent)


def create_bot_move(game: Game, player_id: int) -> Dict[str, Any]:
    """
    Удобная функция-обертка для создания хода бота
    """
    bot = BotPlayer(player_id, game)
    return bot.make_move()


def play_bot_turn(game: Game, player_id: int) -> TurnResult:
    """
    Выполняет ход бота и возвращает результат
    """
    move_data = create_bot_move(game, player_id)
    
    if move_data.get('action') == 'discard':
        return game.discard_cards(player_id, move_data['card_indices'])
    
    elif move_data.get('action') == 'discard_for_repair':
        return game.discard_two_to_repair(player_id, 
                                         move_data['card_indices'], 
                                         move_data['equip_type'])
    
    elif 'card_idx' in move_data:
        return game.play_turn(
            card_idx=move_data['card_idx'],
            x=move_data.get('x'),
            y=move_data.get('y'),
            target_player=move_data.get('target_player'),
            rotate_before_playing=move_data.get('rotate_before_playing', False)
        )
    
    # Если ничего не подошло, пропускаем ход (сбрасываем первую карту)
    if game.hands[player_id]:
        return game.discard_cards(player_id, [0])
    
    return TurnResult(False, "Бот не может сделать ход")