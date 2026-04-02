import random
import time
from typing import Optional

try:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ImportError, ValueError) as exc:
    raise SystemExit(
        "未检测到 GTK 运行环境。请先安装 PyGObject/GTK 后再运行图形界面版本。"
    ) from exc

import idiom_game


MODE_SINGLE = "single"
MODE_BATTLE = "battle"
MODE_CHALLENGE = "challenge"
SUPPORTED_MODES = {MODE_SINGLE, MODE_BATTLE, MODE_CHALLENGE}
CHALLENGE_ROUNDS = 3
CHALLENGE_OPTIONS = 4
SINGLE_CATEGORY_OPTIONS = ["全部", "寓言", "动物", "人物"]


def resolve_gtk_voice_guess_result(
    voice_text: Optional[str],
    reason: Optional[str],
    invalid_voice_message: str = "语音结果不符合输入要求，请改用键盘输入。",
) -> tuple[Optional[str], str]:
    if voice_text is None:
        return None, reason or "语音输入不可用，请改用键盘输入。"
    normalized = voice_text.strip()
    if not normalized:
        return None, invalid_voice_message
    return normalized, "语音识别成功，已填入输入框。"


def create_battle_round_state(idiom: idiom_game.Idiom, player1: str, player2: str) -> dict:
    normalized_player1 = player1.strip() or "玩家1"
    normalized_player2 = player2.strip() or "玩家2"
    return {
        "idiom": idiom,
        "word": idiom.word,
        "display": ["_"] * len(idiom.word),
        "players": [normalized_player1, normalized_player2],
        "turn": 0,
        "max_turns": max(1, len(idiom.word) * 4),
        "finished": False,
        "winner": None,
        "winner_score": 0,
        "status": "双人对战进行中。",
    }


def get_battle_current_player(state: dict) -> str:
    players = state["players"]
    return players[state["turn"] % len(players)]


def apply_battle_turn(state: dict, position_text: str, guess_text: str) -> dict:
    if state.get("finished"):
        return state
    word = state["word"]
    position = idiom_game.parse_int_in_range(position_text, 1, len(word))
    if position is None:
        state["status"] = "位置输入无效，请输入有效范围。"
        return state
    guess_char = idiom_game.normalize_single_char_input(guess_text)
    if guess_char is None:
        state["status"] = "猜测字符无效，请输入单个字符。"
        return state
    current_player = get_battle_current_player(state)
    changed = idiom_game.apply_battle_guess(word, state["display"], position - 1, guess_char)
    if changed:
        if idiom_game.is_word_revealed(word, state["display"]):
            state["finished"] = True
            state["winner"] = current_player
            state["winner_score"] = 10
            state["status"] = f"{current_player} 率先拼出完整成语，获胜！答案：{word}"
            return state
        state["status"] = f"{current_player} 猜对了，轮到下一位。"
    else:
        state["status"] = "猜错了，或该位置已揭示/无效。"
    state["turn"] += 1
    if state["turn"] >= state["max_turns"]:
        state["finished"] = True
        state["winner"] = None
        state["winner_score"] = 0
        state["status"] = "达到回合上限，本局平局。"
    return state


def resolve_battle_winner_score(
    scores: dict[str, int], winner: Optional[str], winner_score: int
) -> tuple[dict[str, int], Optional[tuple[str, int]]]:
    new_scores = dict(scores)
    if winner is None or winner_score <= 0:
        return new_scores, None
    total = new_scores.get(winner, 0) + winner_score
    new_scores[winner] = total
    return new_scores, (winner, total)


def next_mode_state(state: dict, target_mode: str) -> dict:
    if target_mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {target_mode}")
    new_state = dict(state)
    new_state["mode"] = target_mode
    if target_mode == MODE_SINGLE:
        new_state["substate"] = "single-ready"
        new_state["status"] = "已切换到单人模式。"
    elif target_mode == MODE_BATTLE:
        new_state["substate"] = "battle-ready"
        new_state["status"] = "已切换到双人对战模式。"
    else:
        new_state["substate"] = "challenge-ready"
        new_state["status"] = "创新模式：释义挑战（3轮）"
    return new_state


def build_description_challenge_round(
    idioms: list[idiom_game.Idiom], rng: random.Random = random
) -> tuple[idiom_game.Idiom, list[str]]:
    unique_words = list({item.word for item in idioms})
    if len(unique_words) < CHALLENGE_OPTIONS:
        raise ValueError("描述挑战模式至少需要 4 个不同成语。")
    idiom = rng.choice(idioms)
    distractors = rng.sample([word for word in unique_words if word != idiom.word], CHALLENGE_OPTIONS - 1)
    options = [idiom.word, *distractors]
    rng.shuffle(options)
    return idiom, options


def evaluate_description_challenge_choice(
    idiom: idiom_game.Idiom, options: list[str], selected_index: int, current_score: int
) -> tuple[bool, int, int]:
    won, gain = idiom_game.run_description_challenge_round(idiom, options, str(selected_index + 1))
    if won:
        return True, gain, current_score + gain
    return False, gain, current_score


def parse_difficulty_to_hide_count(choice: str) -> int:
    mapping = {"1": 1, "2": 2, "3": 3}
    if choice not in mapping:
        raise ValueError(f"Unsupported difficulty: {choice}")
    return mapping[choice]


def select_category_pool(idioms: list[idiom_game.Idiom], category: str) -> list[idiom_game.Idiom]:
    if category == "全部":
        return idioms
    return [item for item in idioms if item.category == category]


def validate_single_guess_input(guess: str, idiom_word: str) -> tuple[bool, str]:
    value = guess.strip()
    if not value:
        return False, "输入不能为空。"
    if idiom_word.isascii():
        if not idiom_game._is_pinyin_guess(value):
            return False, "请输入纯字母拼音。"
    elif not value.isalpha():
        return False, "请输入字母或汉字，不要包含数字或特殊字符。"
    if len(value) > len(idiom_word):
        return False, f"输入过长，请输入不超过 {len(idiom_word)} 个字母。"
    return True, ""


def format_learning_feedback(idiom: idiom_game.Idiom) -> str:
    text = f"学习提示：{idiom.description}"
    if idiom.example:
        text += f" 例句：{idiom.example}"
    return text


def format_top5_leaderboard(records: list[tuple[str, int]]) -> str:
    lines = ["===== 当前排行榜 TOP 5 ====="]
    if not records:
        lines.append("暂无记录")
        return "\n".join(lines)
    for idx, (name, score) in enumerate(records, start=1):
        lines.append(f"{idx}. {name} - {score}")
    return "\n".join(lines)


class IdiomGameGtkWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="成语猜猜猜 - GTK版")
        self.set_border_width(12)
        self.set_default_size(640, 420)

        self.idioms = idiom_game.load_idioms(idiom_game.IDIOMS_FILE)
        self.hide_count = 2
        self.player_name = "GTK玩家"
        self.selected_category = "全部"
        self.timed_mode = False
        self.learning_mode = False
        self.high_score = idiom_game.load_high_score(idiom_game.SCORE_FILE)
        self.state = {
            "mode": MODE_SINGLE,
            "substate": "single-ready",
            "score": 0,
            "streak": 0,
            "status": "欢迎来到成语猜猜猜（GTK）",
        }

        self.current_idiom: Optional[idiom_game.Idiom] = None
        self.round_start_time: Optional[float] = None
        self.attempts = 3
        self.used_hint = False
        self._voice_space_pressed = False
        self.battle_state: Optional[dict] = None
        self.battle_scores: dict[str, int] = {}

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(root)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.pack_start(mode_row, False, False, 0)

        single_mode_button = Gtk.Button(label="单人")
        single_mode_button.connect("clicked", self.on_switch_mode, MODE_SINGLE)
        mode_row.pack_start(single_mode_button, False, False, 0)

        battle_mode_button = Gtk.Button(label="双人对战")
        battle_mode_button.connect("clicked", self.on_switch_mode, MODE_BATTLE)
        mode_row.pack_start(battle_mode_button, False, False, 0)

        challenge_mode_button = Gtk.Button(label="挑战")
        challenge_mode_button.connect("clicked", self.on_switch_mode, MODE_CHALLENGE)
        mode_row.pack_start(challenge_mode_button, False, False, 0)

        quit_button = Gtk.Button(label="退出")
        quit_button.connect("clicked", self.on_quit)
        mode_row.pack_start(quit_button, False, False, 0)

        self.global_status_label = Gtk.Label()
        self.global_status_label.set_xalign(0)
        root.pack_start(self.global_status_label, False, False, 0)

        self.mode_stack = Gtk.Stack()
        root.pack_start(self.mode_stack, True, True, 0)

        single_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        single_settings_row_1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        single_panel.pack_start(single_settings_row_1, False, False, 0)

        self.player_name_entry = Gtk.Entry()
        self.player_name_entry.set_placeholder_text("昵称")
        self.player_name_entry.set_text(self.player_name)
        single_settings_row_1.pack_start(Gtk.Label(label="玩家："), False, False, 0)
        single_settings_row_1.pack_start(self.player_name_entry, False, False, 0)

        self.difficulty_combo = Gtk.ComboBoxText()
        self.difficulty_combo.append("1", "简单（隐藏1个字）")
        self.difficulty_combo.append("2", "中等（隐藏2个字）")
        self.difficulty_combo.append("3", "困难（隐藏3个字）")
        self.difficulty_combo.set_active_id("2")
        single_settings_row_1.pack_start(Gtk.Label(label="难度："), False, False, 0)
        single_settings_row_1.pack_start(self.difficulty_combo, False, False, 0)

        self.category_combo = Gtk.ComboBoxText()
        for category in SINGLE_CATEGORY_OPTIONS:
            self.category_combo.append(category, category)
        self.category_combo.set_active_id("全部")
        single_settings_row_1.pack_start(Gtk.Label(label="分类："), False, False, 0)
        single_settings_row_1.pack_start(self.category_combo, False, False, 0)

        single_settings_row_2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        single_panel.pack_start(single_settings_row_2, False, False, 0)

        self.timed_check = Gtk.CheckButton(label="限时模式（30秒）")
        single_settings_row_2.pack_start(self.timed_check, False, False, 0)
        self.learning_check = Gtk.CheckButton(label="学习模式（猜错显示解释/例句）")
        single_settings_row_2.pack_start(self.learning_check, False, False, 0)

        self.info_label = Gtk.Label()
        self.info_label.set_xalign(0)
        single_panel.pack_start(self.info_label, False, False, 0)

        self.desc_label = Gtk.Label()
        self.desc_label.set_xalign(0)
        single_panel.pack_start(self.desc_label, False, False, 0)

        self.word_label = Gtk.Label()
        self.word_label.set_xalign(0)
        single_panel.pack_start(self.word_label, False, False, 0)

        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0)
        single_panel.pack_start(self.status_label, False, False, 0)

        self.high_score_label = Gtk.Label()
        self.high_score_label.set_xalign(0)
        single_panel.pack_start(self.high_score_label, False, False, 0)

        self.guess_entry = Gtk.Entry()
        self.guess_entry.set_placeholder_text("请输入完整成语")
        single_panel.pack_start(self.guess_entry, False, False, 0)

        self.voice_hint_label = Gtk.Label(
            label="语音输入：按住空格说话，松开后自动识别并填入输入框。"
        )
        self.voice_hint_label.set_xalign(0)
        single_panel.pack_start(self.voice_hint_label, False, False, 0)

        single_button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        single_panel.pack_start(single_button_row, False, False, 0)

        submit_button = Gtk.Button(label="提交猜测")
        submit_button.connect("clicked", self.on_submit_guess)
        single_button_row.pack_start(submit_button, False, False, 0)

        new_round_button = Gtk.Button(label="下一局")
        new_round_button.connect("clicked", self.on_new_round)
        single_button_row.pack_start(new_round_button, False, False, 0)

        self.leaderboard_label = Gtk.Label()
        self.leaderboard_label.set_xalign(0)
        self.leaderboard_label.set_line_wrap(True)
        single_panel.pack_start(self.leaderboard_label, False, False, 0)

        battle_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        battle_player_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        battle_panel.pack_start(battle_player_row, False, False, 0)
        battle_player_row.pack_start(Gtk.Label(label="玩家1："), False, False, 0)
        self.battle_player1_entry = Gtk.Entry()
        self.battle_player1_entry.set_text("玩家1")
        battle_player_row.pack_start(self.battle_player1_entry, True, True, 0)
        battle_player_row.pack_start(Gtk.Label(label="玩家2："), False, False, 0)
        self.battle_player2_entry = Gtk.Entry()
        self.battle_player2_entry.set_text("玩家2")
        battle_player_row.pack_start(self.battle_player2_entry, True, True, 0)

        battle_action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        battle_panel.pack_start(battle_action_row, False, False, 0)
        battle_start_button = Gtk.Button(label="开始对战")
        battle_start_button.connect("clicked", self.on_start_battle)
        battle_action_row.pack_start(battle_start_button, False, False, 0)
        battle_next_button = Gtk.Button(label="下一局对战")
        battle_next_button.connect("clicked", self.on_start_battle)
        battle_action_row.pack_start(battle_next_button, False, False, 0)

        self.battle_turn_label = Gtk.Label(label="当前回合：-")
        self.battle_turn_label.set_xalign(0)
        battle_panel.pack_start(self.battle_turn_label, False, False, 0)
        self.battle_desc_label = Gtk.Label(label="释义：-")
        self.battle_desc_label.set_xalign(0)
        battle_panel.pack_start(self.battle_desc_label, False, False, 0)
        self.battle_word_label = Gtk.Label(label="当前成语：-")
        self.battle_word_label.set_xalign(0)
        battle_panel.pack_start(self.battle_word_label, False, False, 0)
        self.battle_label = Gtk.Label(label="状态：请先开始对战。")
        self.battle_label.set_xalign(0)
        battle_panel.pack_start(self.battle_label, False, False, 0)

        battle_guess_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        battle_panel.pack_start(battle_guess_row, False, False, 0)
        self.battle_position_entry = Gtk.Entry()
        self.battle_position_entry.set_placeholder_text("位置(1-N)")
        battle_guess_row.pack_start(self.battle_position_entry, False, False, 0)
        self.battle_char_entry = Gtk.Entry()
        self.battle_char_entry.set_placeholder_text("单个字符")
        battle_guess_row.pack_start(self.battle_char_entry, False, False, 0)
        battle_submit_button = Gtk.Button(label="提交猜测")
        battle_submit_button.connect("clicked", self.on_submit_battle_guess)
        battle_guess_row.pack_start(battle_submit_button, False, False, 0)

        challenge_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.challenge_title_label = Gtk.Label(label="创新模式：释义挑战（3轮）")
        self.challenge_title_label.set_xalign(0)
        challenge_panel.pack_start(self.challenge_title_label, False, False, 0)

        self.challenge_round_label = Gtk.Label(label="点击“开始挑战”开始。")
        self.challenge_round_label.set_xalign(0)
        challenge_panel.pack_start(self.challenge_round_label, False, False, 0)

        self.challenge_desc_label = Gtk.Label(label="")
        self.challenge_desc_label.set_xalign(0)
        challenge_panel.pack_start(self.challenge_desc_label, False, False, 0)

        challenge_options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        challenge_panel.pack_start(challenge_options_box, False, False, 0)
        self.challenge_option_buttons = []
        for idx in range(CHALLENGE_OPTIONS):
            option_btn = Gtk.Button(label=f"{idx + 1}.")
            option_btn.connect("clicked", self.on_challenge_option, idx)
            challenge_options_box.pack_start(option_btn, False, False, 0)
            self.challenge_option_buttons.append(option_btn)

        challenge_action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        challenge_panel.pack_start(challenge_action_row, False, False, 0)

        challenge_start_button = Gtk.Button(label="开始挑战")
        challenge_start_button.connect("clicked", self.on_start_challenge)
        challenge_action_row.pack_start(challenge_start_button, False, False, 0)

        self.challenge_next_button = Gtk.Button(label="下一轮")
        self.challenge_next_button.connect("clicked", self.on_next_challenge_round)
        self.challenge_next_button.set_sensitive(False)
        challenge_action_row.pack_start(self.challenge_next_button, False, False, 0)

        self.challenge_status_label = Gtk.Label(label="规则：每轮显示释义，4选1，答对 +5 分。")
        self.challenge_status_label.set_xalign(0)
        challenge_panel.pack_start(self.challenge_status_label, False, False, 0)

        self.challenge_round_done = 0
        self.challenge_score = 0
        self.challenge_current_idiom: Optional[idiom_game.Idiom] = None
        self.challenge_options: list[str] = []

        self.mode_stack.add_titled(single_panel, MODE_SINGLE, "单人")
        self.mode_stack.add_titled(battle_panel, MODE_BATTLE, "双人对战")
        self.mode_stack.add_titled(challenge_panel, MODE_CHALLENGE, "挑战")

        self.mode_stack.set_visible_child_name(MODE_SINGLE)
        self.connect("key-press-event", self.on_key_press)
        self.connect("key-release-event", self.on_key_release)
        self.update_mode_placeholder_panels()
        self.update_high_score_label()
        self.update_leaderboard_display(idiom_game.load_leaderboard(idiom_game.LEADERBOARD_FILE))
        self.update_global_status()
        self.on_new_round(None)

    def update_global_status(self):
        self.global_status_label.set_text(
            f"模式：{self.state['mode']} | 子状态：{self.state['substate']} | "
            f"总分：{self.state['score']} | 连胜：{self.state['streak']} | {self.state['status']}"
        )

    def update_mode_placeholder_panels(self):
        if self.battle_state is None:
            self.battle_turn_label.set_text("当前回合：-")
            self.battle_desc_label.set_text("释义：等待开始对战。")
            self.battle_word_label.set_text("当前成语：-")
            self.battle_label.set_text("状态：请先填写玩家并点击“开始对战”。")
        else:
            current = get_battle_current_player(self.battle_state)
            self.battle_turn_label.set_text(f"当前回合：{current}")
            self.battle_desc_label.set_text(f"释义：{self.battle_state['idiom'].description}")
            self.battle_word_label.set_text(f"当前成语：{''.join(self.battle_state['display'])}")
            self.battle_label.set_text(f"状态：{self.battle_state['status']}")

    def on_switch_mode(self, _button, target_mode: str):
        self.state = next_mode_state(self.state, target_mode)
        self.mode_stack.set_visible_child_name(target_mode)
        if target_mode == MODE_SINGLE:
            self.on_new_round(None)
        elif target_mode == MODE_BATTLE:
            self.battle_state = None
            self.state["status"] = "请填写玩家并点击“开始对战”。"
            self.update_mode_placeholder_panels()
            self.update_global_status()
        elif target_mode == MODE_CHALLENGE:
            self.start_challenge()
        else:
            self.update_mode_placeholder_panels()
            self.update_global_status()

    def start_challenge(self):
        self.challenge_round_done = 0
        self.challenge_score = 0
        self.state["substate"] = "challenge-playing"
        self.state["status"] = "挑战开始。"
        self.load_challenge_round()
        self.update_global_status()

    def load_challenge_round(self):
        self.challenge_current_idiom, self.challenge_options = build_description_challenge_round(self.idioms)
        round_no = self.challenge_round_done + 1
        self.challenge_round_label.set_text(f"第 {round_no}/{CHALLENGE_ROUNDS} 轮")
        self.challenge_desc_label.set_text(f"释义：{self.challenge_current_idiom.description}")
        for idx, button in enumerate(self.challenge_option_buttons):
            button.set_label(f"{idx + 1}. {self.challenge_options[idx]}")
            button.set_sensitive(True)
        self.challenge_next_button.set_sensitive(False)
        self.challenge_status_label.set_text(
            f"请选择答案。挑战得分：{self.challenge_score} | 总分：{self.state['score']}"
        )

    def on_start_challenge(self, _button):
        if self.state["mode"] != MODE_CHALLENGE:
            return
        self.start_challenge()

    def on_challenge_option(self, _button, selected_index: int):
        if (
            self.state["mode"] != MODE_CHALLENGE
            or self.state["substate"] != "challenge-playing"
            or self.challenge_current_idiom is None
        ):
            return
        won, gain, self.challenge_score = evaluate_description_challenge_choice(
            self.challenge_current_idiom, self.challenge_options, selected_index, self.challenge_score
        )
        if won:
            self.state["score"] += gain
        self.challenge_round_done += 1
        for button in self.challenge_option_buttons:
            button.set_sensitive(False)

        if won:
            self.challenge_status_label.set_text(
                f"答对了！本轮 +{gain}。挑战得分：{self.challenge_score} | 总分：{self.state['score']}"
            )
        else:
            self.challenge_status_label.set_text(
                f"答错了。正确答案：{self.challenge_current_idiom.word}。"
                f"挑战得分：{self.challenge_score} | 总分：{self.state['score']}"
            )

        if self.challenge_round_done < CHALLENGE_ROUNDS:
            self.state["substate"] = "challenge-round-complete"
            self.state["status"] = f"第 {self.challenge_round_done} 轮已完成。"
            self.challenge_next_button.set_sensitive(True)
        else:
            self.finish_challenge()
        self.update_mode_placeholder_panels()
        self.update_global_status()

    def on_next_challenge_round(self, _button):
        if self.state["mode"] != MODE_CHALLENGE or self.challenge_round_done >= CHALLENGE_ROUNDS:
            return
        self.state["substate"] = "challenge-playing"
        self.state["status"] = f"第 {self.challenge_round_done + 1} 轮开始。"
        self.load_challenge_round()
        self.update_global_status()

    def finish_challenge(self):
        self.state["substate"] = "challenge-finished"
        self.state["status"] = f"挑战结束，3轮得分：{self.challenge_score}"
        self.challenge_round_label.set_text("挑战结束")
        self.challenge_desc_label.set_text("")
        self.challenge_next_button.set_sensitive(False)
        idiom_game.save_game_record(
            idiom_game.RECORD_FILE,
            self.player_name,
            "challenge-gtk",
            self.challenge_score > 0,
            0.0,
            self.challenge_score,
        )
        board = idiom_game.update_leaderboard(
            idiom_game.LEADERBOARD_FILE, self.player_name, self.challenge_score
        )
        top_line = f"排行榜第1名：{board[0][0]} {board[0][1]}分" if board else "排行榜暂无记录。"
        self.challenge_status_label.set_text(f"{self.state['status']}。{top_line}")

    def _elapsed_seconds(self) -> float:
        if self.round_start_time is None:
            return 0.0
        return max(0.0, time.monotonic() - self.round_start_time)

    def _build_round_status_text(self) -> str:
        text = f"剩余机会：{self.attempts} | 当前总分：{self.state['score']}"
        if self.timed_mode:
            left = max(0, 30 - int(self._elapsed_seconds()))
            text += f" | 剩余时间：{left} 秒"
        return text

    def update_high_score_label(self):
        self.high_score_label.set_text(f"当前历史最高分：{self.high_score}")

    def update_leaderboard_display(self, board: list[tuple[str, int]]):
        self.leaderboard_label.set_text(format_top5_leaderboard(board))

    def _update_high_score_if_needed(self):
        if self.state["score"] > self.high_score:
            self.high_score = self.state["score"]
            idiom_game.save_high_score(idiom_game.SCORE_FILE, self.high_score)
            self.update_high_score_label()

    def _save_single_round_record(self, won: bool):
        idiom_game.save_game_record(
            idiom_game.RECORD_FILE,
            self.player_name,
            "single-gtk",
            won,
            self._elapsed_seconds(),
            self.state["score"],
        )

    def on_start_battle(self, _button):
        if self.state["mode"] != MODE_BATTLE:
            return
        idiom = random.choice(self.idioms)
        self.battle_state = create_battle_round_state(
            idiom, self.battle_player1_entry.get_text(), self.battle_player2_entry.get_text()
        )
        self.state["substate"] = "battle-playing"
        self.state["status"] = "双人对战开始。"
        self.battle_position_entry.set_text("")
        self.battle_char_entry.set_text("")
        self.update_mode_placeholder_panels()
        self.update_global_status()

    def on_submit_battle_guess(self, _button):
        if self.state["mode"] != MODE_BATTLE or self.battle_state is None:
            return
        self.battle_state = apply_battle_turn(
            self.battle_state,
            self.battle_position_entry.get_text(),
            self.battle_char_entry.get_text(),
        )
        self.battle_position_entry.set_text("")
        self.battle_char_entry.set_text("")
        if self.battle_state["finished"]:
            self.state["substate"] = "battle-round-finished"
            self.battle_scores, winner_entry = resolve_battle_winner_score(
                self.battle_scores, self.battle_state["winner"], self.battle_state["winner_score"]
            )
            if winner_entry is None:
                self.state["status"] = "对战结束：平局。"
            else:
                winner, total_score = winner_entry
                self.state["score"] += self.battle_state["winner_score"]
                self.state["status"] = f"对战结束：{winner} 获胜，本局 +{self.battle_state['winner_score']}。"
                idiom_game.update_leaderboard(idiom_game.LEADERBOARD_FILE, winner, total_score)
        else:
            self.state["substate"] = "battle-playing"
            self.state["status"] = self.battle_state["status"]
        self.update_mode_placeholder_panels()
        self.update_global_status()

    def on_new_round(self, _button):
        if self.state["mode"] != MODE_SINGLE:
            return
        self.player_name = self.player_name_entry.get_text().strip() or "GTK玩家"
        self.hide_count = parse_difficulty_to_hide_count(self.difficulty_combo.get_active_id() or "2")
        self.selected_category = self.category_combo.get_active_id() or "全部"
        self.timed_mode = self.timed_check.get_active()
        self.learning_mode = self.learning_check.get_active()
        round_pool = select_category_pool(self.idioms, self.selected_category)
        if not round_pool:
            self.state["status"] = "该分类暂无成语，请切换分类。"
            self.info_label.set_text(self.state["status"])
            self.update_global_status()
            return
        self.current_idiom = random.choice(round_pool)
        self.round_start_time = time.monotonic()
        self.attempts = 3
        self.used_hint = False
        self.state["substate"] = "single-playing"
        self.state["status"] = "新的一局开始。"
        masked = idiom_game.mask_word(self.current_idiom.word, self.hide_count)
        self.desc_label.set_text(f"分类：{self.current_idiom.category} | 释义：{self.current_idiom.description}")
        self.word_label.set_text(f"题面：{masked}")
        self.status_label.set_text(self._build_round_status_text())
        self.guess_entry.set_text("")
        self.info_label.set_text(self.state["status"])
        self.update_mode_placeholder_panels()
        self.update_global_status()

    def on_submit_guess(self, _button):
        if self.state["mode"] != MODE_SINGLE or self.current_idiom is None:
            return
        guess = self.guess_entry.get_text().strip()
        is_valid, validation_message = validate_single_guess_input(guess, self.current_idiom.word)
        if not is_valid:
            self.info_label.set_text(validation_message)
            self.state["status"] = validation_message
            self.update_global_status()
            return
        if self.timed_mode and self._elapsed_seconds() > 30:
            self.state["streak"] = 0
            self.state["substate"] = "single-round-lost"
            self.state["status"] = "超时！本局失败。"
            self.info_label.set_text(self.state["status"])
            self.status_label.set_text(self._build_round_status_text())
            self._save_single_round_record(False)
            board = idiom_game.update_leaderboard(
                idiom_game.LEADERBOARD_FILE, self.player_name, self.state["score"]
            )
            self.update_leaderboard_display(board)
            self.update_mode_placeholder_panels()
            self.update_global_status()
            return
        if guess == self.current_idiom.word:
            gain = 10 - (2 if self.used_hint else 0)
            self.state["score"] += gain
            self.state["streak"] += 1
            bonus = ""
            if self.state["streak"] % 3 == 0:
                self.state["score"] += 5
                bonus = " 连胜奖励 +5。"
            self.state["substate"] = "single-round-won"
            self.state["status"] = f"恭喜猜对！本局 +{gain}。{bonus}"
            self.status_label.set_text(self._build_round_status_text())
            self.info_label.set_text(self.state["status"])
            self._save_single_round_record(True)
            self._update_high_score_if_needed()
            board = idiom_game.update_leaderboard(
                idiom_game.LEADERBOARD_FILE, self.player_name, self.state["score"]
            )
            self.update_leaderboard_display(board)
            self.update_mode_placeholder_panels()
            self.update_global_status()
            return

        self.attempts -= 1
        if self.attempts > 0:
            hint_msg = "猜错了。"
            if self.attempts == 2 and not self.used_hint:
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text="是否使用提示（显示最后一个字，扣2分）？",
                )
                response = dialog.run()
                dialog.destroy()
                if response == Gtk.ResponseType.YES:
                    self.used_hint = True
                    hint_msg += f" 提示：最后一个字是“{self.current_idiom.word[-1]}”。"
            elif self.attempts == 1:
                if len(self.current_idiom.word) >= 2:
                    hint_msg += f" 提示：第二个字是“{self.current_idiom.word[1]}”。"
                else:
                    hint_msg += f" 提示：唯一的字是“{self.current_idiom.word[0]}”。"
            if self.learning_mode:
                hint_msg += f" {format_learning_feedback(self.current_idiom)}"
            self.info_label.set_text(hint_msg)
            self.state["status"] = hint_msg
            self.state["substate"] = "single-playing"
            self.status_label.set_text(self._build_round_status_text())
            self.update_global_status()
            return

        self.state["streak"] = 0
        self.state["substate"] = "single-round-lost"
        self.state["status"] = f"本局失败。正确答案：{self.current_idiom.word}"
        if self.learning_mode:
            self.state["status"] += f" {format_learning_feedback(self.current_idiom)}"
        self.info_label.set_text(self.state["status"])
        self.status_label.set_text(f"剩余机会：0 | 当前总分：{self.state['score']}")
        self._save_single_round_record(False)
        board = idiom_game.update_leaderboard(idiom_game.LEADERBOARD_FILE, self.player_name, self.state["score"])
        self.update_leaderboard_display(board)
        self.update_mode_placeholder_panels()
        self.update_global_status()

    def on_key_press(self, _widget, event):
        if getattr(event, "keyval", None) != 32:
            return False
        if self.state["mode"] != MODE_SINGLE:
            return False
        if self._voice_space_pressed:
            return True
        self._voice_space_pressed = True
        voice_text, reason = idiom_game.VOICE_ENGINE.transcribe_while_space_held()
        normalized, status = resolve_gtk_voice_guess_result(voice_text, reason)
        self.info_label.set_text(status)
        self.state["status"] = status
        if normalized is not None:
            self.guess_entry.set_text(normalized)
            self.guess_entry.grab_focus()
            self.guess_entry.set_position(-1)
        self.update_global_status()
        self._voice_space_pressed = False
        return True

    def on_key_release(self, _widget, event):
        if getattr(event, "keyval", None) != 32:
            return False
        self._voice_space_pressed = False
        return True

    def on_quit(self, _button):
        self.close()


def main():
    window = IdiomGameGtkWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
