import docker
import uuid
import time
from typing import Optional, Dict
import requests


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.game_api_url = "http://game-api:8000"
        self.redis_url = "redis://redis:6379/0"

    def start_game_container(
        self,
        bot_code: str,
        user_id: int,
        game_id: str,
        redis_channel: str,
    ) -> Dict[str, str]:
        container_id = f"game-{game_id}-{uuid.uuid4().hex[:8]}"

        try:
            container = self.client.containers.run(
                "gnomes-bot:latest",
                name=container_id,
                detach=True,
                environment={
                    "GAME_API_URL": self.game_api_url,
                    "GAME_ID": game_id,
                    "REDIS_URL": self.redis_url,
                    "USER_CHANNEL": redis_channel,
                    "USER_ID": str(user_id),
                },
                ports={"8001/tcp": None},
                remove=False,
            )

            time.sleep(2)

            container.reload()
            port = container.ports.get("8001/tcp", [{}])[0].get("HostPort", None)

            if not port:
                container.stop()
                container.remove()
                return {"error": "Failed to get port"}

            base_url = f"http://localhost:{port}"

            try:
                resp = requests.post(
                    f"{base_url}/init",
                    json={"code": bot_code, "player_id": 0, "game_id": game_id},
                    timeout=10,
                )
                if resp.status_code != 200:
                    container.stop()
                    container.remove()
                    return {"error": f"Init failed: {resp.text}"}
            except Exception as e:
                container.stop()
                container.remove()
                return {"error": f"Connection failed: {e}"}

            return {
                "container_id": container_id,
                "url": base_url,
                "port": port,
                "game_id": game_id,
            }

        except docker.errors.ImageNotFound:
            return {
                "error": "Image not found. Build with: docker build -t gnomes-bot ./src/bot-container"
            }
        except Exception as e:
            return {"error": str(e)}

    def start_bot_container(self, bot_code: str, player_id: int = 0) -> Dict[str, str]:
        container_id = f"bot-{uuid.uuid4().hex[:8]}"

        try:
            container = self.client.containers.run(
                "gnomes-bot:latest",
                name=container_id,
                detach=True,
                environment={
                    "GAME_API_URL": self.game_api_url,
                },
                ports={"8001/tcp": None},
                remove=False,
            )

            time.sleep(2)

            container.reload()
            port = container.ports.get("8001/tcp", [{}])[0].get("HostPort", None)

            if not port:
                container.stop()
                container.remove()
                return {"error": "Failed to get port"}

            base_url = f"http://localhost:{port}"

            try:
                resp = requests.post(
                    f"{base_url}/init",
                    json={"code": bot_code, "player_id": player_id},
                    timeout=10,
                )
                if resp.status_code != 200:
                    container.stop()
                    container.remove()
                    return {"error": f"Init failed: {resp.text}"}
            except Exception as e:
                container.stop()
                container.remove()
                return {"error": f"Connection failed: {e}"}

            return {
                "container_id": container_id,
                "url": base_url,
                "port": port,
            }

        except docker.errors.ImageNotFound:
            return {
                "error": "Image not found. Build with: docker build -t gnomes-bot ./src/bot-container"
            }
        except Exception as e:
            return {"error": str(e)}

    def stop_game_container(self, container_id: str) -> bool:
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            return True
        except Exception:
            return False

    def stop_bot_container(self, container_id: str) -> bool:
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            return True
        except Exception:
            return False

    def get_container_status(self, container_id: str) -> Optional[str]:
        try:
            container = self.client.containers.get(container_id)
            return container.status
        except Exception:
            return None

    def cleanup_all_bots(self) -> int:
        count = 0
        try:
            for container in self.client.containers.list(filters={"name": "bot-"}):
                container.stop()
                container.remove()
                count += 1
        except Exception:
            pass
        return count

    def cleanup_all_games(self) -> int:
        count = 0
        try:
            for container in self.client.containers.list(filters={"name": "game-"}):
                container.stop()
                container.remove()
                count += 1
        except Exception:
            pass
        return count


docker_manager = DockerManager()
