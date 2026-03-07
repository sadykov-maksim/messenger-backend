
import hmac
import hashlib
import time
import os
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

WS_TRANSPORT_KEY = bytes.fromhex("6e0ba81549b4905a42126f634848a3b2d967e7039abdbf65e8853f7fb3c79f6a")

# Create your views here.
@csrf_exempt
@require_POST
def transport_key(request):
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model

    # Достаём токен из заголовка Authorization
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        token_str = auth_header.split(" ")[1]
        token = AccessToken(token_str)
        user_id = token["id"]
    except Exception:
        return JsonResponse({"error": "Invalid token"}, status=401)

    master_key = WS_TRANSPORT_KEY
    window = int(time.time()) // 300

    def derive(w):
        payload = f"{user_id}:{w}".encode()
        return hmac.new(master_key, payload, hashlib.sha256).digest().hex()

    curr = derive(window)
    prev = derive(window - 1)

    import logging
    logging.warning(f"[VIEW] user_id={user_id} window={window}")
    logging.warning(f"[VIEW] key_curr={curr}")

    return JsonResponse({
        "key": curr,
        "key_prev": prev,
        "expires_in": 300 - (int(time.time()) % 300)
    })