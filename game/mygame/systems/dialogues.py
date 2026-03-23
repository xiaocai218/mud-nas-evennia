"""NPC dialogue configuration helpers."""

from .content_loader import load_content


DIALOGUE_DATA = load_content("dialogues")


def get_dialogue(section, key, **kwargs):
    text = DIALOGUE_DATA.get(section, {}).get(key, "")
    return text.format(**kwargs) if kwargs else text
