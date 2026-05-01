import json
import re
from uuid import uuid4

from flask import Blueprint, Response, jsonify, render_template, request, session, stream_with_context

from app.models import db
from app.models.recipe import ChatMessage, Recipe
from app.services import ai_service


bp = Blueprint('main', __name__)


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


def _session_id():
    if 'chat_session_id' not in session:
        session['chat_session_id'] = uuid4().hex
        session.modified = True
    return session['chat_session_id']


def _model_history(session_id, limit=30):
    messages = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(messages)
    ]


def _history_with_profile_context(session_id):
    history = _model_history(session_id)
    state = _chef_state(session_id)

    if state.get("profile_complete") and state.get("profile"):
        profile = state["profile"]
        context = (
            "Known returning user profile. Do not ask to confirm these details again unless the user says they changed. "
            f"skill_level={profile.get('skill_level') or 'unknown'}; "
            f"dietary={profile.get('dietary') or 'unknown'}; "
            f"tools={profile.get('tools') or 'unknown'}; "
            f"time_available={profile.get('time_available') or 'unknown'}."
        )
        history.insert(0, {"role": "system", "content": context})

    return history


def _display_history(session_id, limit=100):
    messages = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "role": message.role,
            "content": message.display_content or message.content,
        }
        for message in reversed(messages)
    ]


def _recipe_count(session_id):
    messages = ChatMessage.query.filter_by(session_id=session_id, role='assistant').all()
    count = 0

    for message in messages:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", message.content, re.DOTALL)
        if not json_match:
            continue

        try:
            data = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            continue

        if data.get("stage") == "recipe":
            count += 1

    return count


def _chef_state(session_id):
    message = (
        ChatMessage.query
        .filter_by(session_id=session_id, role='assistant')
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .first()
    )
    if not message:
        return {
            "stage": "profiling",
            "profile": {},
            "profile_complete": False,
            "dish_options": [],
            "selected_title": "",
        }

    json_match = re.search(r"```json\s*(\{.*?\})\s*```", message.content, re.DOTALL)
    if not json_match:
        return {
            "stage": "profiling",
            "profile": {},
            "profile_complete": False,
            "dish_options": [],
            "selected_title": "",
        }

    try:
        data = json.loads(json_match.group(1))
    except json.JSONDecodeError:
        return {
            "stage": "profiling",
            "profile": {},
            "profile_complete": False,
            "dish_options": [],
            "selected_title": "",
        }

    dish_options = data.get("dish_options", []) or []
    for option in dish_options:
        if not option.get("image_url"):
            option["image_url"] = ai_service._photo_url(
                option.get("image_query") or option.get("title") or "recipe"
            )

    return {
        "stage": data.get("stage", "profiling"),
        "profile": data.get("profile_data", {}),
        "profile_complete": data.get("profile_complete", False),
        "dish_options": dish_options,
        "selected_title": data.get("selected_title", ""),
    }


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/start', methods=['POST'])
def start():
    session_id = _session_id()
    history = _display_history(session_id)

    if history:
        state = _chef_state(session_id)
        return jsonify({
            "response": "",
            "messages": history,
            "stage": state["stage"],
            "profile": state["profile"],
            "profile_complete": state["profile_complete"],
            "dish_options": state["dish_options"],
            "selected_title": state["selected_title"],
            "recipe_count": _recipe_count(session_id),
        })

    return jsonify({
        "response": "Hello, I am Chef Big Max. First, what is your cooking skill level: beginner, home cook, or advanced?",
        "messages": [],
        "stage": "profiling",
        "profile": {},
        "dish_options": [],
        "recipe_count": 0,
    })


@bp.route('/reset', methods=['POST'])
def reset():
    session_id = _session_id()
    ChatMessage.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    session.pop('history', None)
    return jsonify({"ok": True})


@bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    selected_option = data.get('selected_option')
    session_id = _session_id()

    result = ai_service.call_chef_service(
        user_message,
        _history_with_profile_context(session_id),
        selected_option,
    )

    if result.get('error'):
        return jsonify({
            "response": result['response'],
            "error": result.get('error'),
            "stage": result.get('stage'),
            "profile": result.get('profile'),
            "dish_options": result.get('dish_options', []),
            "recipe_count": _recipe_count(session_id),
        }), 502

    try:
        db.session.add(ChatMessage(
            session_id=session_id,
            role='user',
            content=user_message,
            display_content=user_message,
        ))
        db.session.add(ChatMessage(
            session_id=session_id,
            role='assistant',
            content=result.get('history_content') or result['response'],
            display_content=result['response'],
        ))

        if result.get('stage') == 'recipe':
            db.session.add(Recipe(
                title=result.get('selected_title') or (selected_option or {}).get('title') or 'Chef Big Max Creation',
                ingredients=user_message,
                recipe_text=result['response'],
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "response": result['response'],
        "error": result.get('error'),
        "stage": result.get('stage'),
        "profile": result.get('profile'),
        "dish_options": result.get('dish_options', []),
        "selected_title": result.get('selected_title'),
        "recipe_count": _recipe_count(session_id),
    })


@bp.route('/chat-stream', methods=['POST'])
def chat_stream():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    selected_option = data.get('selected_option')
    session_id = _session_id()
    history = _history_with_profile_context(session_id)

    @stream_with_context
    def generate():
        final_result = None

        for event in ai_service.stream_chef_service(user_message, history, selected_option):
            event_type = event.get("type")

            if event_type == "delta":
                yield _sse("delta", {"text": event.get("text", "")})

            elif event_type == "error":
                yield _sse("error", {
                    "response": event.get("response", "Streaming error."),
                    "error": event.get("error", "Streaming error."),
                    "stage": event.get("stage", "error"),
                    "recipe_count": _recipe_count(session_id),
                })
                return

            elif event_type == "done":
                final_result = event.get("result") or {}

        if final_result is None:
            yield _sse("error", {
                "response": "The stream ended before Chef Big Max sent a full response.",
                "error": "Empty streaming response.",
                "stage": "error",
                "recipe_count": _recipe_count(session_id),
            })
            return

        try:
            db.session.add(ChatMessage(
                session_id=session_id,
                role='user',
                content=user_message,
                display_content=user_message,
            ))
            db.session.add(ChatMessage(
                session_id=session_id,
                role='assistant',
                content=final_result.get('history_content') or final_result.get('response', ''),
                display_content=final_result.get('response', ''),
            ))

            if final_result.get('stage') == 'recipe':
                db.session.add(Recipe(
                    title=final_result.get('selected_title') or (selected_option or {}).get('title') or 'Chef Big Max Creation',
                    ingredients=user_message,
                    recipe_text=final_result.get('response', ''),
                ))

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            yield _sse("error", {
                "response": f"Database error: {e}",
                "error": str(e),
                "stage": "error",
                "recipe_count": _recipe_count(session_id),
            })
            return

        yield _sse("done", {
            "response": final_result.get('response', ''),
            "stage": final_result.get('stage'),
            "profile": final_result.get('profile'),
            "profile_complete": final_result.get('profile_complete'),
            "dish_options": final_result.get('dish_options', []),
            "selected_title": final_result.get('selected_title'),
            "recipe_count": _recipe_count(session_id),
        })

    return Response(generate(), content_type='text/event-stream; charset=utf-8')
