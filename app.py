from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for
import datetime
from zoneinfo import ZoneInfo
import time
import io
import hashlib
import os
import signal
from concurrent.futures import ThreadPoolExecutor

from data_services import get_weather
from config import Config
import todo_service
import learning_service
from lunardate import LunarDate

executor = ThreadPoolExecutor(max_workers=10)

app = Flask(__name__)

# Simple in-memory cache for the /render endpoint
# Format: {"data": bytes, "timestamp": float}
_render_cache = {"data": None, "timestamp": 0}
_consecutive_render_failures = 0
MAX_RENDER_FAILURES = 5

def _clear_render_cache():
    global _render_cache
    _render_cache["data"] = None
    _render_cache["timestamp"] = 0

@app.route('/health')
def health():
    return "OK"

@app.route('/dashboard')
def dashboard():
    # Submit Data Fetch Tasks in Parallel
    future_weather = executor.submit(get_weather)
    try:
        weather = future_weather.result(timeout=10)
    except Exception as e:
        print(f"Weather Timeout: {e}")
        weather = {"current": {"temp": "--"}, "forecast": [], "tomorrow": {}}

    try:
        now = datetime.datetime.now(ZoneInfo(Config.TIMEZONE))
    except Exception:
        now = datetime.datetime.now()

    tomorrow_date = now.date() + datetime.timedelta(days=1)
    lunar = LunarDate.fromSolarDate(now.year, now.month, now.day)
    weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    day_labels = []
    daily_weather = weather.get("daily", [])
    for offset in range(3):
        forecast_date = now.date() + datetime.timedelta(days=offset)
        forecast = daily_weather[offset] if offset < len(daily_weather) else {}
        day_labels.append({
            "label": ["今天", "明天", "后天"][offset],
            "date": forecast_date,
            "weather": forecast.get("desc", "天气暂无"),
            "range": f"{forecast.get('low', '--')}°–{forecast.get('high', '--')}°",
        })
    school = learning_service.get_plan(tomorrow_date)

    return render_template(
        'learning_dashboard.html',
        weather=weather, 
        today=now,
        lunar=f"农历{lunar.month}月{lunar.day}日",
        weekday=weekday_cn[now.weekday()],
        tomorrow_weather=day_labels,
        school=school,
        updated_at=now.strftime("%H:%M"),
        config=Config
    )

@app.route('/school')
def school_page():
    settings = learning_service.get_settings()
    return render_template('school.html', settings=settings, weekdays=learning_service.WEEKDAYS)

@app.route('/api/school', methods=['GET'])
def api_get_school():
    return jsonify({"success": True, **learning_service.get_settings()})

@app.route('/api/school', methods=['POST'])
def api_save_school():
    payload = request.get_json(silent=True) or request.form
    settings = learning_service.save_settings(payload)
    _clear_render_cache()
    return jsonify({"success": True, **settings})

# --- Todo Management Web Page & APIs ---

@app.route('/todos')
@app.route('/tasks')
@app.route('/todo')
def todos_page():
    todos = todo_service.get_todos()
    stats = todo_service.get_stats()
    return render_template('todos.html', todos=todos, stats=stats)

@app.route('/api/todos', methods=['GET'])
def api_get_todos():
    return jsonify({
        "success": True,
        "todos": todo_service.get_todos(),
        "stats": todo_service.get_stats()
    })

@app.route('/api/todos', methods=['POST'])
def api_add_todo():
    data = request.get_json(silent=True) or request.form
    text = data.get('text', '')
    priority = data.get('priority', 'normal')
    new_item = todo_service.add_todo(text, priority)
    if new_item:
        _clear_render_cache()
        return jsonify({
            "success": True, 
            "todo": new_item, 
            "stats": todo_service.get_stats()
        })
    return jsonify({"success": False, "error": "待办内容不能为空"}), 400

@app.route('/api/todos/<todo_id>/toggle', methods=['POST', 'PUT'])
def api_toggle_todo(todo_id):
    item = todo_service.toggle_todo(todo_id)
    if item:
        _clear_render_cache()
        return jsonify({
            "success": True, 
            "todo": item, 
            "stats": todo_service.get_stats()
        })
    return jsonify({"success": False, "error": "待办事项不存在"}), 404

@app.route('/api/todos/<todo_id>', methods=['DELETE', 'POST'])
def api_delete_todo(todo_id):
    ok = todo_service.delete_todo(todo_id)
    if ok:
        _clear_render_cache()
        return jsonify({
            "success": True, 
            "stats": todo_service.get_stats()
        })
    return jsonify({"success": False, "error": "待办事项不存在"}), 404

@app.route('/api/todos/clear-completed', methods=['POST'])
def api_clear_completed():
    todo_service.clear_completed()
    _clear_render_cache()
    return jsonify({
        "success": True, 
        "stats": todo_service.get_stats()
    })

@app.route('/api/cache/clear', methods=['POST', 'GET'])
def api_clear_cache():
    _clear_render_cache()
    return jsonify({"success": True, "message": "Render cache cleared"})

# --- E-ink Render Endpoint ---

@app.route('/render')
@app.route('/render.png')
def render_dashboard():
    from renderer import render_dashboard_to_bytes
    global _render_cache, _consecutive_render_failures
    
    current_time = time.time()
    
    def prepare_response(data, timestamp):
        global _consecutive_render_failures
        _consecutive_render_failures = 0
        
        response = send_file(
            io.BytesIO(data), 
            mimetype='image/png',
            as_attachment=False, 
            download_name='dashboard.png'
        )
        response.headers['Cache-Control'] = f'public, max-age={Config.CACHE_TTL_RENDER}, s-maxage={Config.CACHE_TTL_RENDER}'
        
        last_modified = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
        response.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        etag = hashlib.md5(data).hexdigest()
        response.set_etag(etag)
        return response

    # 1. Check if we have a valid cache
    if _render_cache["data"] and (current_time - _render_cache["timestamp"] < Config.CACHE_TTL_RENDER):
        print(f"Returning cached image (age: {int(current_time - _render_cache['timestamp'])}s)")
        return prepare_response(_render_cache["data"], _render_cache["timestamp"])

    # 2. If not cached, render it
    port = Config.PORT
    dashboard_url = f"http://127.0.0.1:{port}/dashboard"
    
    try:
        image_io = render_dashboard_to_bytes(dashboard_url)
        image_bytes = image_io.getvalue()
        
        # Update Cache
        _render_cache["data"] = image_bytes
        _render_cache["timestamp"] = current_time
        
        return prepare_response(image_bytes, current_time)
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        _consecutive_render_failures += 1
        print(f"Rendering failed. Failure count: {_consecutive_render_failures}/{MAX_RENDER_FAILURES}")
        
        if _consecutive_render_failures >= MAX_RENDER_FAILURES:
             print("CRITICAL: Too many consecutive rendering errors. Restarting container...")
             try:
                 os.kill(1, signal.SIGTERM)
             except PermissionError:
                 print("Could not kill PID 1 (Permission Denied). Killing self instead.")
                 os.kill(os.getpid(), signal.SIGTERM)

        return f"Error rendering dashboard: {e}", 500

if __name__ == '__main__':
    print("Starting app...")
    app.run(debug=True, port=Config.PORT, host=Config.HOST)
