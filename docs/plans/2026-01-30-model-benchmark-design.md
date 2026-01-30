# Model Benchmark & Auto-Routing Design

**Goal:** Cost optimization - use cheaper models (Haiku) for simple tasks, save Opus for complex ones.

**Approach:** Research first with a benchmarking tool, then implement automatic routing based on empirical data.

**Languages:** Scala, Kotlin

---

## Overview

We're building two components:

1. **Model Benchmark Tool** - CLI that runs identical coding tasks through different Claude models and compares results using automated quality metrics
2. **Prompt Classifier Hook** - Claude Code hook that auto-routes tasks to the appropriate model based on complexity

The benchmark generates empirical data; the classifier uses that data to make routing decisions.

---

## Component 1: Model Benchmark Tool

### Architecture

```
model-benchmark/
├── src/main/scala/
│   ├── Main.scala              # CLI entry point
│   ├── runner/
│   │   ├── BenchmarkRunner.scala    # Orchestrates test execution
│   │   └── ClaudeClient.scala       # API calls to different models
│   ├── tasks/
│   │   ├── Task.scala               # Task definition trait
│   │   └── TaskLoader.scala         # Loads tasks from YAML
│   ├── evaluator/
│   │   ├── Evaluator.scala          # Trait for quality checks
│   │   ├── ScalaEvaluator.scala     # scalafmt, scalafix, tests
│   │   └── KotlinEvaluator.scala    # ktlint, detekt, tests
│   └── reporter/
│       ├── Reporter.scala           # Generates comparison reports
│       └── BlindReview.scala        # Handles close-call reviews
├── tasks/                      # Task definitions
│   ├── scala/
│   │   ├── simple/
│   │   ├── medium/
│   │   └── complex/
│   └── kotlin/
│       ├── simple/
│       ├── medium/
│       └── complex/
└── build.sbt
```

### Task Definition Format

```yaml
# tasks/scala/medium/refactor-option-handling.yaml
name: refactor-option-handling
language: scala
complexity: medium
description: "Refactor nested Option matching to use flatMap/map"

# The prompt sent to Claude
prompt: |
  Refactor this Scala code to eliminate nested pattern matching
  using flatMap, map, and getOrElse:

  ```scala
  def getUserEmail(id: Int): Option[String] = {
    getUser(id) match {
      case Some(user) =>
        user.email match {
          case Some(email) => Some(email)
          case None => None
        }
      case None => None
    }
  }
  ```

# Scaffold code provided (dependencies, helper functions)
scaffold: |
  case class User(name: String, email: Option[String])
  def getUser(id: Int): Option[User] = ???

# Expected behavior for test validation
tests: |
  assert(getUserEmail(1) == Some("test@example.com"))
  assert(getUserEmail(999) == None)

# Quality thresholds (0-100)
thresholds:
  compiles: required        # Must compile
  tests_pass: required      # Must pass tests
  scalafix_score: 80        # Minimum linting score
  wartremover_warnings: 0   # No wartremover issues
```

### Evaluation Pipeline

**Step 1: Extraction**
- Parse the code block from Claude's response
- Combine with scaffold to create compilable file

**Step 2: Compilation (pass/fail)**
- Run `scalac` or `kotlinc`
- If it fails, score = 0, skip remaining steps

**Step 3: Test Execution (pass/fail)**
- Run the defined tests
- If tests fail, score capped at 40 (code works but wrong)

**Step 4: Quality Metrics (0-100 each)**

| Scala | Kotlin |
|-------|--------|
| scalafmt | ktlint |
| scalafix | detekt |
| wartremover | - |

**Step 5: Composite Score**

```scala
def score(result: EvalResult): Int = {
  if (!result.compiles) 0
  else if (!result.testsPass) 40
  else {
    val qualityAvg = result.qualityScores.values.sum / result.qualityScores.size
    40 + (qualityAvg * 0.6).toInt  // 40-100 range
  }
}
```

**Close call threshold:** If two models score within 5 points, flag for blind review.

### CLI Interface

```bash
# Run all tasks in a suite
model-benchmark run --suite scala-all

# Run specific complexity level
model-benchmark run --suite scala-simple --models haiku,sonnet

# Run a single task
model-benchmark run --task scala/medium/refactor-option-handling

# List available tasks
model-benchmark list

# Review close calls from last run
model-benchmark review
```

### Report Output

```markdown
# Benchmark Results - 2026-01-30

## Summary
| Model  | Avg Score | Cost    | Tasks Won |
|--------|-----------|---------|-----------|
| Haiku  | 76%       | $0.12   | 8/20      |
| Sonnet | 84%       | $0.89   | 7/20      |
| Opus   | 91%       | $4.23   | 5/20      |

## Recommendations
- **Simple tasks**: Haiku sufficient (saves ~97% vs Opus)
- **Medium tasks**: Sonnet recommended (quality gap too large for Haiku)
- **Complex tasks**: Opus required

## Close Calls (need blind review)
- scala/medium/pattern-match-refactor (Haiku: 82, Sonnet: 85)

## Full Results
[detailed task-by-task breakdown...]
```

### Blind Review Process

When scores are within 5 points:

```bash
$ model-benchmark review

Close call: scala/medium/pattern-match-refactor
Scores: A=82, B=85

--- Option A ---
def process(items: List[Item]): List[Result] =
  items.flatMap(item => item.value.map(v => Result(v)))

--- Option B ---
def process(items: List[Item]): List[Result] =
  for {
    item <- items
    value <- item.value
  } yield Result(value)

Which is better? [A/B/tie]: _
```

Review storage:
```json
{
  "task": "scala/medium/pattern-match-refactor",
  "options": {"A": "haiku", "B": "sonnet"},
  "choice": "tie",
  "winner": "haiku",
  "reason": "cost"
}
```

Tie goes to cheaper model (Haiku > Sonnet > Opus).

---

## Component 2: Prompt Classifier Hook

### Flow

```
Your prompt → Haiku classifier → "simple" → Haiku handles it
                              → "medium" → Sonnet handles it
                              → "complex" → Opus handles it
```

### Classifier Prompt

```
Based on benchmark data, classify this coding task:
- SIMPLE: single function, formatting, rename, obvious fix
- MEDIUM: multi-file, moderate refactor, standard patterns
- COMPLEX: architecture, concurrency, optimization, design decisions

Task: {user_prompt}

Respond with only: SIMPLE, MEDIUM, or COMPLEX
```

Criteria will be tuned based on benchmark results.

### Display

```
┌─────────────────────────────────────────────────────────┐
│ You: "Refactor this function to use flatMap"            │
├─────────────────────────────────────────────────────────┤
│ 🎯 Classifier: MEDIUM → Using Sonnet                    │
├─────────────────────────────────────────────────────────┤
│ Claude (Sonnet): Here's the refactored code...          │
└─────────────────────────────────────────────────────────┘
```

**Display modes:**

```bash
# Compact (default)
🎯 MEDIUM → Sonnet

# Verbose (--verbose flag or config)
🎯 Task classified as MEDIUM complexity
   Reason: Multi-step refactor with type transformations
   Model: Sonnet (saves $0.14 vs Opus)

# Minimal (config option)
[Sonnet]
```

### Override Capability

```bash
# Force a specific model for this task
/model opus

# Or prefix your prompt
@opus "Refactor this function..."
```

### Logging

```json
// ~/.claude/classifier-log.jsonl
{"timestamp": "...", "prompt_preview": "Refactor this func...", "classification": "MEDIUM", "model": "sonnet", "override": null}
```

Helps spot patterns where the classifier is wrong for tuning.

---

## Implementation Workflow

1. **Build benchmark tool** → run against Scala/Kotlin task suites
2. **Analyze results** → learn where Haiku/Sonnet are sufficient
3. **Tune classifier prompt** → encode thresholds from benchmark data
4. **Build Claude Code hook** → auto-route with display
5. **Deploy and monitor** → review logs, refine over time

---

## Task Suites to Create

| Suite | Count | Examples |
|-------|-------|----------|
| scala-simple | 5-7 | Single function, formatting, rename |
| scala-medium | 5-7 | Multi-step refactor, pattern usage |
| scala-complex | 3-5 | Async/concurrency, architecture |
| kotlin-simple | 5-7 | Single function, formatting, rename |
| kotlin-medium | 5-7 | Multi-step refactor, coroutines basics |
| kotlin-complex | 3-5 | Flow, coroutines, architecture |

---

## Not Included (YAGNI)

- CI integration (add later if needed)
- Code review benchmarks (start with code generation, expand later)
- Skill training benchmarks (expand later)
- Automatic retraining of classifier
