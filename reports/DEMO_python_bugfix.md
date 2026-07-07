# Demo Report

- Task: `python_bugfix`
- Success: **True**
- Workspace: `D:\-\hello-agent\mini-coding-agent-harness\artifacts\demo\python_bugfix\workspace`
- Trace: `D:\-\hello-agent\mini-coding-agent-harness\artifacts\demo\python_bugfix\trace.jsonl`
- HTML trace: `D:\-\hello-agent\mini-coding-agent-harness\artifacts\demo\python_bugfix\TRACE.html` (22490 chars)

## Tool Flow

1. `todo_write` creates a repair plan.
2. `run_tests` reproduces the failing calculator test.
3. `read_file` inspects `calculator.py`.
4. `edit_file` changes `return a - b` to `return a + b`.
5. `run_tests` verifies the fix.
6. `git_diff` shows the final code change.
7. `trace-report` renders the JSONL trace as static HTML.

## Before

```text
============================= test session starts =============================
platform win32 -- Python 3.10.9, pytest-7.1.2, pluggy-1.0.0
rootdir: D:\-\hello-agent\mini-coding-agent-harness\artifacts\demo\python_bugfix\workspace, configfile: ..\..\..\..\pytest.ini
plugins: anyio-3.5.0
collected 1 item

tests\test_calculator.py F                                               [100%]

================================== FAILURES ===================================
__________________________________ test_add ___________________________________

    def test_add():
>       assert add(2, 3) == 5
E       assert -1 == 5
E        +  where -1 = add(2, 3)

tests\test_calculator.py:4: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_calculator.py::test_add - assert -1 == 5
============================== 1 failed in 0.16s ==============================
```

## After

```text
============================= test session starts =============================
platform win32 -- Python 3.10.9, pytest-7.1.2, pluggy-1.0.0
rootdir: D:\-\hello-agent\mini-coding-agent-harness\artifacts\demo\python_bugfix\workspace, configfile: ..\..\..\..\pytest.ini
plugins: anyio-3.5.0
collected 1 item

tests\test_calculator.py .                                               [100%]

============================== 1 passed in 0.02s ==============================
```

## Diff

```diff
diff --git a/calculator.py b/calculator.py
index 12ee743..4693ad3 100644
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
```
