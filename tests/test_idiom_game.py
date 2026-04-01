import os
import tempfile
import unittest

import idiom_game


class TestLeaderboard(unittest.TestCase):
    def test_parse_leaderboard_line_valid(self):
        self.assertEqual(idiom_game.parse_leaderboard_line("张三:12"), ("张三", 12))

    def test_parse_leaderboard_line_invalid(self):
        self.assertIsNone(idiom_game.parse_leaderboard_line("bad_line"))
        self.assertIsNone(idiom_game.parse_leaderboard_line("张三:abc"))

    def test_update_leaderboard_keeps_top_five(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "leaderboard.txt")
            for name, score in [("a", 3), ("b", 9), ("c", 4), ("d", 7), ("e", 5), ("f", 8)]:
                idiom_game.update_leaderboard(path, name, score)
            records = idiom_game.load_leaderboard(path)
            self.assertEqual(len(records), 5)
            self.assertEqual(records[0], ("b", 9))
            self.assertEqual(records[1], ("f", 8))


class TestBattleHelpers(unittest.TestCase):
    def test_apply_battle_guess_reveals_char(self):
        display = ["_", "_", "_", "_"]
        changed = idiom_game.apply_battle_guess("画蛇添足", display, 0, "画")
        self.assertTrue(changed)
        self.assertEqual(display, ["画", "_", "_", "_"])

    def test_is_word_revealed(self):
        self.assertTrue(idiom_game.is_word_revealed("画蛇添足", ["画", "蛇", "添", "足"]))
        self.assertFalse(idiom_game.is_word_revealed("画蛇添足", ["画", "_", "添", "足"]))

    def test_apply_battle_guess_rejects_non_single_char(self):
        display = ["_", "_", "_", "_"]
        changed = idiom_game.apply_battle_guess("画蛇添足", display, 0, "中国")
        self.assertFalse(changed)
        self.assertEqual(display, ["_", "_", "_", "_"])


class TestBonusHelpers(unittest.TestCase):
    def test_parse_int_in_range(self):
        self.assertEqual(idiom_game.parse_int_in_range("2", 1, 3), 2)
        self.assertIsNone(idiom_game.parse_int_in_range("x", 1, 3))
        self.assertIsNone(idiom_game.parse_int_in_range("9", 1, 3))

    def test_normalize_single_char_input(self):
        self.assertEqual(idiom_game.normalize_single_char_input(" 画 "), "画")
        self.assertIsNone(idiom_game.normalize_single_char_input("ab"))
        self.assertIsNone(idiom_game.normalize_single_char_input(""))

    def test_run_description_challenge_round(self):
        idiom = idiom_game.Idiom("画蛇添足", "比喻做事多此一举，反而坏事", "寓言")
        options = ["画蛇添足", "掩耳盗铃", "守株待兔", "井底之蛙"]
        won, gained = idiom_game.run_description_challenge_round(idiom, options, "1")
        self.assertTrue(won)
        self.assertEqual(gained, 5)
        won, gained = idiom_game.run_description_challenge_round(idiom, options, "2")
        self.assertFalse(won)
        self.assertEqual(gained, 0)


if __name__ == "__main__":
    unittest.main()
