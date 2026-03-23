"""NPC talk route configuration helpers."""

import json
from pathlib import Path


NPC_ROUTE_DATA_PATH = Path(__file__).resolve().parent.parent / "world" / "data" / "npc_routes.json"


def _load_npc_routes():
    with NPC_ROUTE_DATA_PATH.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


NPC_ROUTES = _load_npc_routes()


def get_npc_route(route_key):
    return NPC_ROUTES.get(route_key)
