# Contributing to comMS

Thank you for your interest in contributing to the development of comMS! This document covers setting up a development environment, the comMS project layout and code style, and how to submit changes.



## Setting up a development environment

As described in [`README.md`][readme-link], comMS requires Python 3.14 or later and uses [`uv`](https://docs.astral.sh/uv/) for Python dependency management.

Clone the repository and install comMS in editable mode with all development dependencies:
```bash
git clone https://github.com/holsam/comMS
cd comMS
uv sync
```
This installs comMS as an editable package into a `.venv` managed by `uv`. The `comms` command will be available within the virtual environment.

To activate the environment manually:
```bash
source .venv/bin/activate
```

### Installing external tools
It is recommended that any development environment includes the external binaries that comMS wraps: the [Crux toolkit][crux-url] and [ThermoRawFileParser][trfp-url].

See [Installing external tools](./README.md#installing-external-tools) in [`README.md`][readme-link] for the expected layout.


## Project layout
comMS follows the below structure:
```
comMS/
  bin/              # External binaries
  src/
    comms/
      cli/          # Typer command definitions (argument parsing, help text)
      commands/     # Logic for each individual command
      utils/        # Shared utilities (e.g I/O, paths, config, Crux/TRFP wrappers)
      config.toml   # Bundled default configuration
  tests/
    conftest.py     # Shared fixtures and binary-availability guards
    fixtures/
      generate_fixtures.py   # Synthetic FASTA and mzML generator
    unit/           # Pure logic tests, no external binaries required
    integration/    # End-to-end tests, may require Crux and/or TRFP
  pyproject.toml    # Project configuration
  uv.lock           # UV lockfile
```

### CLI vs commands separation
Each command is split across two files:
File | Purpose
-- | --
`cli/<command>.py` | Defines the Typer command, argument types, and default values drawn from config
`commands/<command>.py` | Contains all command logic, using functions which are importable and testable without invoking Typer

When adding a new command, please keep these files separate.

## Code style
- Use `camelCase` for functions and `snake_case` for local variables.
- User-facing terminal output should use [Rich](https://rich.readthedocs.io) markup via `from rich import print`.
- Logging should use the shared `logMsg` logger from `comms.utils.log`. Use `logMsg.debug`, `logMsg.info`, `logMsg.warning`, `logMsg.error` at appropriate levels.
- Config values should be defined in the `config` dict imported from `comms.utils.settings`. Configuration values should not be hard-coded.
- Please use British English in docstrings, comments, and user-facing messages.

## Adding a new command
1. Create `src/comms/commands/<name>.py` with a `run_<name>()` function.
2. Create `src/comms/cli/<name>.py` with a Typer instance and command definition.
3. Register the Typer instance in `src/comms/cli/cli.py` via `comms.add_typer(...)`.
4. Add any new config keys to `src/comms/config.toml` with sensible defaults.
  1. If new config keys are introduced, ensure the `config_set` function and `_apply_protocol_flags` helper function in `src/comms/commands/config.py` are updated accordingly.
  2. Also ensure corresponding unit tests are created in `tests/unit/config.py`
5. Write unit tests in `tests/unit/test_<name>.py` covering the business logic in isolation.
6. Write integration tests in `tests/integration/test_<name>.py` if the command wraps an external binary.

## Submitting changes
1. Fork the repository and create a branch from `main`.
2. Make your changes, ensuring the test suite passes.
3. Open a pull request with a clear description of what the change does and why.

Please raise an issue before starting work on large changes so that the approach can be discussed first.

<!-- MARKDOWN LINKS & IMAGES -->
[crux-url]: https://crux.ms
[readme-link]: ./README.md
[trfp-url]: https://github.com/compomics/ThermoRawFileParser