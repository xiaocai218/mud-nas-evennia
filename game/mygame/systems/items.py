"""Item and inventory helpers."""

from evennia.utils.create import create_object


def get_inventory_items(caller):
    return [obj for obj in caller.contents_get(content_type="object") if getattr(obj.db, "is_item", False)]


def find_item(caller, item_name):
    return next((obj for obj in get_inventory_items(caller) if obj.key == item_name), None)


def create_loot(caller, key, desc):
    item = create_object("typeclasses.items.Item", key=key, location=caller)
    item.db.desc = desc
    return item


def create_reward_item(caller, key, desc):
    item = create_object("typeclasses.items.Item", key=key, location=caller)
    item.db.desc = desc
    return item
