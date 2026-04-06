import os
import pickle
import uuid
from typing import Optional, Dict, Any, List
import redis


class GameRedisManager:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=False)
        return self._client

    def _state_key(self, game_id: str) -> str:
        return f"game:{game_id}:state"

    def _channel(self, game_id: str) -> str:
        return f"game:{game_id}"

    def _player_channel(self, game_id: str, user_id: int) -> str:
        return f"game:{game_id}:player:{user_id}"

    def create_game(self, game_state: Dict[str, Any]) -> str:
        game_id = str(uuid.uuid4())[:8]
        key = self._state_key(game_id)
        self.client.set(key, pickle.dumps(game_state))
        return game_id

    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        key = self._state_key(game_id)
        data = self.client.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    def update_game(self, game_id: str, game_state: Dict[str, Any]) -> bool:
        key = self._state_key(game_id)
        return self.client.set(key, pickle.dumps(game_state))

    def delete_game(self, game_id: str) -> bool:
        key = self._state_key(game_id)
        channel = self._channel(game_id)
        self.client.delete(key)
        self.client.publish(channel, pickle.dumps({"type": "game_ended"}))
        return True

    def subscribe_player(self, game_id: str, user_id: int) -> str:
        channel = self._player_channel(game_id, user_id)
        return channel

    def unsubscribe_player(self, game_id: str, user_id: int) -> bool:
        channel = self._player_channel(game_id, user_id)
        return True

    def publish_to_player(
        self, game_id: str, user_id: int, message: Dict[str, Any]
    ) -> int:
        channel = self._player_channel(game_id, user_id)
        return self.client.publish(channel, pickle.dumps(message))

    def publish_to_game(self, game_id: str, message: Dict[str, Any]) -> int:
        channel = self._channel(game_id)
        return self.client.publish(channel, pickle.dumps(message))

    def get_all_games(self) -> List[str]:
        pattern = "game:*:state"
        keys = self.client.keys(pattern)
        return [k.decode().split(":")[1] for k in keys]

    def game_exists(self, game_id: str) -> bool:
        key = self._state_key(game_id)
        return self.client.exists(key) > 0


game_redis = GameRedisManager()
