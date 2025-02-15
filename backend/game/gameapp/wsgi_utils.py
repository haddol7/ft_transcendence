from typing import List, Tuple, Any
import requests
from django.db import transaction
from django.db.models import Min
from socketio.exceptions import ConnectionRefusedError

from exceptions.CustomException import InternalException
from gameapp.envs import GAMEAI_URL, JWT_URL
from gameapp.sio import sio_session
from gameapp.models import (
    TempMatch,
    TempMatchRoom,
    TempMatchRoomUser,
    TempMatchUser,
)
from gameapp.match_objects import Match, MatchUser, match_dict, matchuser
from gameapp.utils import get_int, get_str, generate_secret


def make_rooms(room_name: str, user_id: List[int]):
    with transaction.atomic():
        temp_match_room = TempMatchRoom.objects.create(room_name=room_name)

        temp_match_room_users: list[TempMatchRoomUser] = []
        for id in user_id:
            temp_match_user = TempMatchRoomUser.objects.create(
                user_id=id, temp_match_room_id=temp_match_room.id
            )
            temp_match_room_users.append(temp_match_user)

        user_len = len(user_id)

        prev_match = [
            TempMatch.objects.create(
                match_room_id=temp_match_room.id, round=2, winner_match=None
            )
        ]

        for round in [4, 8, 16]:
            if round > user_len:
                break

            match_len = round // 2
            cur_match = []

            for m in range(match_len):
                cur_match.append(
                    TempMatch.objects.create(
                        match_room_id=temp_match_room.id,
                        round=round,
                        winner_match_id=prev_match[m // 2].id,
                    )
                )

            prev_match = cur_match

        temp_match_users: list[TempMatchUser] = []
        for idx, match in enumerate(prev_match):
            temp_match_users.append(
                TempMatchUser.objects.create(
                    user_id=user_id[idx * 2],
                    temp_match_id=match.id,
                )
            )
            temp_match_users.append(
                TempMatchUser.objects.create(
                    user_id=user_id[idx * 2 + 1],
                    temp_match_id=match.id,
                )
            )

        init_matches(temp_match_users)


def make_airoom(user_id: int):
    room_name = generate_secret()
    with transaction.atomic():
        temp_match_room = TempMatchRoom.objects.create(room_name=room_name)
        temp_match_room_user = TempMatchRoomUser.objects.create(
            user_id=user_id, temp_match_room_id=temp_match_room.id
        )

        temp_match = TempMatch.objects.create(
            match_room_id=temp_match_room.id,
            round=2,
            winner_match=None,
            is_with_ai=True,
        )

        temp_match_user = TempMatchUser.objects.create(
            user_id=user_id, temp_match_id=temp_match.id
        )


def _get_from_sess(sid: str) -> Tuple[int, str]:
    with sio_session(sid) as sess:
        user_id: int = sess["user_id"]
        user_name: str = sess["user_name"]

    return user_id, user_name


def clear_match_dict():
    match_dict.clear()


def _get_match_id_from_jwt(jwt) -> int:
    res = requests.post(f"{JWT_URL}/jwt/check/ai", json={"jwt": jwt})
    if not res.ok:
        raise ConnectionRefusedError(res.content)

    json = res.json()
    return json["match_id"]


def _get_user_id_from_jwt(jwt) -> int:
    res = requests.post(f"{JWT_URL}/jwt/check", json={"jwt": jwt, "skip_2fa": False})

    if not res.ok:
        raise ConnectionRefusedError(res.content)

    json = res.json()
    return json["user_id"]


def on_connect(sid, auth):
    print(f"connected sid={sid}")

    # TODO: auth with JWT
    if "ai" in auth:
        jwt = get_str(auth, "jwt")
        match_id = _get_match_id_from_jwt(jwt)
        print(f"AI joined with match_id={match_id}")
        join_match_ai(sid, match_id)
        return
    elif "jwt" in auth:
        jwt = get_str(auth, "jwt")
        user_id = _get_user_id_from_jwt(jwt)
        # TODO: Fix username
        user_name = str(user_id)
    else:
        user_id = int(auth["user_id"])
        user_name = auth["user_name"]

    with sio_session(sid) as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name

    room_user = get_room_user_or_none(user_id)
    if room_user is None or room_user.is_online:
        raise ConnectionRefusedError("temp match room user none or online")
    room_user.is_online = True
    room_user.save()
    print(room_user)

    # room_name = room_user.temp_match_room.room_name
    # sio.enter_room(sid, room_name, namespace=NAMESPACE)

    match_user = get_match_user_or_none(user_id)
    if match_user is None:
        raise ConnectionRefusedError("temp match user none")
    print(match_user)

    join_match(sid, match_user, username=user_name)


def get_match_user_or_none(user_id: int):
    try:
        temp_user = TempMatchUser.objects.get(user_id=user_id)
    except:
        temp_user = None
    return temp_user


def on_disconnect(sid, reason):
    # TODO: If reason is CLIENT_DISCONNECT, wait to be reconnected

    with sio_session(sid) as sess:
        user_id: int = sess["user_id"]
        username: str = sess["user_name"]

    match_user = get_match_user_or_none(user_id)
    if match_user:
        match_id = match_user.temp_match.id
        match = match_dict.get(match_id)
        if match is not None:
            user = MatchUser(id=match_user.user.id, name=username, sid=sid)
            match.user_disconnected(user)
            print(f"setting lose for user_id={user_id}")
        else:
            print("disconnecting... but match_user not found")
    else:
        print("disconnecting... but match_user not found")


def get_room_user_or_none(user_id: int):
    try:
        temp_match_room_user = TempMatchRoomUser.objects.get(user_id=user_id)
    except:
        temp_match_room_user = None
    return temp_match_room_user


def join_match_ai(sid: str, match_id: int):
    match_dict[match_id].ai_connected(sid)


def join_match(sid: str, match_user: TempMatchUser, username: str):
    room_id = match_user.temp_match.id
    created = False
    is_with_ai = False
    if room_id not in match_dict.get_dict():
        is_with_ai = match_user.temp_match.is_with_ai
        match_dict[room_id] = Match(match_user.temp_match, is_with_ai)
        created = True

    user = MatchUser(id=match_user.user.id, name=username, sid=sid)
    match_dict[room_id].user_connected(user)

    if created and is_with_ai:
        resp = requests.post(f"{GAMEAI_URL}/ai/", json={"match_id": room_id})
        print(f"request to ai has returned! OK={resp.ok}")


def clear_room(room_name: str):
    temp_room = TempMatchRoom.objects.get(room_name=room_name)
    room_user = TempMatchRoomUser.objects.filter(temp_match_room_id=temp_room.id)
    room_user.delete()

    temp_match = TempMatch.objects.filter(match_room_id=temp_room.id)
    temp_match_user = TempMatchUser.objects.filter(temp_match__in=temp_match)

    temp_match_user.delete()
    temp_match.delete()

    temp_room.delete()


def on_paddle_move(sid: str, data: dict[str, Any]):
    print(f"paddle_move event received! sid={sid}, data={data}")
    # paddle_id = get_str(data, "paddleId")

    with sio_session(sid) as sess:
        user_id = sess["user_id"]

    print(f"sid={sid}, user_id={user_id}")

    room = match_dict.get_room_by_userid(user_id)
    if room is None:
        print(f"user_id={user_id} room not found")
        raise InternalException()

    paddle_direction = get_int(data, "paddleDirection")
    print(f"sid={sid}, paddle_direction={paddle_direction}")

    room.match_process.set_paddle(user_id, paddle_direction)


def on_next_game(sid: str):
    user_id, username = _get_from_sess(sid)
    print(f"next_game: sid={sid}, user_id={user_id}")

    user_min_match = TempMatch.objects.filter(tempmatchuser__user_id=user_id).aggregate(
        round=Min("round")
    )["round"]

    match_user = TempMatchUser.objects.filter(
        user_id=user_id, temp_match__round=user_min_match
    ).get()

    print(match_user)
    print("next match id = ", match_user.temp_match.id)

    join_match(sid, match_user, username)


def init_matches(users: List[TempMatchUser]):
    for u in users:
        match_id = u.temp_match.id
        if match_id not in match_dict.get_dict():
            match_dict[match_id] = Match(u.temp_match)

        user = MatchUser(id=u.user.id, name="", sid="")
        print(user)
        match_dict[match_id].user_decided(user)
