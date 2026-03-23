"""Help and newbie content loaders."""

from .content_loader import load_content


HELP_CONTENT = load_content("help_content")


def get_newbie_content():
    return HELP_CONTENT["newbie"]


def get_help_entries():
    return HELP_CONTENT["help_entries"]
