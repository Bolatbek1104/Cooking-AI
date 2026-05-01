import json
import re
from urllib.parse import quote

import requests
from flask import current_app


_PHOTO_CACHE = {}


def _photo_url(query):
    pexels_url = _pexels_photo_url(query)
    if pexels_url:
        return pexels_url

    return _generated_photo_url(query)


def _pexels_photo_url(query):
    api_key = current_app.config.get("PEXELS_API_KEY")
    if not api_key:
        return None

    search_query = f"{query or 'home cooked meal'} food"
    cache_key = search_query.lower().strip()
    if cache_key in _PHOTO_CACHE:
        return _PHOTO_CACHE[cache_key]

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={
                "query": search_query,
                "per_page": 1,
                "orientation": "landscape",
            },
            timeout=6,
        )
        if response.status_code >= 400:
            return None

        photos = response.json().get("photos") or []
        if not photos:
            return None

        src = photos[0].get("src") or {}
        photo_url = src.get("landscape") or src.get("large") or src.get("medium")
        if photo_url:
            _PHOTO_CACHE[cache_key] = photo_url
        return photo_url
    except requests.RequestException:
        return None


def _generated_photo_url(query):
    dish = query or "home cooked meal"
    prompt = (
        "realistic food photography, finished plated dish, no people, no animals, "
        "restaurant lighting, appetizing, "
        f"{dish}"
    )
    seed = quote(dish)
    return (
        "https://image.pollinations.ai/prompt/"
        f"{quote(prompt)}?width=640&height=480&seed={seed}&nologo=true"
    )


SYSTEM_PROMPT = """
You are Chef Big Max, a professional multilingual cooking assistant.
Your tone must be clear, friendly, respectful, and practical.
Do not use slang, memes, internet jokes, insults, exaggerated personality, or chaotic language.
Avoid phrases such as "yo", "fam", "bro", "sigma", "boy", "let's go", or similar informal slang.

Language rules:
- Detect the user's language from their latest message and reply in that same language.
- If the user mixes languages, reply in the main language they used most recently.
- You can answer in English, Russian, Kazakh, or any other language the user uses.
- Keep dish titles and instructions natural in the chosen language.
- The final JSON keys must always stay in English exactly as specified.

You remember the conversation and follow these stages:

1. Profiling
Before working with ingredients, collect these four details one at a time:
- cooking skill level
- dietary restrictions/allergies
- cooking tools/equipment
- time available
When all four are known, say the profile is ready and ask for all ingredients they have.
If the profile is already complete in the conversation or in a system context message, do not ask these questions again.
Never ask the user to confirm the same profile again unless they explicitly say their profile changed.

2. Dish options
When the user gives ingredients and has a complete profile, do not give a full recipe yet.
Instead, suggest 3 to 5 realistic dish options that can be made mostly from those ingredients.
Each option needs a short title, a one-line description, time, difficulty, and a very specific image_query.
The image_query should be in English and describe the visible finished dish, main ingredient, cuisine/style, and plating.
Ask the user to choose one dish.
Do not suggest dishes that depend on several missing key ingredients unless you clearly say they require extra ingredients.

3. Selected recipe
When the user selects one of the options, give the full recipe for that exact dish.
Adapt steps to their skill level, restrictions, tools, and time.
Include ingredients, step-by-step instructions, timing, substitutions, and a rough nutrition estimate when appropriate.
Use only the ingredients the user said they have as required ingredients.
Common pantry basics such as salt, pepper, water, and a small amount of oil may be suggested as optional if reasonable.
If an ingredient was not mentioned by the user, do not list it as required.
Put missing helpful ingredients in a separate "Optional / if available" section.
If the chosen dish needs an important missing ingredient, either ask one short question or give a simplified version that works without it.

4. Follow-up
After a recipe, help with substitutions, scaling, faster versions, and troubleshooting.
In follow-up, if the user mentions a new ingredient or asks what to do next, immediately answer using the known profile.
Do not ask quick refreshers like "are you still a home cook..." when the profile is already known.

Response style:
- Be concise but complete.
- Use simple headings and short paragraphs.
- Ask only one necessary question at a time.
- Do not over-explain the system or mention internal stages unless helpful to the user.
- When writing recipes, separate ingredients into "Available ingredients" and "Optional / if available" when any extra ingredient is mentioned.

Always put a JSON block at the very end:
```json
{
  "stage": "profiling|profiled|options|recipe|followup",
  "question_asked": "",
  "profile_complete": false,
  "profile_data": {
    "skill_level": "",
    "dietary": "",
    "tools": "",
    "time_available": ""
  },
  "dish_options": [
    {
      "title": "",
      "description": "",
      "time": "",
      "difficulty": "",
      "image_query": ""
    }
  ],
  "selected_title": ""
}
```
Use an empty dish_options array unless stage is "options".
"""


def _build_messages(message, history=None, selected_option=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)

    user_content = (
        f"My ingredients/answer: {message}\n"
        "Treat mentioned ingredients as the user's available ingredients. "
        "Do not assume additional required ingredients unless the user already mentioned them; "
        "list extras only as optional or ask a short question."
    )
    if selected_option:
        user_content += (
            "\nThe user selected this dish option. Give the full recipe for it:\n"
            f"{json.dumps(selected_option, ensure_ascii=False)}"
        )
    messages.append({"role": "user", "content": user_content})
    return messages


def _parse_chef_response(full_content):
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", full_content, re.DOTALL)

    if json_match:
        chef_data = json.loads(json_match.group(1))
        display_text = full_content.split("```json")[0].strip()
    else:
        chef_data = {}
        display_text = full_content.strip()

    dish_options = chef_data.get("dish_options", []) or []
    for option in dish_options:
        if not option.get("image_url"):
            option["image_url"] = _photo_url(option.get("image_query") or option.get("title") or "recipe")

    return {
        "response": display_text,
        "history_content": full_content,
        "stage": chef_data.get("stage", "profiling"),
        "profile": chef_data.get("profile_data", {}),
        "profile_complete": chef_data.get("profile_complete", False),
        "dish_options": dish_options,
        "selected_title": chef_data.get("selected_title", ""),
    }


def call_chef_service(message, history=None, selected_option=None):
    api_key = current_app.config["OPENROUTER_API_KEY"]

    if not api_key:
        return {
            "error": "OPENROUTER_API_KEY is not set. Add it to your .env file or hosting environment variables.",
            "response": "OpenRouter API key is missing. Check your .env file.",
            "stage": "error",
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": _build_messages(message, history, selected_option),
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        try:
            result = response.json()
        except ValueError:
            return {
                "error": f"OpenRouter returned a non-JSON response with status {response.status_code}.",
                "response": "OpenRouter returned an invalid response.",
                "stage": "error",
            }

        if response.status_code >= 400:
            api_error = result.get("error", {})
            message = api_error.get("message", str(api_error)) if isinstance(api_error, dict) else str(api_error)
            return {
                "error": f"OpenRouter error {response.status_code}: {message}",
                "response": f"OpenRouter error {response.status_code}: {message}",
                "stage": "error",
            }

        if "choices" not in result or not result["choices"]:
            return {
                "error": f"OpenRouter response did not include choices: {result}",
                "response": "OpenRouter returned no model response.",
                "stage": "error",
            }

        return _parse_chef_response(result["choices"][0]["message"]["content"])

    except Exception as e:
        print(f"Agent error: {e}")
        return {
            "error": str(e),
            "response": f"Agent error: {e}",
            "stage": "error",
        }


def stream_chef_service(message, history=None, selected_option=None):
    api_key = current_app.config["OPENROUTER_API_KEY"]

    if not api_key:
        yield {
            "type": "error",
            "error": "OPENROUTER_API_KEY is not set. Add it to your .env file or hosting environment variables.",
            "response": "OpenRouter API key is missing. Check your .env file.",
            "stage": "error",
        }
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": _build_messages(message, history, selected_option),
        "temperature": 0.7,
        "stream": True,
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        )

        if response.status_code >= 400:
            yield {
                "type": "error",
                "error": f"OpenRouter error {response.status_code}: {response.text}",
                "response": f"OpenRouter error {response.status_code}.",
                "stage": "error",
            }
            return

        response.encoding = "utf-8"
        full_content = ""
        pending_visible = ""
        suppress_visible = False
        json_marker = "```json"
        marker_tail = len(json_marker) - 1

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue

            data = line.removeprefix("data:").strip()
            if data == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choice = (chunk.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            content = delta.get("content") or ""
            if not content:
                continue

            full_content += content
            if suppress_visible:
                continue

            pending_visible += content
            marker_index = pending_visible.find(json_marker)
            if marker_index != -1:
                visible_text = pending_visible[:marker_index]
                suppress_visible = True
                pending_visible = ""
                if visible_text:
                    yield {"type": "delta", "text": visible_text}
            elif len(pending_visible) > marker_tail:
                visible_text = pending_visible[:-marker_tail]
                pending_visible = pending_visible[-marker_tail:]
                if visible_text:
                    yield {"type": "delta", "text": visible_text}

        if pending_visible and not suppress_visible:
            yield {"type": "delta", "text": pending_visible}

        yield {"type": "done", "result": _parse_chef_response(full_content)}

    except Exception as e:
        print(f"Streaming agent error: {e}")
        yield {
            "type": "error",
            "error": str(e),
            "response": f"Agent error: {e}",
            "stage": "error",
        }
