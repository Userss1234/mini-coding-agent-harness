# Tool Implementation Verification Workflow

## Summary

When adding a new harness tool, implement the tool, add focused pytest coverage, update README and REVIEW output, then run pytest, py_compile, and inspect.

## Trigger

Use when adding or changing a tool in harness/tools.py.

## Steps

1. Add the tool handler and register its schema in build_registry.
2. Add pytest coverage for success, failure, and permission behavior.
3. Update inspect_repo if the tool should appear in REVIEW.md.
4. Update README so the documented MVP matches the registry.
5. Run python -m pytest and py_compile.
6. Run python main.py --allow-write --fresh-trace inspect.
