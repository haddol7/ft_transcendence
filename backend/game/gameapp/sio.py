from typing import Any
import socketio
import json


from gameapp.envs import FRONTEND_URL, GAME_URL


NAMESPACE = "/game"

UPDATE_BALL_EVENT = "updateBall"
UPDATE_SCORE_EVENT = "updateScore"
UPDATE_PADDLE_EVENT = "updatePaddle"
GAME_OVER_EVENT = "gameOver"
UPDATE_BALL_EVENT = "updateBall"
RESET_POSITIONS_EVENT = "resetPositions"

sio = socketio.Server(
    cors_allowed_origins=[
        "https://localhost",
        f"https://{FRONTEND_URL}",
        GAME_URL,
    ]
)


def sio_emit(event: str, data: dict[str, Any], to: str):
    print(f"sio_emit: event={event}, data={json.dumps(data)}, to={to}")
    sio.emit(event, data, to=to, namespace=NAMESPACE)


def sio_session(sid: str):
    return sio.session(sid, namespace=NAMESPACE)


def sio_disconnect(sid: str):
    print(f"sid={sid} disconnect")
    sio.disconnect(sid, namespace=NAMESPACE)


def sio_enter_room(sid: str, room_name: str):
    print(f"sid={sid} enters room to {room_name}")
    sio.enter_room(sid, room_name, namespace=NAMESPACE)
