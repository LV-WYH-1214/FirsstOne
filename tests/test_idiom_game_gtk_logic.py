import importlib
import sys
import types
import unittest
from unittest import mock
from unittest.mock import patch


def _load_module_with_fake_gtk():
    fake_gtk = types.SimpleNamespace(
        Window=type("Window", (), {}),
        Box=type("Box", (), {}),
        Label=type("Label", (), {}),
        Entry=type("Entry", (), {}),
        Button=type("Button", (), {}),
        MessageDialog=type("MessageDialog", (), {}),
        MessageType=types.SimpleNamespace(QUESTION=1),
        ButtonsType=types.SimpleNamespace(YES_NO=1),
        ResponseType=types.SimpleNamespace(YES=1),
        Orientation=types.SimpleNamespace(VERTICAL=1, HORIZONTAL=2),
        main_quit=lambda: None,
        main=lambda: None,
    )
    fake_repo = types.ModuleType("gi.repository")
    fake_repo.Gtk = fake_gtk
    fake_gi = types.ModuleType("gi")
    fake_gi.require_version = lambda *_args, **_kwargs: None
    fake_gi.repository = fake_repo

    with patch.dict(sys.modules, {"gi": fake_gi, "gi.repository": fake_repo}):
        import idiom_game_gtk

        return importlib.reload(idiom_game_gtk)


class TestIdiomGameGtkLogic(unittest.TestCase):
    def test_parse_difficulty_to_hide_count(self):
        module = _load_module_with_fake_gtk()
        self.assertEqual(1, module.parse_difficulty_to_hide_count("1"))
        self.assertEqual(2, module.parse_difficulty_to_hide_count("2"))
        self.assertEqual(3, module.parse_difficulty_to_hide_count("3"))
        with self.assertRaises(ValueError):
            module.parse_difficulty_to_hide_count("4")

    def test_select_category_pool(self):
        module = _load_module_with_fake_gtk()
        idioms = [
            module.idiom_game.Idiom("画蛇添足", "d1", "寓言"),
            module.idiom_game.Idiom("井底之蛙", "d2", "动物"),
        ]
        self.assertEqual(2, len(module.select_category_pool(idioms, "全部")))
        self.assertEqual(["画蛇添足"], [i.word for i in module.select_category_pool(idioms, "寓言")])
        self.assertEqual([], module.select_category_pool(idioms, "人物"))

    def test_validate_single_guess_input_matches_cli_rules(self):
        module = _load_module_with_fake_gtk()
        ok, msg = module.validate_single_guess_input("画蛇", "画蛇添足")
        self.assertTrue(ok)
        self.assertEqual("", msg)

        ok, msg = module.validate_single_guess_input("", "画蛇添足")
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)

        ok, msg = module.validate_single_guess_input("abc1", "abcd")
        self.assertFalse(ok)
        self.assertIn("纯字母拼音", msg)

        ok, msg = module.validate_single_guess_input("toolong", "abcd")
        self.assertFalse(ok)
        self.assertIn("输入过长", msg)

    def test_format_learning_feedback_contains_example_when_present(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇添足", "比喻多此一举", "寓言", "这是例句")
        text = module.format_learning_feedback(idiom)
        self.assertIn("学习提示：比喻多此一举", text)
        self.assertIn("例句：这是例句", text)

    def test_format_top5_leaderboard_renders_all_lines(self):
        module = _load_module_with_fake_gtk()
        board_text = module.format_top5_leaderboard(
            [("A", 10), ("B", 9), ("C", 8), ("D", 7), ("E", 6)]
        )
        self.assertIn("TOP 5", board_text)
        self.assertIn("1. A - 10", board_text)
        self.assertIn("5. E - 6", board_text)

    def test_next_mode_state_switches_mode_and_keeps_shared_fields(self):
        module = _load_module_with_fake_gtk()
        state = {
            "mode": "single",
            "substate": "playing",
            "score": 18,
            "streak": 2,
            "status": "ok",
        }

        new_state = module.next_mode_state(state, "battle")
        self.assertEqual("battle", new_state["mode"])
        self.assertEqual(18, new_state["score"])
        self.assertEqual(2, new_state["streak"])

    def test_resolve_gtk_voice_guess_result_success(self):
        module = _load_module_with_fake_gtk()
        guess, status = module.resolve_gtk_voice_guess_result(" 语音答案 ", None)
        self.assertEqual("语音答案", guess)
        self.assertEqual("语音识别成功，已填入输入框。", status)

    def test_resolve_gtk_voice_guess_result_failure_reason(self):
        module = _load_module_with_fake_gtk()
        guess, status = module.resolve_gtk_voice_guess_result(None, "麦克风不可用")
        self.assertIsNone(guess)
        self.assertEqual("麦克风不可用", status)

    def test_resolve_gtk_voice_guess_result_failure_invalid_text(self):
        module = _load_module_with_fake_gtk()
        guess, status = module.resolve_gtk_voice_guess_result("   ", None)
        self.assertIsNone(guess)
        self.assertEqual("语音结果不符合输入要求，请改用键盘输入。", status)

    def test_create_battle_round_state_initializes_round(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇添足", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "甲", "乙")

        self.assertEqual(["_", "_", "_", "_"], state["display"])
        self.assertEqual(["甲", "乙"], state["players"])
        self.assertEqual(0, state["turn"])
        self.assertEqual(16, state["max_turns"])
        self.assertFalse(state["finished"])
        self.assertIsNone(state["winner"])
        self.assertEqual(0, state["winner_score"])

    def test_create_battle_round_state_normalizes_blank_player_names(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇添足", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "  ", "")
        self.assertEqual(["玩家1", "玩家2"], state["players"])

    def test_apply_battle_turn_reveals_and_switches_turn(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "甲", "乙")

        updated = module.apply_battle_turn(state, "1", "画")
        self.assertEqual(["画", "_"], updated["display"])
        self.assertEqual(1, updated["turn"])
        self.assertFalse(updated["finished"])
        self.assertEqual("乙", module.get_battle_current_player(updated))

    def test_apply_battle_turn_detects_winner(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "甲", "乙")

        updated = module.apply_battle_turn(state, "1", "画")
        self.assertTrue(updated["finished"])
        self.assertEqual("甲", updated["winner"])
        self.assertEqual(10, updated["winner_score"])

    def test_apply_battle_turn_draw_on_max_turns(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "甲", "乙")
        state["max_turns"] = 1

        updated = module.apply_battle_turn(state, "1", "错")
        self.assertTrue(updated["finished"])
        self.assertIsNone(updated["winner"])
        self.assertEqual(0, updated["winner_score"])
        self.assertIn("平局", updated["status"])

    def test_apply_battle_turn_invalid_input_keeps_turn(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇", "desc", "寓言")
        state = module.create_battle_round_state(idiom, "甲", "乙")

        updated = module.apply_battle_turn(state, "9", "画")
        self.assertEqual(0, updated["turn"])
        self.assertIn("位置", updated["status"])

    def test_apply_battle_turn_finished_round_is_noop(self):
        module = _load_module_with_fake_gtk()
        state = {
            "finished": True,
            "word": "画蛇",
            "display": ["画", "_"],
            "turn": 2,
            "status": "done",
            "players": ["甲", "乙"],
        }
        updated = module.apply_battle_turn(state, "1", "蛇")
        self.assertIs(updated, state)
        self.assertEqual(2, updated["turn"])
        self.assertEqual("done", updated["status"])

    def test_resolve_battle_winner_score_updates_cumulative_scores(self):
        module = _load_module_with_fake_gtk()
        scores, winner_entry = module.resolve_battle_winner_score({"甲": 7, "乙": 3}, "甲", 10)
        self.assertEqual({"甲": 17, "乙": 3}, scores)
        self.assertEqual(("甲", 17), winner_entry)

    def test_resolve_battle_winner_score_draw_keeps_scores(self):
        module = _load_module_with_fake_gtk()
        original = {"甲": 7, "乙": 3}
        scores, winner_entry = module.resolve_battle_winner_score(original, None, 0)
        self.assertEqual(original, scores)
        self.assertIsNone(winner_entry)
        self.assertIsNot(original, scores)

    def test_next_mode_state_sets_challenge_ready(self):
        module = _load_module_with_fake_gtk()
        state = {
            "mode": "single",
            "substate": "single-playing",
            "score": 5,
            "streak": 1,
            "status": "x",
        }

        new_state = module.next_mode_state(state, module.MODE_CHALLENGE)
        self.assertEqual(module.MODE_CHALLENGE, new_state["mode"])
        self.assertEqual("challenge-ready", new_state["substate"])
        self.assertIn("释义挑战", new_state["status"])

    def test_next_mode_state_rejects_unknown_mode(self):
        module = _load_module_with_fake_gtk()
        with self.assertRaises(ValueError):
            module.next_mode_state({"mode": "single"}, "unknown")

    def test_build_description_challenge_round_returns_four_unique_options(self):
        module = _load_module_with_fake_gtk()
        idioms = [
            module.idiom_game.Idiom("画蛇添足", "d1", "寓言"),
            module.idiom_game.Idiom("掩耳盗铃", "d2", "寓言"),
            module.idiom_game.Idiom("守株待兔", "d3", "寓言"),
            module.idiom_game.Idiom("井底之蛙", "d4", "寓言"),
        ]

        idiom, options = module.build_description_challenge_round(idioms, rng=module.random.Random(1))
        self.assertEqual(4, len(options))
        self.assertEqual(4, len(set(options)))
        self.assertIn(idiom.word, options)

    def test_build_description_challenge_round_requires_four_unique_idioms(self):
        module = _load_module_with_fake_gtk()
        idioms = [
            module.idiom_game.Idiom("画蛇添足", "d1", "寓言"),
            module.idiom_game.Idiom("画蛇添足", "d2", "寓言"),
            module.idiom_game.Idiom("守株待兔", "d3", "寓言"),
        ]
        with self.assertRaises(ValueError):
            module.build_description_challenge_round(idioms, rng=module.random.Random(2))

    def test_evaluate_description_challenge_choice_correct_adds_five(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇添足", "d1", "寓言")
        options = ["画蛇添足", "掩耳盗铃", "守株待兔", "井底之蛙"]

        won, gain, score = module.evaluate_description_challenge_choice(idiom, options, 0, 10)
        self.assertTrue(won)
        self.assertEqual(5, gain)
        self.assertEqual(15, score)

    def test_evaluate_description_challenge_choice_wrong_no_score_gain(self):
        module = _load_module_with_fake_gtk()
        idiom = module.idiom_game.Idiom("画蛇添足", "d1", "寓言")
        options = ["画蛇添足", "掩耳盗铃", "守株待兔", "井底之蛙"]

        won, gain, score = module.evaluate_description_challenge_choice(idiom, options, 2, 10)
        self.assertFalse(won)
        self.assertEqual(0, gain)
        self.assertEqual(10, score)

    def test_evaluate_description_challenge_choice_accumulates_across_rounds(self):
        module = _load_module_with_fake_gtk()
        idiom1 = module.idiom_game.Idiom("画蛇添足", "d1", "寓言")
        options1 = ["掩耳盗铃", "画蛇添足", "守株待兔", "井底之蛙"]
        won1, gain1, score1 = module.evaluate_description_challenge_choice(idiom1, options1, 1, 0)
        self.assertTrue(won1)
        self.assertEqual(5, gain1)
        self.assertEqual(5, score1)

        idiom2 = module.idiom_game.Idiom("掩耳盗铃", "d2", "寓言")
        options2 = ["掩耳盗铃", "画蛇添足", "守株待兔", "井底之蛙"]
        won2, gain2, score2 = module.evaluate_description_challenge_choice(idiom2, options2, 2, score1)
        self.assertFalse(won2)
        self.assertEqual(0, gain2)
        self.assertEqual(5, score2)

    def test_format_top5_leaderboard_empty(self):
        module = _load_module_with_fake_gtk()
        text = module.format_top5_leaderboard([])
        self.assertIn("TOP 5", text)
        self.assertIn("暂无记录", text)

    def test_elapsed_seconds_returns_zero_when_clock_moves_back(self):
        module = _load_module_with_fake_gtk()
        dummy = types.SimpleNamespace(round_start_time=100.0)
        with patch.object(module.time, "monotonic", return_value=90.0):
            elapsed = module.IdiomGameGtkWindow._elapsed_seconds(dummy)
        self.assertEqual(0.0, elapsed)

    def test_build_round_status_text_timed_includes_countdown(self):
        module = _load_module_with_fake_gtk()
        dummy = types.SimpleNamespace(
            attempts=2,
            timed_mode=True,
            state={"score": 8},
            _elapsed_seconds=lambda: 4.2,
        )
        text = module.IdiomGameGtkWindow._build_round_status_text(dummy)
        self.assertIn("剩余机会：2", text)
        self.assertIn("当前总分：8", text)
        self.assertIn("剩余时间：26 秒", text)

    def test_save_single_round_record_persists_single_gtk_mode(self):
        module = _load_module_with_fake_gtk()
        dummy = types.SimpleNamespace(
            player_name="阿甲",
            state={"score": 12},
            _elapsed_seconds=lambda: 3.5,
        )
        with patch.object(module.idiom_game, "save_game_record") as mock_save:
            module.IdiomGameGtkWindow._save_single_round_record(dummy, True)
        mock_save.assert_called_once_with(
            module.idiom_game.RECORD_FILE,
            "阿甲",
            "single-gtk",
            True,
            3.5,
            12,
        )

    def test_update_high_score_if_needed_saves_and_refreshes(self):
        module = _load_module_with_fake_gtk()
        dummy = types.SimpleNamespace(
            state={"score": 15},
            high_score=10,
            update_high_score_label=mock.Mock(),
        )
        with patch.object(module.idiom_game, "save_high_score") as mock_save:
            module.IdiomGameGtkWindow._update_high_score_if_needed(dummy)
        self.assertEqual(15, dummy.high_score)
        dummy.update_high_score_label.assert_called_once()
        mock_save.assert_called_once_with(module.idiom_game.SCORE_FILE, 15)


if __name__ == "__main__":
    unittest.main()
