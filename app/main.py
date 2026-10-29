from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine, get_db
from .evaluator import evaluate_code
from .exercises import EXERCISES
from . import firebase_store
from .config import settings
from .languages import LANGUAGES, SUPPORTED_LANGUAGES
from .mentor import diagnose
from .models import Attempt, ErrorEvent, Exercise, Feedback, Learner, LearnerFact, MemoryEvent, SessionState
from .topics import TOPICS

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Programming Practice Mentor")
bearer = HTTPBearer(auto_error=False)


class LearnerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    language: str = "python"
    skill_level: str = "beginner"
    topic: str = "default"


class SubmitIn(BaseModel):
    session_id: int
    code: str = Field(min_length=1)
    idempotency_key: str | None = None


class FactUpdateIn(BaseModel):
    value: str = Field(min_length=1, max_length=200)


def seed(db: Session) -> None:
    existing = {(x.language, x.title) for x in db.scalars(select(Exercise)).all()}
    db.add_all([Exercise(**item) for item in EXERCISES if (item["language"], item["title"]) not in existing])
    db.commit()


def log_event(db: Session, learner_id: int, event_type: str, payload: dict) -> None:
    db.add(MemoryEvent(learner_id=learner_id, event_type=event_type, payload=payload))


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict | None:
    if not credentials:
        return None
    try:
        user = firebase_store.verify_token(credentials.credentials)
        if user.get("email") and not user.get("email_verified", False):
            raise HTTPException(403, "Please verify your email address before using the mentor")
        return user
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Firebase token verification failed: {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(401, f"Firebase token verification failed: {type(exc).__name__}") from exc


def check_access(user: dict | None, learner_id: int) -> None:
    if user and not firebase_store.learner_belongs_to(user["uid"], learner_id):
        raise HTTPException(403, "This learner profile belongs to another account")


def profile(db: Session, learner_id: int) -> dict:
    learner = db.get(Learner, learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")
    errors = db.scalars(select(ErrorEvent).where(ErrorEvent.learner_id == learner_id).order_by(desc(ErrorEvent.created_at))).all()
    counts: dict[str, int] = {}
    for e in errors:
        counts[e.category] = counts.get(e.category, 0) + 1
    attempts = db.scalars(select(Attempt).where(Attempt.learner_id == learner_id).order_by(desc(Attempt.created_at))).all()
    topic_fact = db.scalar(select(LearnerFact).where(LearnerFact.learner_id == learner_id, LearnerFact.fact_type == "topic", LearnerFact.status == "current").order_by(desc(LearnerFact.version)))
    return {"id": learner.id, "name": learner.name, "language": learner.language, "skill_level": learner.skill_level, "topic": topic_fact.fact_value if topic_fact else "default", "attempts": len(attempts), "error_counts": counts, "recent_errors": [e.category for e in errors[:5]]}


def choose_exercise(db: Session, learner: Learner) -> Exercise:
    p = profile(db, learner.id)
    session = db.scalar(select(SessionState).where(SessionState.learner_id == learner.id).order_by(desc(SessionState.updated_at)))
    plan = session.current_plan if session and session.current_plan else {}
    action = plan.get("recommended_action") or plan.get("action")
    weak = max(p["error_counts"], key=p["error_counts"].get, default=None)
    query = select(Exercise).where(Exercise.language == learner.language)
    exercises = db.scalars(query).all()
    if p["topic"] != "default":
        selected = [e for e in exercises if e.topic == p["topic"]]
        if selected:
            exercises = selected
    if action == "retrieve_targeted_exercise":
        target_topic = plan.get("target_topic")
        targeted = [e for e in exercises if e.topic == target_topic or plan.get("error_category") in (e.target_errors or [])]
        if targeted:
            return targeted[p["attempts"] % len(targeted)]
    if action == "increase_difficulty":
        harder = [e for e in exercises if e.difficulty in {"intermediate", "advanced"}]
        if harder:
            return harder[p["attempts"] % len(harder)]
    if action == "retrieve_follow_up":
        follow_up = [e for e in exercises if e.topic == plan.get("target_topic")]
        if follow_up:
            return follow_up[p["attempts"] % len(follow_up)]
    if weak:
        targeted = [e for e in exercises if weak in (e.target_errors or []) or (weak == "off_by_one" and e.topic == "array_bounds")]
        if targeted:
            return targeted[p["attempts"] % len(targeted)]
    preferred = [e for e in exercises if e.difficulty == learner.skill_level]
    return (preferred or exercises)[p["attempts"] % len(preferred or exercises)]


@app.on_event("startup")
def startup() -> None:
    with SessionLocal() as db:
        seed(db)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/auth")
def auth_page():
    return FileResponse(Path(__file__).parent / "static" / "auth.html")


@app.get("/api/firebase-config")
def get_firebase_config():
    return firebase_store.web_config()


@app.get("/api/firebase-status")
def get_firebase_status():
    service_file = settings.firebase_service_account_file
    return {
        "project_configured": bool(settings.firebase_project_id),
        "service_file_configured": bool(service_file),
        "service_file_exists": bool(service_file and Path(service_file).exists()),
        "admin_enabled": firebase_store.enabled(),
    }


@app.get("/api/me")
def get_current_account(user: dict | None = Depends(current_user)):
    if not user:
        return {"authenticated": False, "learners": []}
    return {"authenticated": True, "uid": user["uid"], "email": user.get("email"), "anonymous": user.get("firebase", False) or not user.get("email"), "learners": firebase_store.load_learners(user["uid"])}


@app.post("/api/learners")
def create_learner(payload: LearnerIn, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    if payload.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language: {payload.language}")
    if payload.topic not in TOPICS:
        raise HTTPException(400, f"Unsupported topic: {payload.topic}")
    learner = Learner(name=payload.name, language=payload.language, skill_level=payload.skill_level)
    db.add(learner)
    db.flush()
    db.add(LearnerFact(learner_id=learner.id, fact_type="skill_level", fact_value=learner.skill_level, version=1))
    db.add(LearnerFact(learner_id=learner.id, fact_type="topic", fact_value=payload.topic, version=1))
    log_event(db, learner.id, "learner_created", payload.model_dump())
    db.commit()
    result = profile(db, learner.id)
    if user:
        firebase_store.link_learner(user["uid"], learner.id, result)
        firebase_store.save_profile(user["uid"], result)
    return result


@app.get("/api/learners/{learner_id}")
def get_profile(learner_id: int, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    return profile(db, learner_id)


@app.get("/api/languages")
def get_languages():
    return [{"id": key, **value} for key, value in LANGUAGES.items()]


@app.get("/api/topics")
def get_topics():
    return [{"id": key, "label": value} for key, value in TOPICS.items()]


@app.put("/api/learners/{learner_id}/facts/{fact_type}")
def update_fact(learner_id: int, fact_type: str, payload: FactUpdateIn, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    learner = db.get(Learner, learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")
    previous = db.scalar(select(LearnerFact).where(LearnerFact.learner_id == learner_id, LearnerFact.fact_type == fact_type, LearnerFact.status == "current").order_by(desc(LearnerFact.version)))
    version = (previous.version + 1) if previous else 1
    if previous:
        previous.status = "superseded"
    fact = LearnerFact(learner_id=learner_id, fact_type=fact_type, fact_value=payload.value, version=version, supersedes_id=previous.id if previous else None)
    db.add(fact)
    if fact_type == "skill_level":
        learner.skill_level = payload.value
    log_event(db, learner_id, "fact_corrected", {"fact_type": fact_type, "new_value": payload.value, "superseded_id": previous.id if previous else None})
    db.commit()
    result = profile(db, learner_id)
    if user:
        firebase_store.save_profile(user["uid"], result)
    return result


@app.post("/api/learners/{learner_id}/sessions")
def start_session(learner_id: int, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    learner = db.get(Learner, learner_id)
    if not learner: raise HTTPException(404, "Learner not found")
    exercise = choose_exercise(db, learner)
    session = SessionState(learner_id=learner_id, exercise_id=exercise.id, current_plan={"action": "evaluate_code"}, checkpoint={"exercise_id": exercise.id})
    db.add(session)
    previous = db.scalar(select(SessionState).where(SessionState.learner_id == learner_id).order_by(desc(SessionState.updated_at)))
    prior_plan = previous.current_plan if previous and previous.current_plan else {}
    log_event(db, learner_id, "exercise_retrieved", {
        "exercise_id": exercise.id,
        "topic": exercise.topic,
        "based_on_action": prior_plan.get("recommended_action") or prior_plan.get("action") or "initial_retrieval",
    })
    db.commit()
    result = {"session_id": session.id, "exercise": {"id": exercise.id, "title": exercise.title, "description": exercise.description, "starter_code": exercise.starter_code, "topic": exercise.topic, "difficulty": exercise.difficulty}}
    if user:
        firebase_store.save_session(user["uid"], result)
    return result


@app.get("/api/learners/{learner_id}/resume")
def resume_session(learner_id: int, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    session = db.scalar(select(SessionState).where(SessionState.learner_id == learner_id).order_by(desc(SessionState.updated_at)))
    if not session or not session.exercise_id:
        return {"found": False}
    exercise = db.get(Exercise, session.exercise_id)
    return {"found": True, "session_id": session.id, "status": session.status, "exercise": {"id": exercise.id, "title": exercise.title, "description": exercise.description, "starter_code": exercise.starter_code, "topic": exercise.topic, "difficulty": exercise.difficulty}, "checkpoint": session.checkpoint}


@app.post("/api/submissions")
def submit(payload: SubmitIn, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    session = db.get(SessionState, payload.session_id)
    if not session: raise HTTPException(404, "Session not found")
    check_access(user, session.learner_id)
    existing = db.scalar(select(Attempt).where(Attempt.learner_id == session.learner_id, Attempt.idempotency_key == (payload.idempotency_key or ""))) if payload.idempotency_key else None
    if existing:
        return build_submission_response(db, existing)
    exercise = db.get(Exercise, session.exercise_id)
    result = evaluate_code(exercise.language, payload.code, exercise.tests)
    attempt = Attempt(learner_id=session.learner_id, session_id=session.id, exercise_id=exercise.id, code=payload.code, result=result, idempotency_key=payload.idempotency_key or str(uuid4()))
    db.add(attempt)
    db.flush()
    prior = db.scalars(select(ErrorEvent).where(ErrorEvent.learner_id == session.learner_id).order_by(desc(ErrorEvent.created_at))).all()
    plan, source = diagnose(result, [x.category for x in prior])
    if plan["error_category"] != "none":
        db.add(ErrorEvent(learner_id=session.learner_id, attempt_id=attempt.id, category=plan["error_category"], topic=plan["target_topic"], confidence=0.8, evidence=result.get("message", "failing test result")))
    db.add(Feedback(attempt_id=attempt.id, text=plan["feedback"], plan=plan))
    session.current_plan = plan
    session.status = "completed"
    session.checkpoint = {"attempt_id": attempt.id, "evaluation": result}
    log_event(db, session.learner_id, "submission_evaluated", {"attempt_id": attempt.id, "result": result, "diagnosis_source": source, "next_action": plan["recommended_action"]})
    db.commit()
    response = build_submission_response(db, attempt)
    if user:
        firebase_store.save_attempt(user["uid"], response)
        firebase_store.save_profile(user["uid"], response["profile"])
    return response


def build_submission_response(db: Session, attempt: Attempt) -> dict:
    feedback = db.scalar(select(Feedback).where(Feedback.attempt_id == attempt.id))
    return {"attempt_id": attempt.id, "result": attempt.result, "feedback": feedback.text if feedback else "", "plan": feedback.plan if feedback else {}, "profile": profile(db, attempt.learner_id)}


@app.get("/api/learners/{learner_id}/audit")
def audit(learner_id: int, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    events = db.scalars(select(MemoryEvent).where(MemoryEvent.learner_id == learner_id).order_by(desc(MemoryEvent.created_at))).all()
    return [{"type": x.event_type, "payload": x.payload, "timestamp": x.created_at.isoformat()} for x in events]


@app.get("/api/learners/{learner_id}/history")
def history(learner_id: int, db: Session = Depends(get_db), user: dict | None = Depends(current_user)):
    check_access(user, learner_id)
    local = db.scalars(select(Attempt).where(Attempt.learner_id == learner_id).order_by(desc(Attempt.created_at))).all()
    result = {"local_attempts": [{"id": x.id, "result": x.result, "created_at": x.created_at.isoformat()} for x in local], "cloud": {"sessions": [], "attempts": []}}
    if user:
        result["cloud"] = firebase_store.load_history(user["uid"])
    return result
