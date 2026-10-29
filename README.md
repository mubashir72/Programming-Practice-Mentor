# Programming Practice Mentor

An agentic programming-practice prototype with persistent learner memory. The mentor retrieves an exercise, evaluates a submission, diagnoses the evidence, writes progress, and selects the next action based on the learner's history.

The prototype supports Python, JavaScript, C++, C, Java, Kotlin, C#, Dart, and R in learner profiles and the exercise catalog. Python is currently the executable language; the other languages remain selectable but require dedicated evaluator containers before code execution is enabled.

## Quick start

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. The default SQLite database makes the demo runnable without PostgreSQL. For PostgreSQL, set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL.

3. Optionally add `LLM_API_KEY` and set `LLM_MODEL`. With an LLM key, the validated mentor decision selects the next action (`retrieve_targeted_exercise`, `retrieve_follow_up`, or `increase_difficulty`). The app works without an API key by using a deterministic mentor fallback.

4. Install and start Docker Desktop, then pull the evaluator image:

   ```powershell
   docker pull python:3.12-slim
   ```

   The evaluator runs learner code in a restricted container with no network, a read-only filesystem, a non-root user, memory/CPU/PID limits, a temporary filesystem, and a timeout. Set the `SANDBOX_*` variables in `.env` to adjust these limits.

5. Start the app:

   ```powershell
   uvicorn app.main:app --reload
   ```

6. Open <http://127.0.0.1:8000>.

Run the automated checks with `python -m pytest -q`. The API also supports correcting an approved fact, for example `PUT /api/learners/{id}/facts/skill_level`; the previous value is retained as superseded history.

## Demonstration workflow

Use the same learner for three separate cycles:

1. Create a beginner Python learner and start the first session.
2. Submit an off-by-one solution, such as `range(len(values) + 1)`. The evaluator records the failing evidence and the mentor stores an `off_by_one` error.
3. Start the second session. The previous plan and error profile cause the coordinator to retrieve a targeted `array_bounds` exercise. Submit the same kind of mistake again.
4. Stop and restart FastAPI. Use `Resume saved session` or load the learner from the account. No original exercise or code upload is required because the database stores the checkpoint and history.
5. Complete the third session successfully. The mentor stores improvement and selects a harder exercise or another weak topic.

With `LLM_API_KEY` configured, the audit log records the validated LLM plan and the resulting next action. Without a key, the deterministic fallback follows the same allowed action schema.

## Architecture and tool decisions

The browser calls FastAPI. The coordinator uses these meaningful capabilities:

1. Exercise retrieval from the curated local dataset, filtered by language, topic, difficulty, and the current mentor plan.
2. Code evaluation in the Docker sandbox, producing deterministic test evidence.
3. Mentor diagnosis using the evaluation evidence and prior error categories. The optional LLM returns a structured plan; deterministic validation controls allowed actions.
4. Persistent progress writing for learners, sessions, attempts, errors, feedback, facts, and audit events.
5. Next-exercise selection driven by the validated action: targeted retrieval, follow-up retrieval, or difficulty increase.

The LLM does not calculate test results, authorize access, or write records directly. Deterministic application code performs validation, permissions, database updates, and exercise retrieval.

SQLite is the default authoritative store for the local demonstration. PostgreSQL can be configured with `DATABASE_URL` for deployment, but a PostgreSQL driver must also be installed in the deployment environment.

## Memory design and lifecycle

### Working state

`SessionState` stores the current exercise, session status, bounded `current_plan`, and `checkpoint`. It is written after exercise retrieval and submission evaluation so a session can resume after interruption or restart.

### Long-term memory

The database stores the learner profile, skill level, topic, attempts, evaluator results, error categories, feedback plans, completed actions, and versioned learner facts. These records influence later exercise selection.

### Source knowledge

The curated exercise catalog is local source knowledge. Each exercise has a stable title, language, topic, difficulty, starter code, tests, and target error categories. Exercise retrieval events reference the selected exercise and the action that caused retrieval.

### Lifecycle and access

Records are written during learner creation, exercise retrieval, submission evaluation, and fact correction. They are retrieved when restoring a learner, choosing the next exercise, resuming a session, or loading history. Authenticated Firebase users can access only learners linked to their Firebase UID. Guest practice uses the local demonstration store. Fact corrections create a new version and mark the previous version as superseded; the current version is used for later decisions.

The local SQL database is authoritative for the running prototype. Firestore is an account-linked persistence layer for Firebase history and does not overwrite local evaluator results.

## Assignment evidence

- Meaningful tools: memory read, exercise retrieval, Docker code evaluation, LLM diagnosis, progress write, and next-exercise selection.
- Persistent state: learner profile, sessions, attempts, errors, feedback, and versioned facts.
- Restart: state is loaded from the database, not memory-only state.
- Adaptation: the validated mentor plan and repeated errors change retrieval filters and the next action.
- Retry safety: submissions use an idempotency key and a database uniqueness constraint.
- Inspectability: `/api/learners/{id}/audit` exposes action events, outcomes, plan source, selected actions, and timestamps.
- Controlled execution: Python learner code runs in a restricted Docker container rather than directly on the host.

See `AI_USAGE.md` for the required AI-assistance disclosure.

## Firebase guest and account history

Firebase is optional for local development. To enable it:

1. Create a Firebase project.
2. Enable Anonymous and Email/Password sign-in providers.
3. Create a Firestore database.
4. Add the Firebase web configuration values and a Firebase Admin service-account file to `.env` using the names in `.env.example`.
5. Install the updated requirements and restart the app.

Guests receive an anonymous Firebase user ID. When they create an account, the browser links the email/password credential to that anonymous user, preserving the same history. The backend verifies Firebase ID tokens and writes learner profiles, sessions, attempts, and progress to `users/{uid}` in Firestore. It also retains the local SQL database as the prototype's authoritative store. The `Big Tech Interview Challenges` topic contains tricky interview-style problems such as Two Sum, sliding windows, and interval merging.

Use `Resume saved session` to restore the latest locally saved session and `Load saved history` to retrieve local and Firestore history.
