# stolid Development Guidelines

## Documentation

Always update `README.rst` when adding a new SLD error code. Each code
needs a short description and (where helpful) a bad/good example, placed
under the appropriate `SLDNxx` section heading.

## Adopting a New Rule

When you finish implementing a new SLD rule and it catches violations in
stolid's own source, follow this two-step adoption sequence:

1. **Commit and push the rule first.** The implementation, tests,
   coverage, and README update are one self-contained change; ship that
   commit on its own so the rule's history isn't entangled with the
   cleanup it forces.
2. **Then fix the violations the rule found in stolid itself**, as one
   or more follow-up commits, and push. Stolid practices what it
   preaches: every rule it ships must hold on its own codebase.

This applies whether the new rule runs as a flake8 plugin check or as a
cross-file scanner under `python -m stolid`.

## Running Tests and Linting

**Always run `nox` to verify your changes.** Never rely on reasoning,
type-checks, or partial runs alone — every task must be verified by
actually running `nox` against the code.

Use `nox` to run all checks. If nox is not installed:

```bash
pip install nox
```

Run all checks:
```bash
nox
```

Run specific sessions:
```bash
nox -s tests    # Run tests with coverage
nox -s lint     # Run black and flake8
nox -s mypy     # Run type checking
```

**Always run the full `nox` before declaring a task complete.** Running
individual tools (e.g. `flake8`, `pytest`, `mypy`) directly is not enough:
stolid itself runs as a flake8 plugin, and the `lint` session is the only
configuration that actually loads the stolid plugin and self-checks the
codebase against its own rules. Per-tool invocations outside of nox can
silently miss stolid violations (for example, SLD60x function-length or
SLD20x import-placement errors).

### Installing Python 3.14

`nox` requires Python 3.12, 3.13, and 3.14 (see `VERSIONS` in
`noxfile.py`). The `tests-3.14`, `lint`, `mypy`, `docs`, `build`, and
`dry_release` sessions all run on 3.14, so a working `python3.14` on
`PATH` is mandatory. The interpreter must be a full system install
(stdlib alongside the binary) so that `virtualenv` — which nox uses to
build session venvs — can resolve `encodings` and friends.

On Ubuntu 24.04 (Noble), install Python 3.14 from the deadsnakes PPA:

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.14 python3.14-venv
```

Then verify the interpreter and that `venv` works end-to-end (this is
what `virtualenv` needs):

```bash
python3.14 --version
python3.14 -m venv /tmp/check-314 && /tmp/check-314/bin/python -c 'import encodings'
rm -rf /tmp/check-314
```

Do **not** install Python 3.14 with `uv python install` and symlink the
binary into `/usr/local/bin`: `virtualenv` resolves `home` from the
symlink target and fails with `ModuleNotFoundError: No module named
'encodings'` when nox tries to create the session env.

If `python3.12` or `python3.13` are missing, install them the same way
(`apt-get install -y python3.12 python3.12-venv` etc.) so `nox -s tests`
runs the full version matrix.

## Checking CI

**Do not declare a task complete until CI is green.** A clean local
`nox` is necessary but not sufficient — push the branch, watch the
checks defined in `.github/workflows/pr-main.yml` (`tests-3.12`,
`tests-3.13`, `tests-3.14`, `lint`, `mypy`, `docs`, `build`,
`dry_release`), and only call the task done once every required check
has passed. If a check fails, fix the underlying issue, push again, and
re-check — CI is the final verification, not a formality.

## Testing Framework: Virtue

This project uses **Virtue** as the test runner, not pytest. Tests are standard `unittest.TestCase` classes with methods prefixed with `test_`. Use **PyHamcrest** matchers for readable assertions.

Example test pattern:

```python
import unittest
from hamcrest import assert_that, equal_to

class TestPlanStack(unittest.TestCase):
    def test_add_step(self) -> None:
        plan = PlanStack()
        result = plan.add("Do something")
        assert_that(plan.current_plan(), equal_to(["Do something"]))
```

## No Mocking - Dependency Injection Only

Tests **never** use `unittest.mock.patch`. All dependencies are injected.

Bad:
```python
from unittest.mock import patch

class TestBad(unittest.TestCase):
    @patch("mymodule.requests.get")
    def test_fetch(self, mock_get):
        mock_get.return_value.json.return_value = {"data": 1}
        result = fetch_data()
        assert_that(result, equal_to(1))
```

Good:
```python
class TestGood(unittest.TestCase):
    def test_fetch(self) -> None:
        fake_client = FakeHTTPClient(response={"data": 1})
        fetcher = DataFetcher(client=fake_client)
        result = fetcher.fetch()
        assert_that(result, equal_to(1))
```

This makes tests deterministic and easier to reason about.

## 100% Code Coverage Required

The project enforces 100% code coverage with branch coverage. Any untested code must be explicitly marked:

```python
if rare_edge_case:  # pragma: no cover
    handle_edge_case()
```

Use `# pragma: no cover` sparingly and only when testing is genuinely impractical.

## Object-Oriented Design Principles

### Declare Interfaces with Protocol

Make contracts explicit using `typing.Protocol`:

```python
from typing import Protocol

class HTTPClient(Protocol):
    def get(self, url: str) -> Response: ...
    def post(self, url: str, data: bytes) -> Response: ...

class DataFetcher:
    def __init__(self, client: HTTPClient) -> None:
        self.client = client
```

This enables:
- Clear communication of expected behavior
- Easy creation of test doubles
- Type checker verification of implementations

### Simplify Initialization

Keep constructors boring - only assign parameters to attributes:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True, kw_only=True)
class DataProcessor:
    client: HTTPClient
    config: Config

    @classmethod
    def from_environment(cls) -> "DataProcessor":
        # Complex setup logic goes in class methods
        return cls(
            client=RealHTTPClient(),
            config=Config.load(),
        )
```

Never do I/O or complex object creation in `__init__`.

### Avoid Mutation

Prefer immutable objects using `@dataclass(frozen=True)`:

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True, slots=True)
class Settings:
    timeout: int
    retries: int

# Create modified copies instead of mutating
new_settings = replace(settings, timeout=30)
```

### Avoid Hiding

Don't use private methods that duplicate logic. Extract into separate classes:

Bad:
```python
class Processor:
    def _validate(self, data):
        # validation logic

    def process_a(self, data):
        self._validate(data)
        # process A

    def process_b(self, data):
        self._validate(data)
        # process B
```

Good:
```python
class Validator:
    def validate(self, data):
        # validation logic

class Processor:
    def __init__(self, validator: Validator) -> None:
        self.validator = validator
```

### Avoid Inheritance

Use composition and Protocol instead of inheritance:

Bad:
```python
class BaseHandler:
    def handle(self):
        self.validate()
        self.process()

class MyHandler(BaseHandler):
    def validate(self): ...
    def process(self): ...
```

Good:
```python
from dataclasses import dataclass

class Validator(Protocol):
    def validate(self, data: Data) -> None: ...

class Processor(Protocol):
    def process(self, data: Data) -> Result: ...

@dataclass(frozen=True, slots=True)
class Handler:
    validator: Validator
    processor: Processor

    def handle(self, data: Data) -> Result:
        self.validator.validate(data)
        return self.processor.process(data)
```

### Keep Methods Minimal

Classes should be data containers with minimal behavior. Prefer module-level functions or `functools.singledispatch` for complex operations:

```python
import functools

@functools.singledispatch
def serialize(obj) -> bytes:
    raise TypeError(f"Cannot serialize {type(obj)}")

@serialize.register
def _(obj: User) -> bytes:
    return json.dumps({"name": obj.name}).encode()

@serialize.register
def _(obj: Order) -> bytes:
    return json.dumps({"items": obj.items}).encode()
```
