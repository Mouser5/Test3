FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn fastapi pydantic requests

COPY bot_server.py /app/bot_server.py

EXPOSE 8001

CMD ["python", "bot_server.py"]
