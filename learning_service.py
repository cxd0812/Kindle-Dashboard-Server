import datetime as dt
import json
import os
import re
import tempfile
import threading
from pathlib import Path

from config import Config
from pypinyin import Style, pinyin

_lock = threading.RLock()
DATA_FILE = Path(Config.TODO_DATA_DIR) / "school.json"

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
DEFAULT_SCHEDULE = {
    "1": ["数学", "语文", "美术", "道德与法治", "体育与健康", "综合实践活动", "少先队活动/心理健康"],
    "2": ["语文", "数学", "语文", "", "音乐", "劳动", ""],
    "3": ["英语", "语文", "科学", "", "语文", "体育与健康", ""],
    "4": ["数学", "语文", "体育与健康", "", "整本书阅读", "语文", "社团课"],
    "5": ["语文", "音乐", "体育与健康", "", "道德与法治", "美术", ""],
    "6": ["", "", "", "", "", "", ""],
    "7": ["", "", "", "", "", "", ""],
}


def _default_data():
    return {"schedule": DEFAULT_SCHEDULE, "plans": {}}


def _read(path=None):
    file_path = Path(path or DATA_FILE)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("School data must be an object")
    except FileNotFoundError:
        data = _default_data()
    except (json.JSONDecodeError, ValueError):
        data = _default_data()
    data.setdefault("schedule", _default_data()["schedule"])
    data.setdefault("plans", {})
    return data


def _write(data, path=None):
    file_path = Path(path or DATA_FILE)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="school-", suffix=".json", dir=file_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, file_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _lines(value):
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").splitlines()
    return [str(item).strip() for item in values if str(item).strip()][:30]


def homework_items(value):
    items = []
    for line in _lines(value):
        if "|" in line:
            reading, text = (part.strip() for part in line.split("|", 1))
        else:
            pinyin_text = re.sub(r"\d+", lambda match: _number_to_chinese(match.group()), line)
            reading = " ".join(syllable[0] for syllable in pinyin(pinyin_text, style=Style.TONE, errors="ignore"))
            text = line
        if text:
            # Keep each reading above its own character, including numeric groups.
            chunks = re.findall(r"\d+|[^\d]", text)
            expanded = [_number_to_chinese(chunk) if chunk.isdigit() else chunk for chunk in chunks]
            syllables = [part[0] for part in pinyin("".join(expanded), style=Style.TONE, errors=lambda chars: list(chars))]
            ruby = []
            offset = 0
            for chunk, spoken in zip(chunks, expanded):
                ruby.append({"text": chunk, "reading": " ".join(syllables[offset:offset + len(spoken)]).strip() if any(c.isalnum() for c in chunk) else ""})
                offset += len(spoken)
            if "|" in line:
                manual = reading.split()
                readable = [part for part in ruby if part["reading"]]
                if len(manual) == len(readable):
                    for part, syllable in zip(readable, manual):
                        part["reading"] = syllable
                else:
                    ruby = []  # Preserve custom readings that cannot be aligned safely.
            items.append({"pinyin": reading, "text": text, "ruby": ruby})
    return items


def _number_to_chinese(value):
    digits = "零一二三四五六七八九"
    number = int(value)
    if number < 10:
        return digits[number]
    if number < 20:
        return "十" + (digits[number % 10] if number % 10 else "")
    if number < 100:
        tens, ones = divmod(number, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    if number < 1000:
        hundreds, remainder = divmod(number, 100)
        result = digits[hundreds] + "百"
        if remainder == 0:
            return result
        if remainder < 10:
            return result + "零" + digits[remainder]
        return result + _number_to_chinese(str(remainder))
    return " ".join(digits[int(digit)] for digit in value)


def tomorrow(today=None):
    return (today or dt.date.today()) + dt.timedelta(days=1)


def get_plan(target_date=None, path=None):
    target = target_date or tomorrow()
    weekday = str(target.isoweekday())
    with _lock:
        data = _read(path)
    subjects = data["schedule"].get(weekday, DEFAULT_SCHEDULE.get(weekday, [""] * 7))
    subjects = (list(subjects) + [""] * 7)[:7]
    if target.isoweekday() == 4 and "社团课" not in subjects:
        subjects[6] = subjects[6] or "社团课"

    plan = data["plans"].get(target.isoformat(), {})
    homework = homework_items(plan.get("homework", []))
    extras = _lines(plan.get("extras", []))
    carry = []
    for subject in subjects:
        if subject in ("语文", "数学"):
            carry.extend((f"{subject}课本", f"{subject}作业"))
        elif subject == "美术":
            carry.append("美术工具")
        elif subject == "社团课" and target.isoweekday() == 4:
            carry.append("尤克里里")
    carry.extend(extras)
    carry = list(dict.fromkeys(carry))
    return {
        "date": target,
        "date_label": f"{target.month}月{target.day}日",
        "weekday": WEEKDAYS[target.isoweekday() - 1],
        "subjects": subjects,
        "homework": homework,
        "carry": carry,
        "extras": extras,
    }


def get_settings(target_date=None, path=None):
    target = target_date or tomorrow()
    with _lock:
        data = _read(path)
    plan = data["plans"].get(target.isoformat(), {})
    schedule = {}
    for day in range(1, 8):
        schedule[str(day)] = (list(data["schedule"].get(str(day), [""] * 7)) + [""] * 7)[:7]
    return {
        "target_date": target.isoformat(),
        "weekday": WEEKDAYS[target.isoweekday() - 1],
        "schedule": schedule,
        "homework": "\n".join(_lines(plan.get("homework", []))),
        "extras": "\n".join(_lines(plan.get("extras", []))),
    }


def save_settings(payload, target_date=None, path=None):
    target = target_date or tomorrow()
    incoming = payload.get("schedule", {})
    schedule = {}
    for day in range(1, 8):
        values = incoming.get(str(day), []) if isinstance(incoming, dict) else []
        if not isinstance(values, list):
            values = []
        schedule[str(day)] = [str(value).strip()[:40] for value in (values + [""] * 7)[:7]]
    with _lock:
        data = _read(path)
        data["schedule"] = schedule
        data.setdefault("plans", {})[target.isoformat()] = {
            "homework": _lines(payload.get("homework", "")),
            "extras": _lines(payload.get("extras", "")),
        }
        _write(data, path)
    return get_settings(target, path)
