# comMS test suite
This document outlines the comMS test suite: its structure, shared fixtures, and what each module covers.

## Contents
- [Running the test suite](#running-the-test-suite)
- [Test markers](#test-markers)
- [Shared fixtures](#shared-fixtures)
    - [Binary availability fixtures](#binary-availability-fixtures)
    - [Synthetic file fixtures](#synthetic-file-fixtures)
    - [Sample sheet fixtures](#sample-sheet-fixtures)
    - [Config fixtures](#config-fixtures)
    - [Synthetic Percolator results](#synthetic-percolator-results)

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

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

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

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

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Shared fixtures
Shared fixtures are defined in `tests/conftest.py` and are described below.

### Binary availability fixtures
Two session-scoped fixtures are defined to locate external binaries, which both use the same regular expression/globbing logic as the source code. If a binary is absent, any test depending on that fixture will be skipped.

Fixture | Description
-- | --
`crux_bin` | Resolves to Crux binary path under `bin/`; requires `pytest.mark.crux`
`trfp_exe` | Resolves to `ThermoRawFileParser.exe` under `bin`; requires `pytest.mark.trfp`

### Synthetic file fixtures
Fixture | Description 
---|---
`synthetic_fasta(tmp_path)` | Writes `synthetic_proteome.fasta` to a temporary directory and returns its path
`synthetic_mzml(tmp_path)` | Writes `synthetic.mzML` to a temporary directory and returns its path
`synthetic_fixtures(tmp_path)` | Writes both files to the same temporary directory; returns `(fasta_path, mzml_path)`

### Sample sheet fixtures
Fixture | Description
---|---
`valid_sample_sheet(tmp_path)` | Two samples across two treatments, one replicate each; written as TSV
`sample_sheet_missing_col(tmp_path)` | Missing the required `treatment` column; used to test validation errors
`sample_sheet_duplicate_ids(tmp_path)` | Duplicate `sample_id` values; used to test duplicate detection

### Config fixtures
Fixture | Description
---|---
`isolated_config_dir(tmp_path, monkeypatch)` | Monkeypatches `userConfigPath()` in both `settings` and `config` modules to point at a temporary directory, so tests don't access the real OS config file

### Synthetic Percolator results

Fixture | Description
---|---
`synthetic_percolator_results(tmp_path)` | Writes a minimal synthetic Percolator PSM file at the expected path, bypassing the need to run Percolator on synthetic data (which does not provide enough PSMs for Percolator to converge); shared between `test_crux.py` and `test_pipeline.py`