# comMS test suite
This document outlines the comMS test suite: its structure, shared fixtures, and what each module covers.

## Running the test suite
comMS uses [pytest](https://docs.pytest.org). To run the full suite:

```bash
uv run pytest
```

To run only the unit tests (no external binaries required):

```bash
uv run pytest tests/unit/
```

To run only the integration tests:

```bash
uv run pytest tests/integration/
```

To run with verbose output:

```bash
uv run pytest -v
```

## Test markers
Two custom markers control which tests are run depending on external binary availability:

| Marker | Requirement |
|---|---|
| `crux` | Requires the Crux binary under `bin/` |
| `trfp` | Requires ThermoRawFileParser under `bin/` |

Tests decorated with these markers are skipped automatically (with a message) if the corresponding binary is not found, and the rest of the suite continue unaffected. To run only unmarked tests (i.e. those with no external dependency):

```bash
uv run pytest -m "not crux and not trfp"
```