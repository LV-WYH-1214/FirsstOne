import os
import tempfile
import unittest
from unittest import mock

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


class TestSingleRoundHints(unittest.TestCase):
    def setUp(self):
        self.idiom = idiom_game.Idiom("画蛇添足", "desc", "寓言")

    def test_first_hint_reveals_last_char_when_accepted(self):
        guesses = iter(["aaa", "bbb", "ccc"])
        with mock.patch.object(idiom_game, "random") as mock_random, \
             mock.patch.object(idiom_game, "mask_word", return_value="____"), \
             mock.patch.object(idiom_game, "ask_yes_no", return_value=True), \
             mock.patch("builtins.print") as mock_print:
            mock_random.choice.return_value = self.idiom
            idiom_game.play_round(
                [self.idiom],
                hide_count=2,
                timed_mode=False,
                learning_mode=False,
                input_func=lambda _word: next(guesses),
            )
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("提示：最后一个字是“足”", printed)

    def test_second_hint_reveals_second_char_on_last_attempt(self):
        guesses = iter(["aaa", "bbb", "ccc"])
        with mock.patch.object(idiom_game, "random") as mock_random, \
             mock.patch.object(idiom_game, "mask_word", return_value="____"), \
             mock.patch.object(idiom_game, "ask_yes_no", return_value=True), \
             mock.patch("builtins.print") as mock_print:
            mock_random.choice.return_value = self.idiom
            idiom_game.play_round(
                [self.idiom],
                hide_count=2,
                timed_mode=False,
                learning_mode=False,
                input_func=lambda _word: next(guesses),
            )
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("提示：第二个字是“蛇”", printed)


class TestSingleModeValidationAndRecords(unittest.TestCase):
    def test_is_pinyin_guess(self):
        self.assertTrue(idiom_game._is_pinyin_guess("huashetianzu"))
        self.assertFalse(idiom_game._is_pinyin_guess("hua1"))
        self.assertFalse(idiom_game._is_pinyin_guess("画蛇"))

    def test_safe_single_guess_input_rejects_invalid_and_too_long(self):
        with mock.patch.object(idiom_game, "safe_input", side_effect=["ab1", "toolong", "okay"]), \
             mock.patch("builtins.print") as mock_print:
            value = idiom_game._safe_single_guess_input("abcd")
            self.assertEqual(value, "okay")
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("请输入纯字母拼音。", printed)
        self.assertIn("输入过长，请输入不超过 4 个字母。", printed)

    def test_parse_record_line(self):
        line = "2026-04-01 23:00:00:小明:single:win:12.50:20"
        parsed = idiom_game.parse_record_line(line)
        self.assertEqual(parsed["player_name"], "小明")
        self.assertEqual(parsed["mode"], "single")
        self.assertTrue(parsed["won"])
        self.assertEqual(parsed["score"], 20)

    def test_parse_record_line_invalid(self):
        self.assertIsNone(idiom_game.parse_record_line("bad"))
        self.assertIsNone(idiom_game.parse_record_line("2026-04-01 23:00:00:小明:single:unknown:1.0:2"))


class TestVoiceInputHelpers(unittest.TestCase):
    def test_detect_space_hold_trigger_false_without_keyboard(self):
        with mock.patch.object(idiom_game, "keyboard", None):
            self.assertFalse(idiom_game.detect_space_hold_trigger(window_seconds=0.01))

    def test_read_text_with_optional_voice_uses_voice_result(self):
        with mock.patch.object(idiom_game, "detect_space_hold_trigger", return_value=True), \
             mock.patch.object(idiom_game, "VOICE_ENGINE") as mock_engine, \
             mock.patch("builtins.input", return_value="键盘"):
            mock_engine.transcribe_while_space_held.return_value = ("语音答案", None)
            value = idiom_game.read_text_with_optional_voice("请输入：")
            self.assertEqual(value, "语音答案")

    def test_read_text_with_optional_voice_fallback_to_keyboard(self):
        with mock.patch.object(idiom_game, "detect_space_hold_trigger", return_value=True), \
             mock.patch.object(idiom_game, "VOICE_ENGINE") as mock_engine, \
             mock.patch("builtins.input", return_value="键盘答案"):
            mock_engine.transcribe_while_space_held.return_value = (None, "语音识别为空")
            value = idiom_game.read_text_with_optional_voice("请输入：")
            self.assertEqual(value, "键盘答案")

    def test_read_text_with_optional_voice_invalid_by_validator(self):
        with mock.patch.object(idiom_game, "detect_space_hold_trigger", return_value=True), \
             mock.patch.object(idiom_game, "VOICE_ENGINE") as mock_engine, \
             mock.patch("builtins.input", return_value="2"):
            mock_engine.transcribe_while_space_held.return_value = ("abc", None)
            value = idiom_game.read_text_with_optional_voice(
                "输入 1-3：",
                validator=lambda text: idiom_game.parse_int_in_range(text, 1, 3) is not None,
            )
            self.assertEqual(value, "2")


if __name__ == "__main__":
    unittest.main()
