import os

from exceptions.CustomException import InternalException


def get_os_str(key: str) -> str:
    val: str | None = os.getenv(key)
    if val is None:
        raise InternalException()
    return val


def get_os_int(key: str) -> int:
    return int(get_os_str(key))


GAME_URL = get_os_str("GAME_URL")
JWT_URL = get_os_str("JWT_URL")
USER_URL = get_os_str("USER_URL")
GAMEAI_URL = get_os_str("GAMEAI_URL")
FRONTEND_URL = get_os_str("FRONTEND_URL")
