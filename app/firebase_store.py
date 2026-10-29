import json
from datetime import datetime, timezone

from .config import settings

_firestore = None
_auth = None
_initialized = False


def _init() -> None:
    global _firestore, _auth, _initialized
    if _initialized:
        return
    _initialized = True
    if not settings.firebase_project_id:
        return
    try:
        import firebase_admin
        from firebase_admin import auth, credentials, firestore

        if firebase_admin._apps:
            app = firebase_admin.get_app()
        elif settings.firebase_service_account_json:
            app = firebase_admin.initialize_app(credentials.Certificate(json.loads(settings.firebase_service_account_json)))
        elif settings.firebase_service_account_file:
            app = firebase_admin.initialize_app(credentials.Certificate(settings.firebase_service_account_file))
        else:
            return
        _firestore = firestore.client(app)
        _auth = auth
    except Exception as exc:
        print(f"Firebase Admin initialization failed: {type(exc).__name__}: {exc}", flush=True)
        _firestore = None
        _auth = None


def enabled() -> bool:
    _init()
    return _firestore is not None and _auth is not None


def web_config() -> dict:
    return {
        "enabled": bool(settings.firebase_api_key and settings.firebase_project_id and settings.firebase_auth_domain),
        "apiKey": settings.firebase_api_key,
        "authDomain": settings.firebase_auth_domain,
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
        "messagingSenderId": settings.firebase_messaging_sender_id,
        "appId": settings.firebase_app_id,
    }


def verify_token(token: str) -> dict:
    if not enabled():
        raise ValueError("Firebase Admin is not configured")
    return _auth.verify_id_token(token)


def _write(uid: str, collection: str, document: str, data: dict) -> None:
    if not enabled():
        return
    payload = {**data, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        _firestore.collection("users").document(uid).collection(collection).document(str(document)).set(payload, merge=True)
    except Exception:
        # Cloud persistence must not erase a locally completed practice attempt.
        return


def link_learner(uid: str, learner_id: int, profile: dict) -> None:
    _write(uid, "learners", learner_id, {"local_learner_id": learner_id, "profile": profile})


def learner_belongs_to(uid: str, learner_id: int) -> bool:
    if not enabled():
        return True
    try:
        doc = _firestore.collection("users").document(uid).collection("learners").document(str(learner_id)).get()
        return doc.exists
    except Exception:
        return False


def save_session(uid: str, session: dict) -> None:
    _write(uid, "sessions", session["session_id"], session)


def save_attempt(uid: str, attempt: dict) -> None:
    _write(uid, "attempts", attempt["attempt_id"], attempt)


def save_profile(uid: str, profile: dict) -> None:
    _write(uid, "profile", "current", profile)


def load_history(uid: str) -> dict:
    if not enabled():
        return {"sessions": [], "attempts": []}
    base = _firestore.collection("users").document(uid)
    try:
        sessions = [{"id": x.id, **x.to_dict()} for x in base.collection("sessions").stream()]
        attempts = [{"id": x.id, **x.to_dict()} for x in base.collection("attempts").stream()]
        return {"sessions": sessions, "attempts": attempts}
    except Exception:
        return {"sessions": [], "attempts": []}


def load_learners(uid: str) -> list[dict]:
    if not enabled():
        return []
    try:
        base = _firestore.collection("users").document(uid).collection("learners")
        return [{"id": int(x.id), **(x.to_dict().get("profile") or {})} for x in base.stream()]
    except Exception:
        return []
