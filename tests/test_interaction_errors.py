import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT.parent
sys.path.insert(0, str(PLAYGROUND / "evennia-local-env"))
sys.path.insert(0, str(ROOT / "game" / "mygame"))
os.chdir(ROOT / "game" / "mygame")

from systems.interaction_errors import build_interaction_error, resolve_interaction_error_message  # noqa: E402


class InteractionErrorTests(unittest.TestCase):
    def test_target_not_found_uses_common_dialogue(self):
        with patch("systems.interaction_errors.get_dialogue", return_value="没有找到目标。"):
            message = resolve_interaction_error_message("target_not_found")
        self.assertEqual(message, "没有找到目标。")

    def test_build_interaction_error_includes_message(self):
        payload = build_interaction_error("target_not_talkable", target="守渡老人")
        self.assertEqual(payload["code"], "target_not_talkable")
        self.assertIn("守渡老人", payload["message"])


if __name__ == "__main__":
    unittest.main()
