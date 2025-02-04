import datetime
import os
import random
import string
from time import timezone
from typing import Any, Dict, Tuple, TypedDict

import jwt

from exceptions.CustomException import (
    InternalException,
    JwtExpiredException,
    JwtInvalidException,
    TwoFaNotRegisterException,
    TwoFaRequiredException,
)
from jwtapp.models import User, UserInfo, UserStatus


class JwtPayload(TypedDict):
    user_id: int
    user_secret: str
    exp: datetime.datetime


def get_os_str(key: str) -> str:
    val: str | None = os.getenv(key)
    if val is None:
        raise InternalException()
    return val


def get_os_int(key: str) -> int:
    return int(get_os_str(key))


JWT_EXPIRE_SECONDS = get_os_int("JWT_EXPIRE_SECONDS")
JWT_REFRESH_EXPIRE_SECONDS = get_os_int("JWT_REFRESH_EXPIRE_SECONDS")
JWT_SECRET = get_os_str("JWT_SECRET")
JWT_ALGORITHM = get_os_str("JWT_ALGORITHM")


def generate_secret() -> str:
    LEN = 10
    ret: str = ""
    for _ in range(LEN):
        ret += random.choice(string.ascii_letters + string.digits)
    return ret


def _get_payload(user_id: int, user_secret: str, exp: datetime.datetime) -> JwtPayload:
    return {"user_id": user_id, "user_secret": user_secret, "exp": exp}


def _payloadToDict(payload: JwtPayload) -> Dict[str, Any]:
    return {
        "user_id": payload["user_id"],
        "user_secret": payload["user_secret"],
        "exp": payload["exp"],
    }


def _dictToPayload(decoded_jwt: Dict[str, Any]) -> JwtPayload:
    for key in JwtPayload.__required_keys__:
        if key not in decoded_jwt:
            raise JwtInvalidException()

    return {
        "user_id": decoded_jwt["user_id"],
        "user_secret": decoded_jwt["user_secret"],
        "exp": decoded_jwt["exp"],
    }


def _make_jwt(user_id: int, user_secret: str, exp: datetime.datetime) -> str:
    payload = _get_payload(user_id, user_secret, exp)
    decoded_Jwt = _payloadToDict(payload)
    token = jwt.encode(decoded_Jwt, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def _decode_payload(encoded_jwt: str) -> JwtPayload:
    try:
        decoded_jwt: Dict[str, Any] = jwt.decode(
            jwt=encoded_jwt,
            key=JWT_SECRET,
            algorithms=JWT_ALGORITHM,
            options={"require": ["exp"], "verify_exp": True},
        )
        payload: JwtPayload = _dictToPayload(decoded_jwt)
    except (jwt.exceptions.InvalidSignatureError, jwt.exceptions.DecodeError):
        print("Jwt Invalid Signaturre")
        raise JwtInvalidException()
    except jwt.exceptions.ExpiredSignatureError:
        print("Jwt Expired Signaturre")
        raise JwtExpiredException()
    except Exception as e:
        print("Jwt decode Other exception", e, "type:", type(e))
        raise InternalException()
    return payload


def set_user_secret(
    user_id: int, jwt_secret: str, refresh_secret: str, access_exp: datetime.datetime
):
    user_obj, created = UserStatus.objects.update_or_create(
        user_id=User.objects.get(id=user_id),
        defaults={
            "jwt_secret": jwt_secret,
            "refresh_secret": refresh_secret,
            "expired_at": access_exp,
            "twofa_passed": False,
        },
        create_defaults={
            "jwt_secret": jwt_secret,
            "refresh_secret": refresh_secret,
            "expired_at": access_exp,
            "twofa_passed": False,
        },
    )
    print(f"created={created}")
    user_obj.save()
    print(f"set_user_secret = {user_id}, {jwt_secret}, {refresh_secret}, {access_exp}")
    pass


def get_user_status(user_id: int) -> UserStatus:
    print("get_user_secret, user_id=", user_id)
    user_status = UserStatus.objects.get(pk=user_id)
    return user_status


def get_user_refresh_secret(user_id: int) -> str:
    print("get_user_refresh_secret, user_id=", user_id)
    user_status = UserStatus.objects.get(pk=user_id)
    return user_status.refresh_secret


def make_token_pair(user_id: int) -> Tuple[str, str]:
    now_datetime = datetime.datetime.now(datetime.timezone.utc)
    access_exp = now_datetime + datetime.timedelta(seconds=JWT_EXPIRE_SECONDS)
    refresh_exp = now_datetime + datetime.timedelta(seconds=JWT_REFRESH_EXPIRE_SECONDS)

    jwt_secret = generate_secret()
    refresh_secret = generate_secret()
    set_user_secret(user_id, jwt_secret, refresh_secret, access_exp)

    return _make_jwt(user_id, jwt_secret, access_exp), _make_jwt(
        user_id, refresh_secret, refresh_exp
    )


def get_user_info(user_id: int) -> UserInfo:
    user = UserInfo.objects.get(user_id=User.objects.get(id=user_id))
    return user


def check_jwt(encoded_jwt: str, skip_2fa: bool) -> JwtPayload:
    payload = _decode_payload(encoded_jwt)

    user_status = get_user_status(payload["user_id"])
    if user_status.jwt_secret != payload["user_secret"]:
        print("secret not match")
        raise JwtInvalidException()
    if skip_2fa:
        return payload

    user_info = get_user_info(payload["user_id"])
    if user_info.twofa_secret == "":
        raise TwoFaNotRegisterException()

    if not user_status.twofa_passed:
        raise TwoFaRequiredException()

    return payload


def check_refresh_token(encoded_jwt: str) -> JwtPayload:
    payload = _decode_payload(encoded_jwt)

    user_secret = get_user_refresh_secret(payload["user_id"])
    if user_secret != payload["user_secret"]:
        raise JwtInvalidException()

    return payload
