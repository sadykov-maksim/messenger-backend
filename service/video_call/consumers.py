import json
import logging
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

logger = logging.getLogger(__name__)



pending_calls: dict[str, tuple] = {}



class CallConsumer(WebsocketConsumer):

    def connect(self):
        self.my_name: str | None = None
        self.in_call_with: str | None = None
        self.accept()
        self._send("connection", {"message": "Connected"})

    def disconnect(self, close_code):
        if self.my_name:
            if self.in_call_with:
                async_to_sync(self.channel_layer.group_send)(
                    self.in_call_with,
                    {"type": "call_ended", "data": {"reason": "peer_disconnected"}}
                )
                self.in_call_with = None

            async_to_sync(self.channel_layer.group_discard)(self.my_name, self.channel_name)
            logger.info("User '%s' disconnected.", self.my_name)

    def session_evicted(self, event):
        self._send("session_evicted", event["data"])
        self.close()  # закрываем старый WS

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _send(self, event_type: str, data: dict):
        self.send(text_data=json.dumps({"type": event_type, "data": data}))

    def _send_error(self, code: str, message: str):
        self._send("error", {"code": code, "message": message})

    # ------------------------------------------------------------------ #
    #  Receive                                                             #
    # ------------------------------------------------------------------ #

    def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return self._send_error("bad_json", "Invalid JSON")

        event_type = payload.get("type")
        data = payload.get("data") or {}

        if not event_type:
            return self._send_error("bad_request", "Missing 'type'")

        handler = getattr(self, f"_handle_{event_type}", None)
        if handler is None:
            return self._send_error("unknown_type", f"Unknown type: {event_type}")

        # Все события, кроме login, требуют авторизации
        if event_type != "login" and not self.my_name:
            return self._send_error("not_logged_in", "Login first")

        handler(data)

    # ------------------------------------------------------------------ #
    #  Client-event handlers                                               #
    # ------------------------------------------------------------------ #

    def _handle_login(self, data: dict):
        name = data.get("name", "").strip()
        if not name:
            return self._send_error("bad_request", "Missing data.name")

        self.my_name = name
        async_to_sync(self.channel_layer.group_add)(self.my_name, self.channel_name)
        self._send("login", {"success": True, "name": name})
        logger.info("User '%s' logged in.", name)

        # Проверяем есть ли пропущенный входящий звонок
        if name in pending_calls:
            caller, rtc, ts = pending_calls.pop(name)
            import time
            # Звонок не старше 60 секунд
            if time.time() - ts < 60:
                self._send("call_received", {"caller": caller, "rtcMessage": rtc})
                logger.info("Delivered pending call from '%s' to '%s'", caller, name)

    def _handle_call(self, data: dict):
        callee = data.get("callee", "").strip()
        rtc = data.get("rtcMessage")

        if not callee or not rtc:
            return self._send_error("bad_request", "Missing callee or rtcMessage")
        if callee == self.my_name:
            return self._send_error("bad_request", "Cannot call yourself")

        self.in_call_with = callee

        # Пробуем отправить напрямую
        import time
        # Сохраняем как pending на случай если получатель ещё не залогинен
        pending_calls[callee] = (self.my_name, rtc, time.time())

        async_to_sync(self.channel_layer.group_send)(
            callee,
            {
                "type": "call_received",
                "data": {"caller": self.my_name, "rtcMessage": rtc},
            }
        )
        logger.info("'%s' is calling '%s'.", self.my_name, callee)

    def _handle_answer_call(self, data: dict):
        caller = data.get("caller", "").strip()
        rtc = data.get("rtcMessage")

        if not caller:
            return self._send_error("bad_request", "Missing data.caller")
        if not rtc:
            return self._send_error("bad_request", "Missing data.rtcMessage")

        self.in_call_with = caller
        async_to_sync(self.channel_layer.group_send)(
            caller,
            {"type": "call_answered", "data": {"rtcMessage": rtc}}
        )

    def _handle_reject_call(self, data: dict):
        """Callee отклоняет входящий звонок."""
        caller = data.get("caller", "").strip()
        if not caller:
            return self._send_error("bad_request", "Missing data.caller")

        async_to_sync(self.channel_layer.group_send)(
            caller,
            {"type": "call_rejected", "data": {"rejected_by": self.my_name}}
        )

    def _handle_end_call(self, data: dict):
        """Любая сторона завершает звонок."""
        peer = data.get("peer") or self.in_call_with
        if not peer:
            return self._send_error("bad_request", "Missing data.peer")

        self.in_call_with = None
        async_to_sync(self.channel_layer.group_send)(
            peer,
            {"type": "call_ended", "data": {"ended_by": self.my_name}}
        )

    def _handle_ICEcandidate(self, data: dict):
        user = data.get("user", "").strip()
        rtc = data.get("rtcMessage")

        if not user:
            return self._send_error("bad_request", "Missing data.user")
        if not rtc:
            return self._send_error("bad_request", "Missing data.rtcMessage")

        async_to_sync(self.channel_layer.group_send)(
            user,
            {"type": "ICEcandidate", "data": {"rtcMessage": rtc}}
        )

    # ------------------------------------------------------------------ #
    #  Channel-layer event handlers (входящие от других consumers)         #
    # ------------------------------------------------------------------ #

    def call_received(self, event):
        self._send("call_received", event["data"])

    def call_answered(self, event):
        self._send("call_answered", event["data"])

    def call_rejected(self, event):
        self.in_call_with = None
        self._send("call_rejected", event["data"])

    def call_ended(self, event):
        self.in_call_with = None
        self._send("call_ended", event["data"])

    def ICEcandidate(self, event):
        self._send("ICEcandidate", event["data"])