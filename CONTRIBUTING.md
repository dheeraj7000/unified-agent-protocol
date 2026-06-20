# Contributing to UAP-Reference

Thank you for your interest in contributing to the Unified Agent Protocol (UAP) reference implementation!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/dheeraj7000/unified-agent-protocol.git
   cd uap-reference
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the package in editable mode with development and server dependencies:
   ```bash
   pip install -e '.[dev,server]'
   ```

## Running Tests

To run the unit tests:
```bash
python -m unittest discover -s tests -v
```

To run the integration tests:
```bash
python examples/integration_test.py
```

## Linting and Type Checking

We use `ruff` for linting and formatting, and `mypy` for type checking.
```bash
ruff check src tests
mypy src/uap
```

## Adding a Capability Adapter

If you want to add a new protocol bridge or adapter, place your source file under `src/uap/adapters/`. Reference existing adapters like `src/uap/adapters/mcp.py` or `src/uap/adapters/openapi.py` for design patterns.

## Adding Conformance Tests

To add a new conformance test vector, create a JSON file in `conformance/test-vectors/` using the standard schema:
```json
{
  "name": "your_test_name",
  "description": "What it tests",
  "input": { ... },
  "expect": { ... }
}
```

## PR Checklist

Before submitting a Pull Request, please ensure:
1. All unit and integration tests pass.
2. `ruff check` and `mypy` run with no errors.
3. If introducing new behavior, a corresponding conformance vector is added.
