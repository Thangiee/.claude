# Model Benchmark Tool - Implementation Plan (Python)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI that benchmarks Claude models on Scala/Kotlin code tasks and skill behavior tests.

**Architecture:** Python CLI using typer, httpx for API calls, pyyaml for task loading. Shells out to scalac/kotlinc for code evaluation. Uses regex + optional Haiku calls for skill behavior checks.

**Tech Stack:** Python 3.11+, typer, httpx, pyyaml, pytest

---

## Task 1: Project Setup

**Files:**
- Create: `model-benchmark/pyproject.toml`
- Create: `model-benchmark/benchmark/__init__.py`
- Create: `model-benchmark/benchmark/cli.py`

**Step 1: Create project directory**

```bash
mkdir -p ~/projects/model-benchmark/benchmark
cd ~/projects/model-benchmark
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "model-benchmark"
version = "0.1.0"
description = "Benchmark Claude models on coding tasks"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "httpx>=0.25.0",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[project.scripts]
model-benchmark = "benchmark.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 3: Create benchmark/__init__.py**

```python
"""Model benchmark tool for comparing Claude models."""
```

**Step 4: Create minimal CLI**

```python
# benchmark/cli.py
import typer

app = typer.Typer(help="Benchmark Claude models on coding tasks")

@app.command()
def run(
    suite: str = typer.Option(None, help="Task suite to run"),
    task: str = typer.Option(None, help="Single task to run"),
    models: str = typer.Option("haiku,sonnet,opus", help="Models to test"),
):
    """Run benchmark tasks."""
    typer.echo(f"Running suite={suite} task={task} models={models}")

@app.command()
def list():
    """List available tasks."""
    typer.echo("Listing tasks...")

@app.command()
def review():
    """Review close calls from last run."""
    typer.echo("Review mode...")

if __name__ == "__main__":
    app()
```

**Step 5: Install and verify**

```bash
pip install -e ".[dev]"
model-benchmark --help
```

Expected: Shows CLI help with run, list, review commands

**Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: initialize Python project with CLI skeleton"
```

---

## Task 2: Domain Models

**Files:**
- Create: `model-benchmark/benchmark/models.py`
- Create: `model-benchmark/tests/test_models.py`

**Step 1: Write failing test**

```python
# tests/test_models.py
from benchmark.models import Model, EvalResult

def test_score_zero_when_not_compiles():
    result = EvalResult(
        task_name="test",
        model=Model.HAIKU,
        compiles=False,
        tests_pass=False,
        quality_scores={},
        raw_output="",
        extracted_code=None,
        cost=0.001,
    )
    assert result.score == 0

def test_score_40_when_tests_fail():
    result = EvalResult(
        task_name="test",
        model=Model.HAIKU,
        compiles=True,
        tests_pass=False,
        quality_scores={"lint": 80},
        raw_output="",
        extracted_code="code",
        cost=0.001,
    )
    assert result.score == 40

def test_score_includes_quality_when_tests_pass():
    result = EvalResult(
        task_name="test",
        model=Model.HAIKU,
        compiles=True,
        tests_pass=True,
        quality_scores={"lint": 100},
        raw_output="",
        extracted_code="code",
        cost=0.001,
    )
    # 40 + (100 * 0.6) = 100
    assert result.score == 100
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: ImportError

**Step 3: Implement models**

```python
# benchmark/models.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Model(Enum):
    HAIKU = ("claude-3-5-haiku-20241022", 0.001, 0.005)
    SONNET = ("claude-sonnet-4-20250514", 0.003, 0.015)
    OPUS = ("claude-opus-4-20250514", 0.015, 0.075)

    def __init__(self, model_id: str, cost_per_1k_input: float, cost_per_1k_output: float):
        self.model_id = model_id
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output

@dataclass
class Task:
    name: str
    type: str  # "code" or "skill"
    language: str  # "scala", "kotlin", or "skill"
    complexity: str  # "simple", "medium", "complex"
    description: str
    prompt: str
    scaffold: str = ""
    tests: str = ""
    skill_path: str = ""
    checks: list = None
    fuzzy_checks: list = None
    thresholds: dict = None

    def __post_init__(self):
        self.checks = self.checks or []
        self.fuzzy_checks = self.fuzzy_checks or []
        self.thresholds = self.thresholds or {}

@dataclass
class EvalResult:
    task_name: str
    model: Model
    compiles: bool
    tests_pass: bool
    quality_scores: dict[str, int]
    raw_output: str
    extracted_code: Optional[str]
    cost: float

    @property
    def score(self) -> int:
        if not self.compiles:
            return 0
        if not self.tests_pass:
            return 40
        if not self.quality_scores:
            return 100
        quality_avg = sum(self.quality_scores.values()) / len(self.quality_scores)
        return 40 + int(quality_avg * 0.6)

@dataclass
class SkillCheckResult:
    check_type: str
    description: str
    passed: bool
    details: str = ""

@dataclass
class SkillEvalResult:
    task_name: str
    model: Model
    checks: list[SkillCheckResult]
    raw_output: str
    cost: float

    @property
    def score(self) -> int:
        if not self.checks:
            return 0
        passed = sum(1 for c in self.checks if c.passed)
        return int((passed / len(self.checks)) * 100)
```

**Step 4: Run tests**

```bash
pytest tests/test_models.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add domain models with score calculation"
```

---

## Task 3: Task Loader

**Files:**
- Create: `model-benchmark/benchmark/loader.py`
- Create: `model-benchmark/tests/test_loader.py`
- Create: `model-benchmark/tasks/scala/simple/sum-list.yaml`

**Step 1: Write failing test**

```python
# tests/test_loader.py
import tempfile
from pathlib import Path
from benchmark.loader import load_task, load_suite

SAMPLE_YAML = """
name: test-task
type: code
language: scala
complexity: simple
description: Test task
prompt: Write code
scaffold: ""
tests: assert(true)
thresholds:
  compiles: required
"""

def test_load_task_from_yaml():
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(SAMPLE_YAML)
        f.flush()
        task = load_task(Path(f.name))

    assert task.name == "test-task"
    assert task.type == "code"
    assert task.language == "scala"

def test_load_suite():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "task1.yaml").write_text(SAMPLE_YAML)
        (p / "task2.yaml").write_text(SAMPLE_YAML.replace("test-task", "task-2"))

        tasks = load_suite(p)
        assert len(tasks) == 2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_loader.py -v
```

Expected: ImportError

**Step 3: Implement loader**

```python
# benchmark/loader.py
from pathlib import Path
import yaml
from benchmark.models import Task

def load_task(path: Path) -> Task:
    with open(path) as f:
        data = yaml.safe_load(f)

    return Task(
        name=data["name"],
        type=data.get("type", "code"),
        language=data.get("language", "scala"),
        complexity=data.get("complexity", "simple"),
        description=data.get("description", ""),
        prompt=data["prompt"],
        scaffold=data.get("scaffold", ""),
        tests=data.get("tests", ""),
        skill_path=data.get("skill_path", ""),
        checks=data.get("checks", []),
        fuzzy_checks=data.get("fuzzy_checks", []),
        thresholds=data.get("thresholds", {}),
    )

def load_suite(directory: Path) -> list[Task]:
    tasks = []
    for path in directory.glob("*.yaml"):
        tasks.append(load_task(path))
    for path in directory.glob("*.yml"):
        tasks.append(load_task(path))
    return sorted(tasks, key=lambda t: t.name)

def find_suite(name: str, base_dir: Path = Path("tasks")) -> Path:
    """Find suite directory from name like 'scala-simple'."""
    parts = name.split("-", 1)
    if len(parts) == 2:
        return base_dir / parts[0] / parts[1]
    return base_dir / name
```

**Step 4: Run tests**

```bash
pytest tests/test_loader.py -v
```

Expected: All pass

**Step 5: Create sample task**

```yaml
# tasks/scala/simple/sum-list.yaml
name: sum-list
type: code
language: scala
complexity: simple
description: Sum all integers in a list

prompt: |
  Write a Scala function that sums all integers in a list.
  Return 0 for an empty list.

  ```scala
  def sumList(numbers: List[Int]): Int = ???
  ```

scaffold: ""

tests: |
  assert(sumList(List(1, 2, 3)) == 6)
  assert(sumList(List.empty) == 0)
  assert(sumList(List(-1, 1)) == 0)

thresholds:
  compiles: required
  tests_pass: required
```

**Step 6: Commit**

```bash
mkdir -p tasks/scala/simple
git add .
git commit -m "feat: add YAML task loader"
```

---

## Task 4: Claude Client

**Files:**
- Create: `model-benchmark/benchmark/client.py`
- Create: `model-benchmark/tests/test_client.py`

**Step 1: Write failing test**

```python
# tests/test_client.py
from benchmark.client import extract_code, parse_response
from benchmark.models import Model

def test_extract_code_from_scala_block():
    text = """Here's the code:

```scala
def sumList(nums: List[Int]): Int = nums.sum
```

This uses the built-in sum."""

    code = extract_code(text)
    assert code == "def sumList(nums: List[Int]): Int = nums.sum"

def test_extract_code_from_plain_block():
    text = """```
def foo = 1
```"""
    code = extract_code(text)
    assert code == "def foo = 1"

def test_extract_code_returns_none_when_missing():
    assert extract_code("No code here") is None

def test_parse_response():
    json_str = """{
        "content": [{"type": "text", "text": "Hello"}],
        "usage": {"input_tokens": 100, "output_tokens": 50}
    }"""

    text, cost = parse_response(json_str, Model.HAIKU)
    assert text == "Hello"
    assert cost > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_client.py -v
```

Expected: ImportError

**Step 3: Implement client**

```python
# benchmark/client.py
import json
import os
import re
import httpx
from benchmark.models import Model, Task

CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\s*\n([\s\S]*?)\n```")

def extract_code(text: str) -> str | None:
    match = CODE_BLOCK_RE.search(text)
    return match.group(1).strip() if match else None

def parse_response(json_str: str, model: Model) -> tuple[str, float]:
    data = json.loads(json_str)
    text = data["content"][0]["text"]
    usage = data["usage"]
    cost = (
        usage["input_tokens"] * model.cost_per_1k_input +
        usage["output_tokens"] * model.cost_per_1k_output
    ) / 1000
    return text, cost

def call_claude(prompt: str, model: Model, system: str = "") -> tuple[str, float]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    messages = [{"role": "user", "content": prompt}]
    body = {
        "model": model.model_id,
        "max_tokens": 4096,
        "messages": messages,
    }
    if system:
        body["system"] = system

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=body,
        timeout=120,
    )
    response.raise_for_status()
    return parse_response(response.text, model)

def run_task_prompt(task: Task, model: Model) -> tuple[str, float]:
    """Run a task's prompt through Claude and return response + cost."""
    return call_claude(task.prompt, model)
```

**Step 4: Run tests**

```bash
pytest tests/test_client.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Claude API client"
```

---

## Task 5: Code Evaluator (Scala)

**Files:**
- Create: `model-benchmark/benchmark/evaluators/__init__.py`
- Create: `model-benchmark/benchmark/evaluators/scala.py`
- Create: `model-benchmark/tests/test_scala_evaluator.py`

**Step 1: Write failing test**

```python
# tests/test_scala_evaluator.py
import pytest
from benchmark.evaluators.scala import compile_scala, run_scala_tests

def test_compile_valid_scala():
    code = "def add(a: Int, b: Int): Int = a + b"
    assert compile_scala(code) is True

def test_compile_invalid_scala():
    code = "def add(a: Int, b: Int): Int = a + c"  # undefined c
    assert compile_scala(code) is False

def test_run_passing_tests():
    code = "def add(a: Int, b: Int): Int = a + b"
    tests = "assert(add(1, 2) == 3)"
    assert run_scala_tests(code, tests) is True

def test_run_failing_tests():
    code = "def add(a: Int, b: Int): Int = a - b"  # wrong impl
    tests = "assert(add(1, 2) == 3)"
    assert run_scala_tests(code, tests) is False
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_scala_evaluator.py -v
```

Expected: ImportError

**Step 3: Implement Scala evaluator**

```python
# benchmark/evaluators/__init__.py
"""Code evaluators for different languages."""

# benchmark/evaluators/scala.py
import subprocess
import tempfile
from pathlib import Path

def compile_scala(code: str) -> bool:
    """Compile Scala code, return True if successful."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "Code.scala"
        source.write_text(code)

        result = subprocess.run(
            ["scalac", "-d", tmpdir, str(source)],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0

def run_scala_tests(code: str, tests: str) -> bool:
    """Compile and run Scala code with test assertions."""
    full_code = f"""
{code}

@main def runTests(): Unit = {{
  {tests}
  println("TESTS_PASSED")
}}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "Test.scala"
        source.write_text(full_code)

        # Compile
        compile_result = subprocess.run(
            ["scalac", "-d", tmpdir, str(source)],
            capture_output=True,
            timeout=60,
        )
        if compile_result.returncode != 0:
            return False

        # Run
        run_result = subprocess.run(
            ["scala", "-cp", tmpdir, "runTests"],
            capture_output=True,
            timeout=30,
        )
        return b"TESTS_PASSED" in run_result.stdout

def check_scalafmt(code: str) -> int:
    """Check code formatting, return score 0-100."""
    with tempfile.NamedTemporaryFile(suffix=".scala", mode="w", delete=False) as f:
        f.write(code)
        f.flush()

        result = subprocess.run(
            ["scalafmt", "--check", f.name],
            capture_output=True,
        )
        # Simple scoring: 100 if formatted, 70 if not
        return 100 if result.returncode == 0 else 70
```

**Step 4: Run tests**

```bash
pytest tests/test_scala_evaluator.py -v
```

Expected: All pass (requires scalac in PATH)

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Scala evaluator"
```

---

## Task 6: Skill Evaluator

**Files:**
- Create: `model-benchmark/benchmark/evaluators/skill.py`
- Create: `model-benchmark/tests/test_skill_evaluator.py`

**Step 1: Write failing test**

```python
# tests/test_skill_evaluator.py
from benchmark.evaluators.skill import run_check, CheckType

def test_contains_question():
    response = "What error message are you seeing?"
    result = run_check(response, {"type": "contains_question"})
    assert result.passed is True

def test_contains_question_fails():
    response = "Here is the fix for your code."
    result = run_check(response, {"type": "contains_question"})
    assert result.passed is False

def test_mentions_any():
    response = "First, let's reproduce the issue."
    result = run_check(response, {
        "type": "mentions_any",
        "terms": ["reproduce", "replicate"],
    })
    assert result.passed is True

def test_mentions_any_fails():
    response = "Here's the fix."
    result = run_check(response, {
        "type": "mentions_any",
        "terms": ["reproduce", "replicate"],
    })
    assert result.passed is False

def test_not_contains():
    response = "Let me investigate first."
    result = run_check(response, {
        "type": "not_contains",
        "terms": ["just try", "simply"],
    })
    assert result.passed is True

def test_has_section():
    response = "## Root Cause\nThe issue is..."
    result = run_check(response, {
        "type": "has_section",
        "pattern": "(?i)root cause",
    })
    assert result.passed is True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_skill_evaluator.py -v
```

Expected: ImportError

**Step 3: Implement skill evaluator**

```python
# benchmark/evaluators/skill.py
import re
from dataclasses import dataclass
from enum import Enum
from benchmark.models import SkillCheckResult

class CheckType(Enum):
    CONTAINS_QUESTION = "contains_question"
    MENTIONS_ANY = "mentions_any"
    MENTIONS_ALL = "mentions_all"
    NOT_CONTAINS = "not_contains"
    NOT_BEFORE = "not_before"
    HAS_SECTION = "has_section"
    REGEX_MATCH = "regex_match"

def run_check(response: str, check: dict) -> SkillCheckResult:
    """Run a single check against a response."""
    check_type = check["type"]
    description = check.get("description", check_type)

    if check_type == "contains_question":
        # Look for question marks in questioning context
        passed = "?" in response and any(
            q in response.lower()
            for q in ["what", "how", "why", "when", "where", "which", "can you", "could you", "do you"]
        )
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "mentions_any":
        terms = check["terms"]
        response_lower = response.lower()
        passed = any(term.lower() in response_lower for term in terms)
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "mentions_all":
        terms = check["terms"]
        response_lower = response.lower()
        passed = all(term.lower() in response_lower for term in terms)
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "not_contains":
        terms = check["terms"]
        response_lower = response.lower()
        passed = not any(term.lower() in response_lower for term in terms)
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "not_before":
        pattern = check["pattern"]
        before_pattern = check["before_pattern"]
        # Find first occurrence of each
        match_a = re.search(pattern, response, re.IGNORECASE)
        match_b = re.search(before_pattern, response, re.IGNORECASE)
        if match_a is None:
            passed = True  # Pattern A not found, so it's not before B
        elif match_b is None:
            passed = False  # A found but B not found
        else:
            passed = match_b.start() < match_a.start()
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "has_section":
        pattern = check["pattern"]
        passed = re.search(pattern, response, re.IGNORECASE) is not None
        return SkillCheckResult(check_type, description, passed)

    elif check_type == "regex_match":
        pattern = check["pattern"]
        passed = re.search(pattern, response) is not None
        return SkillCheckResult(check_type, description, passed)

    else:
        return SkillCheckResult(check_type, description, False, f"Unknown check type: {check_type}")

def run_all_checks(response: str, checks: list[dict]) -> list[SkillCheckResult]:
    """Run all checks and return results."""
    return [run_check(response, check) for check in checks]
```

**Step 4: Run tests**

```bash
pytest tests/test_skill_evaluator.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add skill behavior evaluator with check types"
```

---

## Task 7: Benchmark Runner

**Files:**
- Create: `model-benchmark/benchmark/runner.py`
- Create: `model-benchmark/tests/test_runner.py`

**Step 1: Write failing test**

```python
# tests/test_runner.py
from benchmark.runner import run_code_task, run_skill_task
from benchmark.models import Model, Task

def test_run_code_task_with_mock():
    task = Task(
        name="test",
        type="code",
        language="scala",
        complexity="simple",
        description="Test",
        prompt="Write hello",
        tests="",
    )

    # Mock client
    def mock_client(prompt, model):
        return "```scala\nprintln(\"hello\")\n```", 0.001

    result = run_code_task(task, Model.HAIKU, client=mock_client)

    assert result.task_name == "test"
    assert result.model == Model.HAIKU
    assert result.extracted_code == 'println("hello")'
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_runner.py -v
```

Expected: ImportError

**Step 3: Implement runner**

```python
# benchmark/runner.py
from pathlib import Path
from typing import Callable
from benchmark.models import Model, Task, EvalResult, SkillEvalResult
from benchmark.client import extract_code, call_claude
from benchmark.evaluators.scala import compile_scala, run_scala_tests, check_scalafmt
from benchmark.evaluators.skill import run_all_checks

ClientFn = Callable[[str, Model], tuple[str, float]]

def run_code_task(
    task: Task,
    model: Model,
    client: ClientFn = None,
) -> EvalResult:
    """Run a code task and evaluate the result."""
    if client is None:
        client = call_claude

    raw_output, cost = client(task.prompt, model)
    extracted_code = extract_code(raw_output)

    if extracted_code is None:
        return EvalResult(
            task_name=task.name,
            model=model,
            compiles=False,
            tests_pass=False,
            quality_scores={},
            raw_output=raw_output,
            extracted_code=None,
            cost=cost,
        )

    # Evaluate based on language
    if task.language == "scala":
        compiles = compile_scala(extracted_code)
        tests_pass = run_scala_tests(extracted_code, task.tests) if compiles and task.tests else False
        quality_scores = {"scalafmt": check_scalafmt(extracted_code)} if compiles else {}
    else:
        # TODO: Add kotlin support
        compiles = False
        tests_pass = False
        quality_scores = {}

    return EvalResult(
        task_name=task.name,
        model=model,
        compiles=compiles,
        tests_pass=tests_pass,
        quality_scores=quality_scores,
        raw_output=raw_output,
        extracted_code=extracted_code,
        cost=cost,
    )

def run_skill_task(
    task: Task,
    model: Model,
    client: ClientFn = None,
) -> SkillEvalResult:
    """Run a skill task and evaluate behavior."""
    if client is None:
        client = call_claude

    # Load skill content if path provided
    system_prompt = ""
    if task.skill_path:
        skill_path = Path(task.skill_path).expanduser()
        if skill_path.exists():
            system_prompt = skill_path.read_text()

    # Run with skill as system prompt
    raw_output, cost = client(task.prompt, model)

    # Run behavior checks
    check_results = run_all_checks(raw_output, task.checks)

    return SkillEvalResult(
        task_name=task.name,
        model=model,
        checks=check_results,
        raw_output=raw_output,
        cost=cost,
    )

def run_task(task: Task, model: Model, client: ClientFn = None):
    """Run a task based on its type."""
    if task.type == "skill":
        return run_skill_task(task, model, client)
    else:
        return run_code_task(task, model, client)

def run_suite(
    tasks: list[Task],
    models: list[Model],
    client: ClientFn = None,
) -> dict[str, list]:
    """Run all tasks with all models."""
    results = {}
    for task in tasks:
        task_results = []
        for model in models:
            print(f"  Running {task.name} with {model.name}...")
            result = run_task(task, model, client)
            task_results.append(result)
        results[task.name] = task_results
    return results
```

**Step 4: Run tests**

```bash
pytest tests/test_runner.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add benchmark runner for code and skill tasks"
```

---

## Task 8: Report Generator

**Files:**
- Create: `model-benchmark/benchmark/reporter.py`
- Create: `model-benchmark/tests/test_reporter.py`

**Step 1: Write failing test**

```python
# tests/test_reporter.py
from benchmark.reporter import generate_report, find_close_calls
from benchmark.models import Model, EvalResult

def test_generate_report_has_summary():
    results = {
        "task1": [
            EvalResult("task1", Model.HAIKU, True, True, {"lint": 90}, "", "code", 0.001),
            EvalResult("task1", Model.OPUS, True, True, {"lint": 95}, "", "code", 0.01),
        ]
    }
    report = generate_report(results)
    assert "## Summary" in report
    assert "Haiku" in report or "HAIKU" in report

def test_find_close_calls():
    results = {
        "task1": [
            EvalResult("task1", Model.HAIKU, True, True, {"lint": 90}, "", "code", 0.001),
            EvalResult("task1", Model.OPUS, True, True, {"lint": 92}, "", "code", 0.01),
        ]
    }
    close = find_close_calls(results, threshold=5)
    assert len(close) == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_reporter.py -v
```

Expected: ImportError

**Step 3: Implement reporter**

```python
# benchmark/reporter.py
from datetime import date
from benchmark.models import Model, EvalResult, SkillEvalResult

def generate_report(results: dict[str, list]) -> str:
    """Generate markdown benchmark report."""
    today = date.today()

    # Calculate summaries
    summaries = calculate_summaries(results)
    close_calls = find_close_calls(results)

    report = f"""# Benchmark Results - {today}

## Summary

| Model | Avg Score | Cost | Tasks Won |
|-------|-----------|------|-----------|
"""
    for s in summaries:
        report += f"| {s['model']} | {s['avg_score']}% | ${s['cost']:.4f} | {s['won']}/{len(results)} |\n"

    report += "\n## Recommendations\n\n"
    if summaries:
        best = summaries[0]
        report += f"- **Best overall**: {best['model']} ({best['avg_score']}% avg)\n"

    report += "\n## Close Calls\n\n"
    if close_calls:
        for name, task_results in close_calls:
            scores = ", ".join(f"{r.model.name}: {r.score}" for r in task_results)
            report += f"- {name} ({scores})\n"
    else:
        report += "None\n"

    report += "\n## Full Results\n\n"
    for name, task_results in sorted(results.items()):
        report += f"### {name}\n\n"
        for r in sorted(task_results, key=lambda x: -x.score):
            report += f"- **{r.model.name}**: {r.score}%\n"
        report += "\n"

    return report

def calculate_summaries(results: dict[str, list]) -> list[dict]:
    """Calculate per-model summary statistics."""
    all_results = [r for task_results in results.values() for r in task_results]
    models = {r.model for r in all_results}

    summaries = []
    for model in models:
        model_results = [r for r in all_results if r.model == model]
        avg_score = sum(r.score for r in model_results) // len(model_results) if model_results else 0
        total_cost = sum(r.cost for r in model_results)

        # Count wins
        won = 0
        for task_results in results.values():
            task_model_results = [r for r in task_results if r.model == model]
            if task_model_results:
                max_score = max(r.score for r in task_results)
                if task_model_results[0].score == max_score:
                    won += 1

        summaries.append({
            "model": model.name,
            "avg_score": avg_score,
            "cost": total_cost,
            "won": won,
        })

    return sorted(summaries, key=lambda x: -x["avg_score"])

def find_close_calls(results: dict[str, list], threshold: int = 5) -> list[tuple[str, list]]:
    """Find tasks where top scores are within threshold."""
    close = []
    for name, task_results in results.items():
        scores = sorted([r.score for r in task_results], reverse=True)
        if len(scores) >= 2 and (scores[0] - scores[1]) <= threshold:
            close.append((name, task_results))
    return close

def save_report(report: str, path: str = None):
    """Save report to file."""
    if path is None:
        path = f"reports/benchmark-{date.today()}.md"
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report)
    return path
```

**Step 4: Run tests**

```bash
pytest tests/test_reporter.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add markdown report generator"
```

---

## Task 9: Wire Up CLI

**Files:**
- Modify: `model-benchmark/benchmark/cli.py`

**Step 1: Update CLI with full implementation**

```python
# benchmark/cli.py
import os
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from benchmark.models import Model
from benchmark.loader import load_task, load_suite, find_suite
from benchmark.runner import run_suite
from benchmark.reporter import generate_report, save_report

app = typer.Typer(help="Benchmark Claude models on coding tasks")
console = Console()

def parse_models(models_str: str) -> list[Model]:
    mapping = {"haiku": Model.HAIKU, "sonnet": Model.SONNET, "opus": Model.OPUS}
    return [mapping[m.strip().lower()] for m in models_str.split(",") if m.strip().lower() in mapping]

@app.command()
def run(
    suite: str = typer.Option(None, "--suite", "-s", help="Task suite (e.g., scala-simple)"),
    task: str = typer.Option(None, "--task", "-t", help="Single task path"),
    models: str = typer.Option("haiku,sonnet,opus", "--models", "-m", help="Models to test"),
):
    """Run benchmark tasks."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
        raise typer.Exit(1)

    model_list = parse_models(models)
    if not model_list:
        console.print("[red]Error: No valid models specified[/red]")
        raise typer.Exit(1)

    # Load tasks
    if suite:
        suite_path = find_suite(suite)
        if not suite_path.exists():
            console.print(f"[red]Suite not found: {suite}[/red]")
            raise typer.Exit(1)
        tasks = load_suite(suite_path)
    elif task:
        task_path = Path(f"tasks/{task}.yaml")
        if not task_path.exists():
            console.print(f"[red]Task not found: {task}[/red]")
            raise typer.Exit(1)
        tasks = [load_task(task_path)]
    else:
        console.print("[red]Specify --suite or --task[/red]")
        raise typer.Exit(1)

    console.print(f"Running {len(tasks)} tasks with {[m.name for m in model_list]}")

    # Run benchmark
    results = run_suite(tasks, model_list)

    # Generate and save report
    report = generate_report(results)
    report_path = save_report(report)

    console.print(f"\n[green]Report saved to: {report_path}[/green]\n")
    console.print(report)

@app.command("list")
def list_tasks():
    """List available tasks."""
    tasks_dir = Path("tasks")
    if not tasks_dir.exists():
        console.print("No tasks directory found")
        return

    table = Table(title="Available Tasks")
    table.add_column("Suite")
    table.add_column("Task")
    table.add_column("Type")

    for yaml_file in sorted(tasks_dir.rglob("*.yaml")):
        relative = yaml_file.relative_to(tasks_dir)
        parts = list(relative.parts)
        suite = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else parts[0]
        name = yaml_file.stem

        task = load_task(yaml_file)
        table.add_row(suite, name, task.type)

    console.print(table)

@app.command()
def review():
    """Review close calls from last run."""
    console.print("[yellow]Review functionality coming soon...[/yellow]")

if __name__ == "__main__":
    app()
```

**Step 2: Test CLI**

```bash
model-benchmark list
model-benchmark run --suite scala-simple --models haiku --help
```

Expected: Shows task list and help

**Step 3: Commit**

```bash
git add .
git commit -m "feat: wire up CLI with run, list commands"
```

---

## Task 10: Add Sample Tasks

**Files:**
- Create: `tasks/scala/simple/reverse-string.yaml`
- Create: `tasks/scala/simple/find-max.yaml`
- Create: `tasks/skills/simple/ask-questions.yaml`

**Step 1: Create code tasks**

```yaml
# tasks/scala/simple/reverse-string.yaml
name: reverse-string
type: code
language: scala
complexity: simple
description: Reverse a string

prompt: |
  Write a Scala function that reverses a string.

  ```scala
  def reverseString(s: String): String = ???
  ```

tests: |
  assert(reverseString("hello") == "olleh")
  assert(reverseString("") == "")
  assert(reverseString("a") == "a")

thresholds:
  compiles: required
  tests_pass: required
```

```yaml
# tasks/scala/simple/find-max.yaml
name: find-max
type: code
language: scala
complexity: simple
description: Find maximum in a list

prompt: |
  Write a Scala function that finds the maximum value in a non-empty list.

  ```scala
  def findMax(numbers: List[Int]): Int = ???
  ```

tests: |
  assert(findMax(List(1, 5, 3)) == 5)
  assert(findMax(List(-1, -5, -3)) == -1)
  assert(findMax(List(42)) == 42)

thresholds:
  compiles: required
  tests_pass: required
```

**Step 2: Create skill task**

```yaml
# tasks/skills/simple/ask-questions.yaml
name: ask-questions
type: skill
language: skill
complexity: simple
description: Test that responses ask clarifying questions

prompt: |
  I have a bug in my code. Can you fix it?

checks:
  - type: contains_question
    description: "Should ask a clarifying question"

  - type: mentions_any
    terms: ["what", "which", "where", "can you", "could you", "more information", "details"]
    description: "Should request more information"

  - type: not_contains
    terms: ["here's the fix", "try this code", "the solution is"]
    description: "Should NOT provide a fix without context"
```

**Step 3: Verify tasks load**

```bash
model-benchmark list
```

Expected: Shows all tasks

**Step 4: Commit**

```bash
mkdir -p tasks/scala/simple tasks/skills/simple
git add .
git commit -m "feat: add sample code and skill tasks"
```

---

## Task 11: End-to-End Test

**Step 1: Set API key**

```bash
export ANTHROPIC_API_KEY="your-key"
```

**Step 2: Run simple benchmark**

```bash
model-benchmark run --suite scala-simple --models haiku
```

Expected: Report generated with scores

**Step 3: Run skill benchmark**

```bash
model-benchmark run --suite skills-simple --models haiku,opus
```

Expected: Report with skill check results

**Step 4: Commit any fixes**

```bash
git add .
git commit -m "fix: adjustments from e2e testing"
```

---

## Summary

**Phase 1 complete when:**
- [ ] All 11 tasks implemented
- [ ] `pytest` passes all tests
- [ ] `model-benchmark run --suite scala-simple` works
- [ ] `model-benchmark run --suite skills-simple` works
- [ ] At least 3 code tasks and 1 skill task exist

**Phase 2 (future):**
- Add Kotlin evaluator
- Add medium/complex task suites
- Implement blind review flow
- Add fuzzy checks with Haiku classifier
