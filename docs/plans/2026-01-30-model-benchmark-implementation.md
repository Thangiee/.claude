# Model Benchmark Tool - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that benchmarks Claude models (Haiku, Sonnet, Opus) on Scala coding tasks and generates cost vs quality reports.

**Architecture:** Scala CLI app using sbt, circe for JSON, snakeyaml for YAML, sttp for HTTP. Each task runs through all models, gets compiled/tested/linted, and scored. Results aggregated into markdown report.

**Tech Stack:** Scala 3, sbt, circe, snakeyaml, sttp, scalafix, scalafmt, munit

**Phase 1 Scope:** Scala evaluation only. Kotlin support added in Phase 2.

---

## Task 1: Project Setup

**Files:**
- Create: `model-benchmark/build.sbt`
- Create: `model-benchmark/project/build.properties`
- Create: `model-benchmark/project/plugins.sbt`
- Create: `model-benchmark/.scalafmt.conf`
- Create: `model-benchmark/.scalafix.conf`

**Step 1: Create project directory**

```bash
mkdir -p ~/projects/model-benchmark/project
cd ~/projects/model-benchmark
```

**Step 2: Create build.sbt**

```scala
val scala3Version = "3.3.1"

lazy val root = project
  .in(file("."))
  .settings(
    name := "model-benchmark",
    version := "0.1.0",
    scalaVersion := scala3Version,
    libraryDependencies ++= Seq(
      // CLI
      "com.monovore" %% "decline" % "2.4.1",
      // JSON
      "io.circe" %% "circe-core" % "0.14.6",
      "io.circe" %% "circe-generic" % "0.14.6",
      "io.circe" %% "circe-parser" % "0.14.6",
      // YAML
      "org.yaml" % "snakeyaml" % "2.2",
      // HTTP
      "com.softwaremill.sttp.client3" %% "core" % "3.9.1",
      "com.softwaremill.sttp.client3" %% "circe" % "3.9.1",
      // Testing
      "org.scalameta" %% "munit" % "0.7.29" % Test
    ),
    // For running scalafmt/scalafix on benchmark outputs
    fork := true
  )
```

**Step 3: Create project/build.properties**

```
sbt.version=1.9.7
```

**Step 4: Create project/plugins.sbt**

```scala
addSbtPlugin("org.scalameta" % "sbt-scalafmt" % "2.5.2")
addSbtPlugin("ch.epfl.scala" % "sbt-scalafix" % "0.11.1")
```

**Step 5: Create .scalafmt.conf**

```hocon
version = 3.7.17
runner.dialect = scala3
maxColumn = 100
```

**Step 6: Create .scalafix.conf**

```hocon
rules = [
  OrganizeImports,
  RemoveUnused
]
```

**Step 7: Verify project compiles**

```bash
cd ~/projects/model-benchmark
sbt compile
```

Expected: `[success]`

**Step 8: Commit**

```bash
git init
git add .
git commit -m "chore: initialize sbt project with dependencies"
```

---

## Task 2: Core Domain Models

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/domain/Task.scala`
- Create: `model-benchmark/src/main/scala/benchmark/domain/EvalResult.scala`
- Create: `model-benchmark/src/main/scala/benchmark/domain/Model.scala`
- Create: `model-benchmark/src/test/scala/benchmark/domain/EvalResultTest.scala`

**Step 1: Write failing test for score calculation**

```scala
// src/test/scala/benchmark/domain/EvalResultTest.scala
package benchmark.domain

import munit.FunSuite

class EvalResultTest extends FunSuite {

  test("score is 0 when compilation fails") {
    val result = EvalResult(
      taskName = "test-task",
      model = Model.Haiku,
      compiles = false,
      testsPass = false,
      qualityScores = Map.empty,
      rawOutput = "",
      extractedCode = None,
      cost = 0.001
    )
    assertEquals(result.score, 0)
  }

  test("score is 40 when tests fail") {
    val result = EvalResult(
      taskName = "test-task",
      model = Model.Haiku,
      compiles = true,
      testsPass = false,
      qualityScores = Map("scalafmt" -> 80),
      rawOutput = "",
      extractedCode = Some("code"),
      cost = 0.001
    )
    assertEquals(result.score, 40)
  }

  test("score is 40 + 60% of quality avg when tests pass") {
    val result = EvalResult(
      taskName = "test-task",
      model = Model.Haiku,
      compiles = true,
      testsPass = true,
      qualityScores = Map("scalafmt" -> 100, "scalafix" -> 80),
      rawOutput = "",
      extractedCode = Some("code"),
      cost = 0.001
    )
    // avg = 90, 60% of 90 = 54, 40 + 54 = 94
    assertEquals(result.score, 94)
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error - classes don't exist

**Step 3: Create Model enum**

```scala
// src/main/scala/benchmark/domain/Model.scala
package benchmark.domain

enum Model(val id: String, val costPer1kInput: Double, val costPer1kOutput: Double):
  case Haiku extends Model("claude-3-5-haiku-20241022", 0.001, 0.005)
  case Sonnet extends Model("claude-sonnet-4-20250514", 0.003, 0.015)
  case Opus extends Model("claude-opus-4-20250514", 0.015, 0.075)
```

**Step 4: Create Task case class**

```scala
// src/main/scala/benchmark/domain/Task.scala
package benchmark.domain

case class Task(
    name: String,
    language: String,
    complexity: String,
    description: String,
    prompt: String,
    scaffold: String,
    tests: String,
    thresholds: Map[String, String]
)
```

**Step 5: Create EvalResult with score calculation**

```scala
// src/main/scala/benchmark/domain/EvalResult.scala
package benchmark.domain

case class EvalResult(
    taskName: String,
    model: Model,
    compiles: Boolean,
    testsPass: Boolean,
    qualityScores: Map[String, Int],
    rawOutput: String,
    extractedCode: Option[String],
    cost: Double
):
  def score: Int =
    if !compiles then 0
    else if !testsPass then 40
    else
      val qualityAvg =
        if qualityScores.isEmpty then 0
        else qualityScores.values.sum / qualityScores.size
      40 + (qualityAvg * 0.6).toInt
```

**Step 6: Run tests to verify they pass**

```bash
sbt test
```

Expected: All 3 tests pass

**Step 7: Commit**

```bash
git add .
git commit -m "feat: add core domain models with score calculation"
```

---

## Task 3: YAML Task Loader

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/tasks/TaskLoader.scala`
- Create: `model-benchmark/src/test/scala/benchmark/tasks/TaskLoaderTest.scala`
- Create: `model-benchmark/tasks/scala/simple/sum-list.yaml`

**Step 1: Write failing test for task loading**

```scala
// src/test/scala/benchmark/tasks/TaskLoaderTest.scala
package benchmark.tasks

import benchmark.domain.Task
import munit.FunSuite
import java.nio.file.{Files, Path}

class TaskLoaderTest extends FunSuite {

  val testYaml = """
    |name: test-task
    |language: scala
    |complexity: simple
    |description: "Test task"
    |prompt: |
    |  Write a function
    |scaffold: |
    |  // scaffold
    |tests: |
    |  assert(true)
    |thresholds:
    |  compiles: required
    |""".stripMargin

  test("loads task from YAML string") {
    val task = TaskLoader.fromYaml(testYaml)
    assertEquals(task.name, "test-task")
    assertEquals(task.language, "scala")
    assertEquals(task.complexity, "simple")
    assertEquals(task.thresholds("compiles"), "required")
  }

  test("loads task from file path") {
    val tempFile = Files.createTempFile("task-", ".yaml")
    Files.writeString(tempFile, testYaml)
    try
      val task = TaskLoader.fromFile(tempFile)
      assertEquals(task.name, "test-task")
    finally Files.delete(tempFile)
  }

  test("loads all tasks from directory") {
    val tempDir = Files.createTempDirectory("tasks-")
    val file1 = tempDir.resolve("task1.yaml")
    val file2 = tempDir.resolve("task2.yaml")
    Files.writeString(file1, testYaml)
    Files.writeString(file2, testYaml.replace("test-task", "test-task-2"))
    try
      val tasks = TaskLoader.fromDirectory(tempDir)
      assertEquals(tasks.size, 2)
    finally
      Files.delete(file1)
      Files.delete(file2)
      Files.delete(tempDir)
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error - TaskLoader doesn't exist

**Step 3: Implement TaskLoader**

```scala
// src/main/scala/benchmark/tasks/TaskLoader.scala
package benchmark.tasks

import benchmark.domain.Task
import org.yaml.snakeyaml.Yaml
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

object TaskLoader:

  private val yaml = new Yaml()

  def fromYaml(content: String): Task =
    val data = yaml.load[java.util.Map[String, Any]](content).asScala
    Task(
      name = data("name").toString,
      language = data("language").toString,
      complexity = data("complexity").toString,
      description = data("description").toString,
      prompt = data("prompt").toString,
      scaffold = data.get("scaffold").map(_.toString).getOrElse(""),
      tests = data.get("tests").map(_.toString).getOrElse(""),
      thresholds = data
        .get("thresholds")
        .map(_.asInstanceOf[java.util.Map[String, Any]].asScala.view.mapValues(_.toString).toMap)
        .getOrElse(Map.empty)
    )

  def fromFile(path: Path): Task =
    fromYaml(Files.readString(path))

  def fromDirectory(dir: Path): List[Task] =
    Files
      .list(dir)
      .filter(p => p.toString.endsWith(".yaml") || p.toString.endsWith(".yml"))
      .map(fromFile)
      .toList
      .asScala
      .toList
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: All tests pass

**Step 5: Create sample task file**

```yaml
# tasks/scala/simple/sum-list.yaml
name: sum-list
language: scala
complexity: simple
description: "Implement a function to sum a list of integers"

prompt: |
  Write a Scala function that sums all integers in a list.

  ```scala
  def sumList(numbers: List[Int]): Int = ???
  ```

scaffold: |
  // No scaffold needed

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
git commit -m "feat: add YAML task loader with sample task"
```

---

## Task 4: Claude API Client

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/runner/ClaudeClient.scala`
- Create: `model-benchmark/src/test/scala/benchmark/runner/ClaudeClientTest.scala`

**Step 1: Write test for response parsing**

```scala
// src/test/scala/benchmark/runner/ClaudeClientTest.scala
package benchmark.runner

import benchmark.domain.Model
import munit.FunSuite

class ClaudeClientTest extends FunSuite {

  test("parses successful API response") {
    val json = """
      |{
      |  "content": [{"type": "text", "text": "Here is the code:\n```scala\ndef foo = 1\n```"}],
      |  "usage": {"input_tokens": 100, "output_tokens": 50}
      |}
      |""".stripMargin

    val response = ClaudeClient.parseResponse(json, Model.Haiku)
    assertEquals(response.text, "Here is the code:\n```scala\ndef foo = 1\n```")
    // cost = (100 * 0.001 + 50 * 0.005) / 1000
    assert(response.cost > 0)
  }

  test("extracts code block from response") {
    val text = """Here is the implementation:
      |
      |```scala
      |def sumList(numbers: List[Int]): Int =
      |  numbers.sum
      |```
      |
      |This uses the built-in sum method.""".stripMargin

    val code = ClaudeClient.extractCode(text)
    assertEquals(code, Some("def sumList(numbers: List[Int]): Int =\n  numbers.sum"))
  }

  test("returns None when no code block found") {
    val text = "I don't have any code for you."
    val code = ClaudeClient.extractCode(text)
    assertEquals(code, None)
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error

**Step 3: Implement ClaudeClient**

```scala
// src/main/scala/benchmark/runner/ClaudeClient.scala
package benchmark.runner

import benchmark.domain.{Model, Task}
import io.circe.*
import io.circe.parser.*
import sttp.client3.*

case class ClaudeResponse(text: String, cost: Double)

object ClaudeClient:

  private val codeBlockPattern = "```(?:scala)?\\s*\\n([\\s\\S]*?)\\n```".r

  def parseResponse(json: String, model: Model): ClaudeResponse =
    val doc = parse(json).getOrElse(Json.Null)
    val cursor = doc.hcursor

    val text = cursor
      .downField("content")
      .downArray
      .downField("text")
      .as[String]
      .getOrElse("")

    val inputTokens = cursor.downField("usage").downField("input_tokens").as[Int].getOrElse(0)
    val outputTokens = cursor.downField("usage").downField("output_tokens").as[Int].getOrElse(0)

    val cost =
      (inputTokens * model.costPer1kInput + outputTokens * model.costPer1kOutput) / 1000.0

    ClaudeResponse(text, cost)

  def extractCode(text: String): Option[String] =
    codeBlockPattern.findFirstMatchIn(text).map(_.group(1).trim)

  def sendRequest(task: Task, model: Model, apiKey: String): ClaudeResponse =
    val backend = HttpURLConnectionBackend()

    val requestBody = Json.obj(
      "model" -> Json.fromString(model.id),
      "max_tokens" -> Json.fromInt(4096),
      "messages" -> Json.arr(
        Json.obj(
          "role" -> Json.fromString("user"),
          "content" -> Json.fromString(task.prompt)
        )
      )
    )

    val response = basicRequest
      .post(uri"https://api.anthropic.com/v1/messages")
      .header("x-api-key", apiKey)
      .header("anthropic-version", "2023-06-01")
      .header("content-type", "application/json")
      .body(requestBody.noSpaces)
      .send(backend)

    response.body match
      case Right(body) => parseResponse(body, model)
      case Left(error) => throw new RuntimeException(s"API error: $error")
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Claude API client with response parsing"
```

---

## Task 5: Scala Evaluator

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/evaluator/ScalaEvaluator.scala`
- Create: `model-benchmark/src/test/scala/benchmark/evaluator/ScalaEvaluatorTest.scala`

**Step 1: Write failing test for compilation check**

```scala
// src/test/scala/benchmark/evaluator/ScalaEvaluatorTest.scala
package benchmark.evaluator

import benchmark.domain.Task
import munit.FunSuite

class ScalaEvaluatorTest extends FunSuite {

  val validCode = """
    |def sumList(numbers: List[Int]): Int = numbers.sum
    |""".stripMargin

  val invalidCode = """
    |def sumList(numbers: List[Int]): Int = numbers.summ // typo
    |""".stripMargin

  val task = Task(
    name = "sum-list",
    language = "scala",
    complexity = "simple",
    description = "Sum a list",
    prompt = "...",
    scaffold = "",
    tests = "assert(sumList(List(1,2,3)) == 6)",
    thresholds = Map("compiles" -> "required")
  )

  test("compiles returns true for valid code") {
    val result = ScalaEvaluator.compiles(validCode)
    assert(result)
  }

  test("compiles returns false for invalid code") {
    val result = ScalaEvaluator.compiles(invalidCode)
    assert(!result)
  }

  test("runTests returns true when assertions pass") {
    val result = ScalaEvaluator.runTests(validCode, task.tests)
    assert(result)
  }

  test("runTests returns false when assertions fail") {
    val wrongCode = "def sumList(numbers: List[Int]): Int = 0"
    val result = ScalaEvaluator.runTests(wrongCode, task.tests)
    assert(!result)
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error

**Step 3: Implement ScalaEvaluator**

```scala
// src/main/scala/benchmark/evaluator/ScalaEvaluator.scala
package benchmark.evaluator

import benchmark.domain.Task
import java.nio.file.{Files, Path}
import scala.sys.process.*
import scala.util.{Try, Success, Failure}

object ScalaEvaluator:

  def compiles(code: String): Boolean =
    withTempFile(code) { file =>
      val result = Process(Seq("scalac", file.toString)).!
      result == 0
    }

  def runTests(code: String, tests: String): Boolean =
    val fullCode = s"""
      |$code
      |
      |@main def runTests(): Unit = {
      |  $tests
      |  println("ALL_TESTS_PASSED")
      |}
      |""".stripMargin

    withTempDir { dir =>
      val sourceFile = dir.resolve("Test.scala")
      Files.writeString(sourceFile, fullCode)

      val compileResult = Process(Seq("scalac", "-d", dir.toString, sourceFile.toString)).!
      if compileResult != 0 then return false

      val output = Process(Seq("scala", "-cp", dir.toString, "runTests")).!!
      output.contains("ALL_TESTS_PASSED")
    }

  def scalafmtScore(code: String): Int =
    withTempFile(code) { file =>
      val checkResult = Process(Seq("scalafmt", "--check", file.toString)).!
      if checkResult == 0 then 100 else 70 // simplified scoring
    }

  def evaluate(code: String, task: Task): Map[String, Int] =
    Map(
      "scalafmt" -> scalafmtScore(code)
      // Add scalafix, wartremover in future
    )

  private def withTempFile[T](code: String)(f: Path => T): T =
    val file = Files.createTempFile("benchmark-", ".scala")
    try
      Files.writeString(file, code)
      f(file)
    finally Files.deleteIfExists(file)

  private def withTempDir[T](f: Path => T): T =
    val dir = Files.createTempDirectory("benchmark-")
    try f(dir)
    finally
      Files.walk(dir).sorted(java.util.Comparator.reverseOrder()).forEach(Files.delete)
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: Tests pass (requires scalac in PATH)

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Scala evaluator for compilation and tests"
```

---

## Task 6: Benchmark Runner

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/runner/BenchmarkRunner.scala`
- Create: `model-benchmark/src/test/scala/benchmark/runner/BenchmarkRunnerTest.scala`

**Step 1: Write failing test**

```scala
// src/test/scala/benchmark/runner/BenchmarkRunnerTest.scala
package benchmark.runner

import benchmark.domain.{Model, Task, EvalResult}
import munit.FunSuite

class BenchmarkRunnerTest extends FunSuite {

  test("runTask returns EvalResult for each model") {
    val task = Task(
      name = "test",
      language = "scala",
      complexity = "simple",
      description = "Test",
      prompt = "Write hello world",
      scaffold = "",
      tests = "",
      thresholds = Map.empty
    )

    // Mock client that returns fixed response
    val mockClient: (Task, Model) => ClaudeResponse = (_, _) =>
      ClaudeResponse("```scala\nprintln(\"hello\")\n```", 0.001)

    val results = BenchmarkRunner.runTask(task, List(Model.Haiku), mockClient)

    assertEquals(results.size, 1)
    assertEquals(results.head.model, Model.Haiku)
    assertEquals(results.head.extractedCode, Some("println(\"hello\")"))
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error

**Step 3: Implement BenchmarkRunner**

```scala
// src/main/scala/benchmark/runner/BenchmarkRunner.scala
package benchmark.runner

import benchmark.domain.{Model, Task, EvalResult}
import benchmark.evaluator.ScalaEvaluator

object BenchmarkRunner:

  type ClientFn = (Task, Model) => ClaudeResponse

  def runTask(task: Task, models: List[Model], client: ClientFn): List[EvalResult] =
    models.map { model =>
      val response = client(task, model)
      val extractedCode = ClaudeClient.extractCode(response.text)

      extractedCode match
        case None =>
          EvalResult(
            taskName = task.name,
            model = model,
            compiles = false,
            testsPass = false,
            qualityScores = Map.empty,
            rawOutput = response.text,
            extractedCode = None,
            cost = response.cost
          )

        case Some(code) =>
          val compiles = ScalaEvaluator.compiles(code)
          val testsPass = if compiles && task.tests.nonEmpty then
            ScalaEvaluator.runTests(code, task.tests)
          else false

          val qualityScores = if compiles then
            ScalaEvaluator.evaluate(code, task)
          else Map.empty[String, Int]

          EvalResult(
            taskName = task.name,
            model = model,
            compiles = compiles,
            testsPass = testsPass,
            qualityScores = qualityScores,
            rawOutput = response.text,
            extractedCode = Some(code),
            cost = response.cost
          )
    }

  def runSuite(
      tasks: List[Task],
      models: List[Model],
      client: ClientFn
  ): Map[String, List[EvalResult]] =
    tasks.map(task => task.name -> runTask(task, models, client)).toMap
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add benchmark runner to orchestrate task execution"
```

---

## Task 7: Report Generator

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/reporter/Reporter.scala`
- Create: `model-benchmark/src/test/scala/benchmark/reporter/ReporterTest.scala`

**Step 1: Write failing test**

```scala
// src/test/scala/benchmark/reporter/ReporterTest.scala
package benchmark.reporter

import benchmark.domain.{Model, EvalResult}
import munit.FunSuite

class ReporterTest extends FunSuite {

  val results = Map(
    "task1" -> List(
      EvalResult("task1", Model.Haiku, true, true, Map("scalafmt" -> 90), "", Some(""), 0.001),
      EvalResult("task1", Model.Opus, true, true, Map("scalafmt" -> 95), "", Some(""), 0.01)
    ),
    "task2" -> List(
      EvalResult("task2", Model.Haiku, true, false, Map.empty, "", Some(""), 0.001),
      EvalResult("task2", Model.Opus, true, true, Map("scalafmt" -> 100), "", Some(""), 0.01)
    )
  )

  test("generates markdown report with summary table") {
    val report = Reporter.generateMarkdown(results)
    assert(report.contains("| Model"))
    assert(report.contains("Haiku"))
    assert(report.contains("Opus"))
  }

  test("identifies close calls within threshold") {
    val closeCalls = Reporter.findCloseCalls(results, threshold = 10)
    assertEquals(closeCalls.size, 1)
    assertEquals(closeCalls.head._1, "task1")
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error

**Step 3: Implement Reporter**

```scala
// src/main/scala/benchmark/reporter/Reporter.scala
package benchmark.reporter

import benchmark.domain.{Model, EvalResult}
import java.time.LocalDate

object Reporter:

  case class ModelSummary(model: Model, avgScore: Int, totalCost: Double, tasksWon: Int)

  def generateMarkdown(results: Map[String, List[EvalResult]]): String =
    val summaries = summarizeByModel(results)
    val closeCalls = findCloseCalls(results, threshold = 5)
    val date = LocalDate.now()

    s"""# Benchmark Results - $date
       |
       |## Summary
       |
       || Model | Avg Score | Cost | Tasks Won |
       ||-------|-----------|------|-----------|
       |${summaries.map(s => s"| ${s.model} | ${s.avgScore}% | $$${f"${s.totalCost}%.4f"} | ${s.tasksWon}/${results.size} |").mkString("\n")}
       |
       |## Recommendations
       |
       |${generateRecommendations(summaries)}
       |
       |## Close Calls (need blind review)
       |
       |${if closeCalls.isEmpty then "None" else closeCalls.map((name, results) =>
         s"- $name (${results.map(r => s"${r.model}: ${r.score}").mkString(", ")})"
       ).mkString("\n")}
       |
       |## Full Results
       |
       |${generateDetailedResults(results)}
       |""".stripMargin

  def summarizeByModel(results: Map[String, List[EvalResult]]): List[ModelSummary] =
    val allResults = results.values.flatten.toList
    val models = allResults.map(_.model).distinct

    models.map { model =>
      val modelResults = allResults.filter(_.model == model)
      val avgScore = if modelResults.nonEmpty then
        modelResults.map(_.score).sum / modelResults.size
      else 0
      val totalCost = modelResults.map(_.cost).sum
      val tasksWon = results.count { case (_, taskResults) =>
        taskResults.filter(_.model == model).exists { r =>
          r.score == taskResults.map(_.score).max
        }
      }
      ModelSummary(model, avgScore, totalCost, tasksWon)
    }.sortBy(-_.avgScore)

  def findCloseCalls(
      results: Map[String, List[EvalResult]],
      threshold: Int
  ): List[(String, List[EvalResult])] =
    results.toList.filter { case (_, taskResults) =>
      val scores = taskResults.map(_.score).sorted.reverse
      scores.length >= 2 && (scores(0) - scores(1)) <= threshold
    }

  private def generateRecommendations(summaries: List[ModelSummary]): String =
    summaries match
      case best :: rest =>
        s"- **Best overall**: ${best.model} (${best.avgScore}% avg)\n" +
        rest.map(s => s"- ${s.model}: ${s.avgScore}% avg, $$${f"${s.totalCost}%.4f"} cost").mkString("\n")
      case _ => "No data"

  private def generateDetailedResults(results: Map[String, List[EvalResult]]): String =
    results.toList.sortBy(_._1).map { case (name, taskResults) =>
      s"### $name\n\n" +
      taskResults.sortBy(-_.score).map { r =>
        s"- **${r.model}**: ${r.score}% (compiles: ${r.compiles}, tests: ${r.testsPass})"
      }.mkString("\n")
    }.mkString("\n\n")
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add report generator with markdown output"
```

---

## Task 8: Blind Review System

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/reporter/BlindReview.scala`
- Create: `model-benchmark/src/test/scala/benchmark/reporter/BlindReviewTest.scala`

**Step 1: Write failing test**

```scala
// src/test/scala/benchmark/reporter/BlindReviewTest.scala
package benchmark.reporter

import benchmark.domain.{Model, EvalResult}
import munit.FunSuite

class BlindReviewTest extends FunSuite {

  test("shuffles options and hides model names") {
    val results = List(
      EvalResult("task1", Model.Haiku, true, true, Map.empty, "", Some("code A"), 0.001),
      EvalResult("task1", Model.Opus, true, true, Map.empty, "", Some("code B"), 0.01)
    )

    val review = BlindReview.prepare("task1", results)

    assertEquals(review.taskName, "task1")
    assertEquals(review.options.size, 2)
    assert(review.options.forall(o => o.label == "A" || o.label == "B"))
    // Model should be hidden in the option
    assert(!review.options.map(_.code).mkString.contains("Haiku"))
  }

  test("resolves winner correctly") {
    val review = BlindReview.ReviewSession(
      taskName = "task1",
      options = List(
        BlindReview.Option("A", "code A", Model.Haiku),
        BlindReview.Option("B", "code B", Model.Opus)
      )
    )

    val result = BlindReview.resolve(review, choice = "A")
    assertEquals(result.winner, Model.Haiku)
  }

  test("tie goes to cheaper model") {
    val review = BlindReview.ReviewSession(
      taskName = "task1",
      options = List(
        BlindReview.Option("A", "code A", Model.Opus),
        BlindReview.Option("B", "code B", Model.Haiku)
      )
    )

    val result = BlindReview.resolve(review, choice = "tie")
    assertEquals(result.winner, Model.Haiku)
  }
}
```

**Step 2: Run test to verify it fails**

```bash
sbt test
```

Expected: Compilation error

**Step 3: Implement BlindReview**

```scala
// src/main/scala/benchmark/reporter/BlindReview.scala
package benchmark.reporter

import benchmark.domain.{Model, EvalResult}
import scala.util.Random

object BlindReview:

  case class Option(label: String, code: String, model: Model)
  case class ReviewSession(taskName: String, options: List[Option])
  case class ReviewResult(taskName: String, choice: String, winner: Model, reason: String)

  def prepare(taskName: String, results: List[EvalResult]): ReviewSession =
    val shuffled = Random.shuffle(results.filter(_.extractedCode.isDefined))
    val labels = List("A", "B", "C", "D").take(shuffled.size)

    val options = shuffled.zip(labels).map { case (result, label) =>
      Option(label, result.extractedCode.getOrElse(""), result.model)
    }

    ReviewSession(taskName, options)

  def resolve(session: ReviewSession, choice: String): ReviewResult =
    val winner = choice.toLowerCase match
      case "tie" =>
        // Tie goes to cheaper model
        session.options.map(_.model).minBy(_.costPer1kInput)
      case label =>
        session.options.find(_.label.equalsIgnoreCase(label)).map(_.model).getOrElse(
          session.options.head.model
        )

    val reason = if choice.toLowerCase == "tie" then "cost" else "quality"
    ReviewResult(session.taskName, choice, winner, reason)

  def formatForDisplay(session: ReviewSession): String =
    val header = s"Close call: ${session.taskName}\n"
    val options = session.options.map { opt =>
      s"""--- Option ${opt.label} ---
         |${opt.code}
         |""".stripMargin
    }.mkString("\n")

    header + options + "\nWhich is better? [" + session.options.map(_.label).mkString("/") + "/tie]: "
```

**Step 4: Run tests to verify they pass**

```bash
sbt test
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add blind review system for close calls"
```

---

## Task 9: CLI Interface

**Files:**
- Create: `model-benchmark/src/main/scala/benchmark/Main.scala`

**Step 1: Implement CLI with decline**

```scala
// src/main/scala/benchmark/Main.scala
package benchmark

import benchmark.domain.{Model, Task}
import benchmark.runner.{BenchmarkRunner, ClaudeClient, ClaudeResponse}
import benchmark.reporter.{Reporter, BlindReview}
import benchmark.tasks.TaskLoader
import com.monovore.decline.*
import java.nio.file.{Files, Path, Paths}
import scala.io.StdIn

object Main
    extends CommandApp(
      name = "model-benchmark",
      header = "Benchmark Claude models on coding tasks",
      main = {
        val runCmd = Opts.subcommand("run", "Run benchmark suite") {
          val suite = Opts.option[String]("suite", "Task suite to run (e.g., scala-simple)").orNone
          val task = Opts.option[String]("task", "Single task path to run").orNone
          val models = Opts
            .option[String]("models", "Comma-separated models (haiku,sonnet,opus)")
            .withDefault("haiku,sonnet,opus")
          (suite, task, models).mapN { (suiteOpt, taskOpt, modelsStr) =>
            runBenchmark(suiteOpt, taskOpt, parseModels(modelsStr))
          }
        }

        val listCmd = Opts.subcommand("list", "List available tasks") {
          Opts.unit.map(_ => listTasks())
        }

        val reviewCmd = Opts.subcommand("review", "Review close calls from last run") {
          Opts.unit.map(_ => reviewCloseCalls())
        }

        runCmd orElse listCmd orElse reviewCmd
      }
    )

def parseModels(str: String): List[Model] =
  str.split(",").toList.flatMap {
    case "haiku"  => Some(Model.Haiku)
    case "sonnet" => Some(Model.Sonnet)
    case "opus"   => Some(Model.Opus)
    case _        => None
  }

def runBenchmark(suite: Option[String], task: Option[String], models: List[Model]): Unit =
  val apiKey = sys.env.getOrElse("ANTHROPIC_API_KEY", {
    println("Error: ANTHROPIC_API_KEY not set")
    sys.exit(1)
  })

  val tasks = (suite, task) match
    case (Some(s), _) =>
      val parts = s.split("-")
      val dir = Paths.get(s"tasks/${parts(0)}/${parts(1)}")
      if Files.exists(dir) then TaskLoader.fromDirectory(dir)
      else
        println(s"Suite not found: $s")
        sys.exit(1)
    case (_, Some(t)) =>
      val path = Paths.get(s"tasks/$t.yaml")
      if Files.exists(path) then List(TaskLoader.fromFile(path))
      else
        println(s"Task not found: $t")
        sys.exit(1)
    case _ =>
      println("Specify --suite or --task")
      sys.exit(1)

  println(s"Running ${tasks.size} tasks with models: ${models.mkString(", ")}")

  val client: (Task, Model) => ClaudeResponse = (t, m) =>
    println(s"  Running ${t.name} with ${m}...")
    ClaudeClient.sendRequest(t, m, apiKey)

  val results = BenchmarkRunner.runSuite(tasks, models, client)

  val report = Reporter.generateMarkdown(results)
  val reportPath = Paths.get(s"reports/benchmark-${java.time.LocalDate.now()}.md")
  Files.createDirectories(reportPath.getParent)
  Files.writeString(reportPath, report)

  println(s"\nReport saved to: $reportPath")
  println(report)

  // Save results for review command
  saveResults(results)

def listTasks(): Unit =
  val tasksDir = Paths.get("tasks")
  if !Files.exists(tasksDir) then
    println("No tasks directory found")
    return

  println("Available tasks:\n")
  Files
    .walk(tasksDir)
    .filter(p => p.toString.endsWith(".yaml"))
    .forEach { path =>
      val relative = tasksDir.relativize(path).toString.replace(".yaml", "")
      println(s"  $relative")
    }

def reviewCloseCalls(): Unit =
  val resultsPath = Paths.get("reports/last-results.json")
  if !Files.exists(resultsPath) then
    println("No results to review. Run a benchmark first.")
    return

  // Load and review (simplified - would need JSON deserialization)
  println("Review functionality - load from last-results.json")

def saveResults(results: Map[String, List[benchmark.domain.EvalResult]]): Unit =
  // Simplified - would serialize to JSON
  val path = Paths.get("reports/last-results.json")
  Files.createDirectories(path.getParent)
  Files.writeString(path, results.toString)
```

**Step 2: Test CLI compiles and shows help**

```bash
sbt "run --help"
```

Expected: Shows usage information

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add CLI interface with run, list, review commands"
```

---

## Task 10: Create Sample Task Suite

**Files:**
- Create: `model-benchmark/tasks/scala/simple/sum-list.yaml`
- Create: `model-benchmark/tasks/scala/simple/reverse-string.yaml`
- Create: `model-benchmark/tasks/scala/simple/find-max.yaml`
- Create: `model-benchmark/tasks/scala/medium/flatten-nested.yaml`
- Create: `model-benchmark/tasks/scala/medium/group-by-key.yaml`

**Step 1: Create simple tasks**

```yaml
# tasks/scala/simple/sum-list.yaml
name: sum-list
language: scala
complexity: simple
description: "Sum all integers in a list"

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

```yaml
# tasks/scala/simple/reverse-string.yaml
name: reverse-string
language: scala
complexity: simple
description: "Reverse a string"

prompt: |
  Write a Scala function that reverses a string.

  ```scala
  def reverseString(s: String): String = ???
  ```

scaffold: ""

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
language: scala
complexity: simple
description: "Find maximum value in a list"

prompt: |
  Write a Scala function that finds the maximum value in a non-empty list.
  You may assume the list is never empty.

  ```scala
  def findMax(numbers: List[Int]): Int = ???
  ```

scaffold: ""

tests: |
  assert(findMax(List(1, 5, 3)) == 5)
  assert(findMax(List(-1, -5, -3)) == -1)
  assert(findMax(List(42)) == 42)

thresholds:
  compiles: required
  tests_pass: required
```

**Step 2: Create medium tasks**

```yaml
# tasks/scala/medium/flatten-nested.yaml
name: flatten-nested
language: scala
complexity: medium
description: "Flatten a nested list structure"

prompt: |
  Write a Scala function that flattens a list of lists into a single list.

  ```scala
  def flatten[A](nested: List[List[A]]): List[A] = ???
  ```

scaffold: ""

tests: |
  assert(flatten(List(List(1, 2), List(3, 4))) == List(1, 2, 3, 4))
  assert(flatten(List(List.empty[Int], List(1))) == List(1))
  assert(flatten(List.empty[List[Int]]) == List.empty[Int])

thresholds:
  compiles: required
  tests_pass: required
```

```yaml
# tasks/scala/medium/group-by-key.yaml
name: group-by-key
language: scala
complexity: medium
description: "Group list elements by a key function"

prompt: |
  Write a Scala function that groups elements by the result of a key function.
  Return a Map where keys are the results of applying the key function,
  and values are lists of elements that produced that key.

  ```scala
  def groupByKey[A, K](items: List[A])(key: A => K): Map[K, List[A]] = ???
  ```

scaffold: ""

tests: |
  val result = groupByKey(List("one", "two", "three"))(_.length)
  assert(result(3) == List("one", "two"))
  assert(result(5) == List("three"))

thresholds:
  compiles: required
  tests_pass: required
```

**Step 3: Verify tasks load correctly**

```bash
sbt "run list"
```

Expected: Shows all 5 tasks

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add sample Scala task suite (simple and medium)"
```

---

## Task 11: End-to-End Test

**Step 1: Set API key**

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Step 2: Run benchmark on simple suite**

```bash
sbt "run run --suite scala-simple --models haiku,sonnet"
```

Expected: Report generated with scores for each task/model combination

**Step 3: Review output**

Check `reports/benchmark-YYYY-MM-DD.md` for the generated report.

**Step 4: Commit any fixes**

```bash
git add .
git commit -m "fix: adjustments from end-to-end testing"
```

---

## Summary

**Phase 1 complete when:**
- [ ] All 10 tasks implemented and committed
- [ ] `sbt test` passes all unit tests
- [ ] `sbt "run run --suite scala-simple"` produces a valid report
- [ ] At least 5 sample Scala tasks exist

**Phase 2 (future):**
- Add Kotlin evaluator and tasks
- Add complex task suite
- Implement full blind review flow with JSON persistence
- Add scalafix and wartremover scoring
