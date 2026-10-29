import ast
import json
import shutil
import subprocess
import sys

from .config import settings


RUNNER = r'''
import json, sys
namespace = {}
code = json.loads(sys.stdin.readline())
tests = json.loads(sys.stdin.readline())
try:
    exec(code, {"__builtins__": __builtins__}, namespace)
    outcomes = []
    for t in tests:
        args = eval(t["input"], {"__builtins__": __builtins__}, namespace)
        if not isinstance(args, tuple): args = (args,)
        fn = next((v for k, v in namespace.items() if callable(v) and not k.startswith("__")), None)
        actual = fn(*args)
        outcomes.append({"expected": t["expected"], "actual": actual, "passed": actual == t["expected"]})
    print(json.dumps({"passed": all(x["passed"] for x in outcomes), "tests": outcomes}))
except Exception as exc:
    print(json.dumps({"passed": False, "kind": "runtime_error", "message": str(exc), "tests": []}))
'''


def _parse_result(stdout: str, stderr: str) -> dict:
    try:
        return json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"passed": False, "kind": "evaluator_error", "message": stderr[-500:], "tests": []}


def evaluate_python(code: str, tests: list[dict], timeout_seconds: int | None = None) -> dict:
    """Evaluate code in a restricted container; never execute learner code on the host by default."""
    timeout_seconds = timeout_seconds or settings.sandbox_timeout_seconds
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return {"passed": False, "kind": "syntax_error", "message": str(exc), "tests": []}

    if settings.sandbox_mode != "docker":
        return {"passed": False, "kind": "sandbox_not_enabled", "message": "Docker sandbox mode is required for code execution.", "tests": []}
    if not shutil.which("docker"):
        return {"passed": False, "kind": "sandbox_unavailable", "message": "Docker is not installed or is not available on PATH.", "tests": []}
    command = [
        "docker", "run", "--rm", "--network", "none",
        "--memory", settings.sandbox_memory, "--cpus", settings.sandbox_cpus,
        "--pids-limit", "64", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", "1000:1000",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        settings.sandbox_image, "python", "-I", "-c", RUNNER,
    ]
    try:
        proc = subprocess.run(
            command,
            input=json.dumps(code) + "\n" + json.dumps(tests) + "\n",
            text=True, capture_output=True, timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "kind": "timeout", "message": "Execution exceeded the time limit.", "tests": []}
    if proc.returncode != 0:
        return {"passed": False, "kind": "sandbox_error", "message": proc.stderr[-500:] or "Sandbox exited unsuccessfully.", "tests": []}
    return _parse_result(proc.stdout, proc.stderr)


def evaluate_code(language: str, code: str, tests: list[dict]) -> dict:
    """Dispatch safely; non-Python execution requires an isolated sandbox."""
    if language == "python":
        return evaluate_python(code, tests)
    return {
        "passed": False,
        "kind": "runtime_unavailable",
        "message": f"{language} is registered and selectable, but its evaluator is disabled until an isolated container or microVM is configured.",
        "tests": [],
    }
