FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn fastapi pydantic requests redis

COPY src /app/src
COPY src/bot-container/bot_server.py /app/
COPY src/bot-container/bot_redis.py /app/

EXPOSE 8001

CMD ["python", "bot_server.py"]
