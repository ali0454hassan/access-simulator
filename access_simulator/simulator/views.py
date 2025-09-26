from django.shortcuts import render

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

# Room rules dictionary
rooms = {
    "ServerRoom": {"min_level": 2, "open": "09:00", "close": "11:00", "cooldown": 15},
    "Vault": {"min_level": 3, "open": "09:00", "close": "10:00", "cooldown": 30},
    "R&D Lab": {"min_level": 1, "open": "08:00", "close": "12:00", "cooldown": 10},
}

def parse_time(time_str):
    """
    Parse HH:MM into a datetime.time represented as a datetime (same day).
    We use datetime.strptime to make comparisons easy.
    """
    return datetime.strptime(time_str, "%H:%M")

def index(request):
    """Render the frontend page (index.html)"""
    return render(request, "index.html")

@csrf_exempt  # for development only: avoids CSRF token handling
def simulate_access(request):
    """
    Accept POST with JSON body: a list of employee request objects.
    Returns JSON list of results with granted(boolean) and reason.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": "Invalid JSON", "details": str(e)}, status=400)

    results = []
    last_access = {}  # track last access per (employee_id || room)

    for emp in payload:
        emp_id = emp.get("id")
        emp_level = emp.get("access_level")
        room = emp.get("room")
        req_time_str = emp.get("request_time")

        # basic validation
        if not (emp_id and (emp_level is not None) and room and req_time_str):
            results.append({
                "id": emp_id,
                "room": room,
                "time": req_time_str,
                "granted": False,
                "reason": "Denied: Missing required fields"
            })
            continue

        # unknown room
        if room not in rooms:
            results.append({
                "id": emp_id,
                "room": room,
                "time": req_time_str,
                "granted": False,
                "reason": f'Denied: Unknown room "{room}"'
            })
            continue

        rule = rooms[room]

        # Rule 1: access level
        if emp_level < rule["min_level"]:
            results.append({
                "id": emp_id,
                "room": room,
                "time": req_time_str,
                "granted": False,
                "reason": f"Denied: Below required level ({emp_level} < {rule['min_level']})"
            })
            continue

        # parse request time
        try:
            req_time = parse_time(req_time_str)
        except Exception:
            results.append({
                "id": emp_id,
                "room": room,
                "time": req_time_str,
                "granted": False,
                "reason": "Denied: Invalid request_time format (expected HH:MM)"
            })
            continue

        open_time = parse_time(rule["open"])
        close_time = parse_time(rule["close"])

        # Rule 2: open/close
        if not (open_time <= req_time <= close_time):
            results.append({
                "id": emp_id,
                "room": room,
                "time": req_time_str,
                "granted": False,
                "reason": f"Denied: Room closed at {req_time_str} (open {rule['open']}–{rule['close']})"
            })
            continue

        # Rule 3: cooldown check (per employee per room)
        key = f"{emp_id}||{room}"
        if key in last_access:
            diff_min = (req_time - last_access[key]).total_seconds() / 60
            if diff_min < rule["cooldown"]:
                results.append({
                    "id": emp_id,
                    "room": room,
                    "time": req_time_str,
                    "granted": False,
                    "reason": f"Denied: Cooldown active (last at {last_access[key].strftime('%H:%M')}; need {rule['cooldown']} min)"
                })
                continue

        # If all checks pass -> grant
        results.append({
            "id": emp_id,
            "room": room,
            "time": req_time_str,
            "granted": True,
            "reason": f"Access granted to {room}"
        })
        # update last access timestamp
        last_access[key] = req_time

    return JsonResponse(results, safe=False)
