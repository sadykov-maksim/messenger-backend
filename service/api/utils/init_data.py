import urllib.parse


def parse_init_data(raw: str) -> dict:
    pairs = urllib.parse.parse_qsl(raw, keep_blank_values=True)
    data = {k: v for k, v in pairs}
    return data


