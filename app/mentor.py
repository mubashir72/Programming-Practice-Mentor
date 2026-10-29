import json

from openai import OpenAI

from .config import settings


def deterministic_diagnosis(result: dict, repeated_categories: list[str]) -> dict:
    if result.get("passed"):
        return {
            "error_category": "none",
            "feedback": "All provided tests passed. Review the solution once more, then try a more difficult exercise.",
            "recommended_action": "increase_difficulty",
            "target_topic": "progression",
            "difficulty_adjustment": "up",
        }
    message = (result.get("message") or "").lower()
    if result.get("kind") == "syntax_error": category = "syntax_error"
    elif result.get("kind") == "timeout": category = "performance_or_infinite_loop"
    elif "index" in message or "range" in message: category = "off_by_one"
    else: category = repeated_categories[0] if repeated_categories else "incorrect_logic"
    repeated = category in repeated_categories
    action = "retrieve_targeted_exercise" if repeated or category == "off_by_one" else "retrieve_follow_up"
    return {
        "error_category": category,
        "feedback": f"The submission did not pass all tests. Focus on {category.replace('_', ' ')} and use the failing test result to trace the behavior.",
        "recommended_action": action,
        "target_topic": "array_bounds" if category == "off_by_one" else "debugging",
        "difficulty_adjustment": "same",
    }


def diagnose(result: dict, repeated_categories: list[str]) -> tuple[dict, str]:
    fallback = deterministic_diagnosis(result, repeated_categories)
    if not settings.llm_api_key:
        return fallback, "deterministic_fallback"
    try:
        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=30.0,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": "Return JSON only with keys error_category, feedback, recommended_action, target_topic, difficulty_adjustment. Allowed actions: retrieve_targeted_exercise, retrieve_follow_up, increase_difficulty."},
                {"role": "user", "content": json.dumps({"evaluation": result, "repeated_categories": repeated_categories})},
            ],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1).replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start:end + 1] if start >= 0 and end > start else raw)
        if parsed.get("recommended_action") not in {"retrieve_targeted_exercise", "retrieve_follow_up", "increase_difficulty"}:
            return fallback, "validated_fallback"
        # Evaluator evidence has priority over a broad LLM label. This keeps
        # the memory and exercise selector stable when the model says only
        # "runtime_error" for a specific indexing failure.
        evidence = (result.get("message") or "").lower()
        if result.get("kind") == "runtime_error" and ("index" in evidence or "range" in evidence):
            parsed["error_category"] = "off_by_one"
            parsed["target_topic"] = "array_bounds"
            parsed["recommended_action"] = "retrieve_targeted_exercise"
        return {**fallback, **parsed}, "llm"
    except Exception:
        return fallback, "llm_error_fallback"
