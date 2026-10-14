import os
import socket

import redis
from flask import Flask

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "db-service")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def get_redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        socket_connect_timeout=2,
        decode_responses=True,
    )


@app.route("/")
def index():
    try:
        hits = get_redis().incr("hits")
    except redis.exceptions.RedisError:
        return "Erreur : impossible de joindre Redis (db-service).\n", 503
    container_id = socket.gethostname()
    return (
        f"Hi tout le monde ! Cette page a été vue {hits} fois. "
        f"Je suis le conteneur {container_id}\n"
    )


@app.route("/health")
def health():
    return "ok\n", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)