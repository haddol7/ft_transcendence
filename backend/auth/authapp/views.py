import random
from typing import Any, Dict
import urllib.parse
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
import requests
import urllib

from authapp.decorators import (
    api_delete,
    api_get,
    api_post,
    authenticated,
)
from authapp.envs import (
    JWT_URL,
    OAUTH_42_URL,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_REDIRECT_URI,
    OAUTH_TOKEN_URL,
    TWOFA_URL,
)
from authapp.models import User
from authapp.utils import create_user, get_str, get_username_from_42, now
from exceptions.CustomException import (
    InternalException,
    UnauthenticatedException,
)
from rest_framework.request import Request

from django.db import transaction

# Create your views here.


# @api_get
# def get_42_oauth(req: Request):
#     redirect_to = get_str(req.query_params, "redirectTo")
#     redirect_to = urllib.parse.quote(redirect_to)

#     return HttpResponseRedirect(
#         f"{OAUTH_42_URL}?"
#         + f"client_id={OAUTH_CLIENT_ID}"
#         + f"&redirect_uri={redirect_to}"
#         + "&response_type=code"
#     )


@api_get
def get_42_code(req: Request):
    code = get_str(req.query_params, "code")

    # ensure state is state
    res = requests.post(
        OAUTH_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "code": code,
        },
    )
    if not res.ok:
        print(f"{res.content}")
        raise UnauthenticatedException()

    res_json = res.json()
    id_42, username = get_username_from_42(res_json["access_token"])
    access_token, refresh_token, isnew = create_user(id_42, username)

    return JsonResponse(
        {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "isnew": isnew,
        }
    )


@api_post
def refresh_token(req: Request, data: Dict[str, Any]):
    refresh_token = get_str(data, "refreshToken")

    res = requests.post(f"{JWT_URL}/jwt/refresh", json={"refresh_token": refresh_token})
    if not res.ok:
        if res.content == "jwt.expired":
            return HttpResponse("jwt.invalid", status=res.status_code)
        return HttpResponse(res.content, status=res.status_code)
    res_json = res.json()
    return JsonResponse(
        {
            "accessToken": res_json["access_token"],
            "refreshToken": res_json["refresh_token"],
        }
    )


@authenticated(skip_2fa=True)
@api_get
def get_2fa(req: Request, user_id: int):
    # Safety: user_id is authenticated with jwt token, so it is safe to call GET
    res = requests.get(f"{TWOFA_URL}/twofa/info", params={"user_id": user_id})

    if not res.ok:
        return HttpResponse(res.content, status=res.status_code)

    res_json = res.json()
    return JsonResponse({"name": res_json["twofa_name"]})


@authenticated(skip_2fa=True)
@api_post
def post_2fa_new(req: Request, user_id: int, data: Dict[str, Any]):
    name = get_str(data, "name")

    # Safety: user is authenticated with JWT token, so it is safe to call POST
    res = requests.post(
        f"{TWOFA_URL}/twofa/info", json={"user_id": user_id, "name": name}
    )

    if not res.ok:
        return HttpResponse(res.content, status=res.status_code)

    res_json = res.json()
    return JsonResponse({"url": res_json["url"]})


@authenticated(skip_2fa=True)
@api_post
def post_2fa(req: Request, user_id: int, data: Dict[str, Any]):
    code = get_str(data, "code")
    res = requests.post(
        f"{TWOFA_URL}/twofa/code", json={"user_id": user_id, "code": code}
    )

    if not res.ok:
        return HttpResponse(res.content, status=res.status_code)
    return JsonResponse({})


def handle_2fa(req: HttpRequest):
    if req.method == "GET":
        return get_2fa(req)
    elif req.method == "POST":
        return post_2fa(req)
    else:
        return HttpResponseNotAllowed(["GET", "POST"])


@authenticated()
@api_delete
def logout(req: Request, user_id: int):
    res = requests.delete(f"{JWT_URL}/jwt/token", params={"user_id": user_id})
    if not res.ok:
        raise InternalException()
    return JsonResponse({})


@api_get
def get_42_code_mock(req: Request):
    user_name = get_str(req.query_params, "user_name")
    id_42 = int(random.random() * 1000000) + 1000000

    access_token, refresh_token, isnew = create_user(id_42, user_name)
    return JsonResponse(
        {"accessToken": access_token, "refreshToken": refresh_token, "isnew": isnew}
    )


@authenticated(skip_2fa=True)
@api_post
def mock_2fa(req: Request, user_id: int, data: Dict[str, Any]):
    res = requests.post(
        f"{TWOFA_URL}/twofa/code",
        json={"user_id": user_id, "code": "1234", "skip": True},
    )
    if not res.ok:
        return HttpResponse(res.content, status=res.status_code)
    return JsonResponse({})
