import os
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple


IDIOMS_FILE = "idioms.txt"
SCORE_FILE = "score.txt"
LEADERBOARD_FILE = "leaderboard.txt"


@dataclass
class Idiom:
    word: str
    description: str
    category: str
    example: str = ""


DEFAULT_IDIOMS = [
    Idiom("画蛇添足", "比喻做事多此一举，反而坏事", "寓言", "你已经完成任务了，还反复改，真是画蛇添足。"),
    Idiom("掩耳盗铃", "比喻自己欺骗自己，以为别人不知道", "寓言", "明明事实摆在眼前，他还在掩耳盗铃。"),
    Idiom("守株待兔", "比喻不主动努力，而存侥幸心理", "寓言", "学习不能守株待兔，要主动练习。"),
    Idiom("井底之蛙", "比喻眼界狭窄，见识短浅的人", "动物", "如果只看眼前，就容易成为井底之蛙。"),
    Idiom("对牛弹琴", "比喻说话不看对象，徒劳无功", "动物", "给他讲高级算法就像对牛弹琴。"),
    Idiom("亡羊补牢", "比喻出了差错及时补救，还不算晚", "动物", "现在开始复习还来得及，算是亡羊补牢。"),
    Idiom("狐假虎威", "比喻依仗别人的势力欺压人", "动物", "他仗着后台作威作福，简直狐假虎威。"),
    Idiom("叶公好龙", "比喻表面上喜欢，实际并不喜欢", "人物", "他说喜欢编程，却从不写代码，真是叶公好龙。"),
    Idiom("愚公移山", "比喻坚持不懈改造自然", "人物", "做项目要有愚公移山的精神。"),
    Idiom("自相矛盾", "比喻言行前后抵触", "寓言", "你的前后说法不一致，明显自相矛盾。"),
]


def safe_input(prompt: str, choices=None) -> str:
    while True:
        value = input(prompt).strip()
        if not value:
            print("输入不能为空，请重新输入。")
            continue
        if choices and value not in choices:
            print(f"输入无效，请输入：{'/'.join(choices)}")
            continue
        return value


def parse_int_in_range(text: str, low: int, high: int) -> Optional[int]:
    value = text.strip()
    if not value.isdigit():
        return None
    number = int(value)
    if number < low or number > high:
        return None
    return number


def safe_int_input(prompt: str, low: int, high: int) -> int:
    while True:
        raw = safe_input(prompt)
        parsed = parse_int_in_range(raw, low, high)
        if parsed is not None:
            return parsed
        print(f"请输入 {low}-{high} 范围内的数字。")


def normalize_single_char_input(text: str) -> Optional[str]:
    value = text.strip()
    if len(value) != 1:
        return None
    return value


def safe_single_char_input(prompt: str) -> str:
    while True:
        raw = safe_input(prompt)
        normalized = normalize_single_char_input(raw)
        if normalized is not None:
            return normalized
        print("请只输入一个字符（支持中文）。")


def load_idioms(path: str) -> List[Idiom]:
    if not os.path.exists(path):
        print(f"未找到 {path}，将使用内置成语库。")
        return DEFAULT_IDIOMS

    idioms = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) < 3:
                    print(f"第 {line_no} 行格式错误，已跳过：{line}")
                    continue
                word, description, category = parts[0].strip(), parts[1].strip(), parts[2].strip()
                example = parts[3].strip() if len(parts) >= 4 else ""
                if not word or not description or not category:
                    print(f"第 {line_no} 行存在空字段，已跳过。")
                    continue
                idioms.append(Idiom(word, description, category, example))
    except OSError as exc:
        print(f"读取 {path} 失败（{exc}），将使用内置成语库。")
        return DEFAULT_IDIOMS

    if not idioms:
        print("文件中没有有效成语数据，将使用内置成语库。")
        return DEFAULT_IDIOMS
    return idioms


def load_high_score(path: str) -> int:
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except ValueError:
        print(f"{path} 内容无效，最高分将重置为 0。")
        return 0
    except OSError as exc:
        print(f"读取 {path} 失败（{exc}），最高分将重置为 0。")
        return 0


def save_high_score(path: str, score: int) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(score))
    except OSError as exc:
        print(f"保存最高分失败（{exc}）。")


def parse_leaderboard_line(line: str) -> Optional[Tuple[str, int]]:
    line = line.strip()
    if not line or ":" not in line:
        return None
    name, score_text = line.split(":", 1)
    name = name.strip()
    score_text = score_text.strip()
    if not name:
        return None
    try:
        return name, int(score_text)
    except ValueError:
        return None


def load_leaderboard(path: str) -> list[Tuple[str, int]]:
    if not os.path.exists(path):
        return []
    records: list[Tuple[str, int]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, raw in enumerate(f, start=1):
                parsed = parse_leaderboard_line(raw)
                if parsed is None:
                    print(f"排行榜第 {idx} 行格式无效，已跳过。")
                    continue
                records.append(parsed)
    except OSError as exc:
        print(f"读取排行榜失败（{exc}），将按空榜处理。")
        return []
    records.sort(key=lambda item: item[1], reverse=True)
    return records[:5]


def save_leaderboard(path: str, records: list[Tuple[str, int]]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            for name, score in records[:5]:
                f.write(f"{name}:{score}\n")
    except OSError as exc:
        print(f"保存排行榜失败（{exc}）。")


def update_leaderboard(path: str, player_name: str, score: int) -> list[Tuple[str, int]]:
    records = load_leaderboard(path)
    records.append((player_name, score))
    records.sort(key=lambda item: item[1], reverse=True)
    records = records[:5]
    save_leaderboard(path, records)
    return records


def print_leaderboard(records: list[Tuple[str, int]]) -> None:
    print("\n===== 当前排行榜 TOP 5 =====")
    if not records:
        print("暂无记录")
        return
    for idx, (name, score) in enumerate(records, start=1):
        print(f"{idx}. {name} - {score}")


def mask_word(word: str, hide_count: int) -> str:
    hide_count = min(hide_count, len(word))
    hidden_positions = set(random.sample(range(len(word)), hide_count))
    return "".join("_" if i in hidden_positions else ch for i, ch in enumerate(word))


def choose_difficulty() -> int:
    print("\n请选择难度：")
    print("1. 简单（隐藏1个字）")
    print("2. 中等（隐藏2个字）")
    print("3. 困难（隐藏3个字）")
    difficulty = safe_input("输入 1/2/3：", {"1", "2", "3"})
    return {"1": 1, "2": 2, "3": 3}[difficulty]


def choose_category(idioms: List[Idiom]) -> str:
    categories = sorted({i.category for i in idioms})
    print("\n请选择分类：")
    print("0. 全部")
    for idx, c in enumerate(categories, start=1):
        print(f"{idx}. {c}")
    choices = {"0"} | {str(i) for i in range(1, len(categories) + 1)}
    selected = safe_input("输入编号：", choices)
    if selected == "0":
        return "全部"
    return categories[int(selected) - 1]


def ask_yes_no(prompt: str) -> bool:
    return safe_input(prompt, {"y", "Y", "n", "N"}).lower() == "y"


def choose_mode() -> str:
    print("\n请选择模式：")
    print("1. 单人模式")
    print("2. 双人对战模式")
    print("3. 创新模式（释义挑战）")
    mode = safe_input("输入 1/2/3：", {"1", "2", "3"})
    if mode == "1":
        return "single"
    if mode == "2":
        return "battle"
    return "challenge"


def play_round(idioms: List[Idiom], hide_count: int, timed_mode: bool, learning_mode: bool) -> tuple[bool, bool]:
    idiom = random.choice(idioms)
    attempts = 3
    used_hint = False
    display = mask_word(idiom.word, hide_count)
    start = time.monotonic()

    print("\n========================================")
    print("              猜成语游戏")
    print("========================================")
    print(f"分类：{idiom.category}")
    print(f"提示：{idiom.description}")
    print(f"当前成语：{display}")
    if timed_mode:
        print("限时模式：本局 30 秒。")

    while attempts > 0:
        if timed_mode:
            elapsed = time.monotonic() - start
            left = 30 - int(elapsed)
            if elapsed > 30:
                print("\n超时！本局失败。")
                break
            print(f"\n剩余机会：{attempts}，剩余时间：{left} 秒")
        else:
            print(f"\n剩余机会：{attempts}")

        guess = safe_input("请输入完整成语：")
        if guess == idiom.word:
            print("恭喜你，猜对了！")
            return True, used_hint

        attempts -= 1
        if attempts > 0:
            print("猜错了。")
            if attempts == 2 and not used_hint and ask_yes_no("是否使用提示（显示第一个字，扣2分）？(y/n)："):
                print(f"提示：第一个字是“{idiom.word[0]}”")
                used_hint = True
            if learning_mode:
                print(f"学习提示：{idiom.description}")
                if idiom.example:
                    print(f"例句：{idiom.example}")

    print(f"\n正确答案：{idiom.word}")
    print(f"解释：{idiom.description}")
    if idiom.example:
        print(f"例句：{idiom.example}")
    return False, used_hint


def run_single_mode(idioms: List[Idiom]) -> None:
    high_score = load_high_score(SCORE_FILE)
    print("欢迎来到成语猜猜猜（Python版）")
    print(f"当前历史最高分：{high_score}")
    player_name = safe_input("请输入你的昵称：")

    hide_count = choose_difficulty()
    timed_mode = ask_yes_no("是否开启限时模式（30秒）？(y/n)：")
    learning_mode = ask_yes_no("是否开启学习模式（猜错显示解释/例句）？(y/n)：")

    score = 0
    streak = 0
    while True:
        chosen_category = choose_category(idioms)
        round_pool = idioms if chosen_category == "全部" else [i for i in idioms if i.category == chosen_category]
        if not round_pool:
            print("该分类暂无成语，请重新选择。")
            continue

        won, used_hint = play_round(round_pool, hide_count, timed_mode, learning_mode)
        if won:
            gain = 10 - (2 if used_hint else 0)
            score += gain
            streak += 1
            print(f"本局得分：{gain}，当前总分：{score}")
            if streak % 3 == 0:
                score += 5
                print("连续猜对3局，奖励 +5 分！")
                print(f"当前总分：{score}")
        else:
            streak = 0
            print(f"本局失败，当前总分：{score}")

        board = update_leaderboard(LEADERBOARD_FILE, player_name, score)
        print_leaderboard(board)

        if not ask_yes_no("\n再玩一局？(y/n)："):
            break

    print(f"\n游戏结束，你的最终得分：{score}")
    if score > high_score:
        save_high_score(SCORE_FILE, score)
        print(f"恭喜！你打破了最高分记录：{score}")
    else:
        print(f"历史最高分仍为：{high_score}")


def apply_battle_guess(word: str, display: list[str], position: int, ch: str) -> bool:
    if len(ch) != 1:
        return False
    if position < 0 or position >= len(word):
        return False
    if display[position] != "_":
        return False
    if word[position] == ch:
        display[position] = ch
        return True
    return False


def is_word_revealed(word: str, display: list[str]) -> bool:
    return "".join(display) == word


def play_battle_mode(idioms: List[Idiom]) -> Tuple[Optional[str], int]:
    player1 = safe_input("请输入玩家1姓名：")
    player2 = safe_input("请输入玩家2姓名：")
    idiom = random.choice(idioms)
    word = idiom.word
    display = ["_"] * len(word)
    players = [player1, player2]
    turn = 0
    max_turns = len(word) * 4

    print("\n========================================")
    print("           双人对战：猜成语")
    print("========================================")
    print(f"分类：{idiom.category}")
    print(f"提示：{idiom.description}")

    for _ in range(max_turns):
        current = players[turn % 2]
        print(f"\n当前成语：{''.join(display)}")
        print(f"{current} 的回合")
        pos = safe_int_input(f"请输入位置(1-{len(word)})：", 1, len(word)) - 1
        guess_char = safe_single_char_input("请输入你猜的一个字：")

        if apply_battle_guess(word, display, pos, guess_char):
            print("猜对了！")
            if is_word_revealed(word, display):
                print(f"{current} 率先拼出完整成语，获胜！")
                print(f"答案：{word}")
                return current, 10
        else:
            print("猜错了，或该位置已揭示/无效。")
        turn += 1

    print("\n达到回合上限，本局平局。")
    print(f"答案：{word}")
    return None, 0


def run_description_challenge_round(idiom: Idiom, options: list[str], choice_text: str) -> Tuple[bool, int]:
    selected = parse_int_in_range(choice_text, 1, len(options))
    if selected is None:
        return False, 0
    picked = options[selected - 1]
    if picked == idiom.word:
        return True, 5
    return False, 0


def play_description_challenge_mode(idioms: List[Idiom]) -> Tuple[str, int]:
    player_name = safe_input("请输入你的昵称：")
    score = 0
    rounds = 3
    print("\n========================================")
    print("         创新模式：释义挑战")
    print("========================================")
    print("规则：每轮显示释义，4选1猜成语，答对 +5 分。")

    for idx in range(1, rounds + 1):
        idiom = random.choice(idioms)
        options = [idiom.word]
        while len(options) < 4:
            candidate = random.choice(idioms).word
            if candidate not in options:
                options.append(candidate)
        random.shuffle(options)

        print(f"\n第 {idx} 轮")
        print(f"释义：{idiom.description}")
        for i, item in enumerate(options, start=1):
            print(f"{i}. {item}")
        choice = safe_input("请选择答案编号：")
        won, gain = run_description_challenge_round(idiom, options, choice)
        if won:
            score += gain
            print(f"答对了！本轮 +{gain} 分，当前分数：{score}")
        else:
            print(f"答错了。正确答案：{idiom.word}，当前分数：{score}")

    print(f"\n挑战结束，你的得分：{score}")
    return player_name, score


def main() -> None:
    random.seed()
    idioms = load_idioms(IDIOMS_FILE)
    mode = choose_mode()
    if mode == "single":
        run_single_mode(idioms)
    elif mode == "battle":
        winner, score = play_battle_mode(idioms)
        if winner:
            board = update_leaderboard(LEADERBOARD_FILE, winner, score)
            print_leaderboard(board)
    else:
        player_name, score = play_description_challenge_mode(idioms)
        board = update_leaderboard(LEADERBOARD_FILE, player_name, score)
        print_leaderboard(board)


if __name__ == "__main__":
    main()
