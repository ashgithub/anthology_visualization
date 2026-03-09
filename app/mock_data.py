from collections.abc import Iterable


def clamp_limit(value: int, *, default: int, max_value: int) -> int:
    if value is None:
        return default
    return max(0, min(int(value), max_value))


def limit_list(items: Iterable, limit: int):
    items_list = list(items)
    return items_list[:limit], len(items_list) > limit
