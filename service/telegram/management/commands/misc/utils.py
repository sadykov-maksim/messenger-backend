def _display_name(first_name: str | None, last_name: str | None, username: str | None, user_id: int) -> str:
    if first_name or last_name:
        full = " ".join([p for p in [first_name or "", last_name or ""] if p]).strip()
        if full:
            return full
    if username:
        return f"@{username}"
    return f"User {user_id}"


def _extract_start_payload(text: str | None) -> str | None:
    # /start payload  OR  /start
    if not text:
        return None
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip() or None
    return None