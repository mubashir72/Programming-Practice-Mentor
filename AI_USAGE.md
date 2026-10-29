# AI Usage Disclosure

## Purpose

AI assistance was used as a development aid while building the Programming Practice Mentor prototype. The student remains responsible for understanding, testing, modifying, and demonstrating the complete system.

## AI-assisted work

AI assistance was used for:

- Translating the assignment brief into an implementation plan.
- Designing the persistent-memory schema.
- Drafting FastAPI, SQLAlchemy, evaluator, and frontend code.
- Suggesting test scenarios and retry/idempotency handling.
- Reviewing the workflow against the assignment requirements.
- Drafting setup documentation and this disclosure.

## Human decisions and verification

The project scope, tool boundaries, memory fields, recurring-error demonstration, and safety limitations were reviewed and selected for this assignment. The implementation must be tested locally using the documented three-cycle workflow. The student should inspect and be able to explain every submitted file, especially the coordinator, evaluator, database models, and memory update rules.

## External services and sources

- The LLM integration uses an OpenAI-compatible third-party API configured through environment variables.
- The exercise content is local sample data created for this prototype.
- No API key is included in source code, documentation, logs, or submitted files.

## Limitations

The prototype evaluator uses a timed subprocess. It is suitable for a local demonstration but is not a production-grade security sandbox. A production deployment should isolate code execution in a container or microVM and enforce network, filesystem, process, CPU, and memory restrictions.
