import os
import json
import uuid
import threading
import datetime

DATA_DIR = os.environ.get("TODO_DATA_DIR", "data")
TODO_FILE = os.path.join(DATA_DIR, "todos.json")
_lock = threading.Lock()

DEFAULT_TODOS = [
    {
        "id": "1",
        "text": "欢迎使用 Kindle 看板待办系统",
        "completed": False,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    },
    {
        "id": "2",
        "text": "在电脑或手机浏览器打开 /todos 随时管理待办",
        "completed": False,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    },
    {
        "id": "3",
        "text": "保持专注，享受高效一天",
        "completed": True,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
]

def _ensure_dir():
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception:
            pass

def _load_todos():
    _ensure_dir()
    if not os.path.exists(TODO_FILE):
        _save_todos(DEFAULT_TODOS)
        return DEFAULT_TODOS
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[TodoService] Error loading todos from {TODO_FILE}: {e}")
        return DEFAULT_TODOS

def _save_todos(todos):
    _ensure_dir()
    temp_file = TODO_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, TODO_FILE)
    except Exception as e:
        print(f"[TodoService] Error saving todos to {TODO_FILE}: {e}")
        try:
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                json.dump(todos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def get_todos():
    with _lock:
        return _load_todos()

def add_todo(text, priority="normal"):
    text = (text or "").strip()
    if not text:
        return None
    new_item = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "completed": False,
        "priority": priority,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with _lock:
        todos = _load_todos()
        todos.append(new_item)
        _save_todos(todos)
    return new_item

def toggle_todo(todo_id):
    with _lock:
        todos = _load_todos()
        target = None
        for item in todos:
            if item.get("id") == todo_id:
                item["completed"] = not item.get("completed", False)
                target = item
                break
        if target:
            _save_todos(todos)
        return target

def delete_todo(todo_id):
    with _lock:
        todos = _load_todos()
        initial_len = len(todos)
        todos = [item for item in todos if item.get("id") != todo_id]
        if len(todos) != initial_len:
            _save_todos(todos)
            return True
        return False

def clear_completed():
    with _lock:
        todos = _load_todos()
        todos = [item for item in todos if not item.get("completed", False)]
        _save_todos(todos)
        return True

def get_stats():
    todos = get_todos()
    total = len(todos)
    completed = sum(1 for item in todos if item.get("completed", False))
    pending = total - completed
    return {
        "total": total,
        "completed": completed,
        "pending": pending
    }
