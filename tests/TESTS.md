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
- [Synthetic fixture generator](#synthetic-fixture-generator)
    - [Running standalone](#running-standalone)
    - [Synthetic proteome](#synthetic-proteome)
    - [Synthetic mzML](#synthetic-mzml)
    - [Mass calculations](#mass-calculations)
    - [Real `.RAW` fixture](#real-raw--fixture)
- [Unit tests](#unit-tests)
    - [`tests/unit/test_config.py`](#testsunittest_configpy)
    - [`tests/unit/test_download.py`](#testsunittest_downloadpy)
    - [`tests/unit/test_paths.py](#testsunittest_pathspy)
    - [`tests/unit/test_samples.py`](#testsunittest_samplespy)
    - [`tests/unit/test_settings.py`](#testsunittest_settingspy)
- [Integration tests](#integration-tests)
    - [`tests/integration/test_convert.py`](#testsintegrationtest_convertpy)
    - [`tests/integration/test_crux.py`](#testsintegrationtest_cruxpy)
    - [`tests/integration/test_pipeline.py`](#testsintegrationtest_pipelinepy)
    - [`tests/integration/test_trfp.py`](#testsintegrationtest_tfrppy)

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

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Synthetic fixture generator
A Python script to generate the necessary synthetic fixture files is provided under `tests/fixtures/generate_fixtures.py`. This script generates the two synthetic files consumed by the integration tests.

### Running standalone
 The functions in this file are importable, and will be called by `conftest.py` during testing, so there is typically no need to run the file. However it can be ran outside of testing contexts by using:
```bash
python tests/fixtures/generate_fixtures.py
```
By default, the script will write files to the directory containing the script. This can be overriden by providing a path during the initial call:
```bash
python tests/fixtures/generate_fixtures.py path/to/output/dir
```
### Synthetic proteome
The synthetic proteome is written to `synthetic_proteome.fasta`. It contains five protein sequences, each with one or two tryptic peptides which exclusively map to the source protein. The protein IDs and peptide sequences are:

Protein ID | Tryptic peptides |
---|---
SP\|PROT1\|GENE1 | ACDEFGHIK, LMNPQR
SP\|PROT2\|GENE2 | SAMPLEK
SP\|PROT3\|GENE3 | PEPTIDEFK
SP\|PROT4\|GENE4 | SYNTHETICR
SP\|PROT5\|GENE5 | VALIDATEK

### Synthetic mzML
The synthetic indexed `.mzML` file is written to `synthetic.mzML`. It is a minimal example, designed to pass through `tide-search` without error, and follows the mzML 1.1.0 standard. It contains:

Scan | Description
-- | --
1x MS1 survey scan | All precursor m/z values represented as centroid peaks
6x MS2 scans | One per target peptide, each containing a computed b/y fragment ion series

All spectra use uncompressed 32-bit float binary arrays with no compression, which is the simplest format accepted by Crux/ProteoWizard without special decoder flags.

### Mass calculations
Monoisotopic residue masses (in Daltons) used throughout the test suite fixtures are:

```
G  57.02146   A  71.03711   V  99.06841   L 113.08406
I 113.08406   P  97.05276   F 147.06841   W 186.07931
M 131.04049   S  87.03203   T 101.04768   C 103.00919
Y 163.06333   H 137.05891   D 115.02694   E 129.04259
N 114.04293   Q 128.05858   K 128.09496   R 156.10111

Masses
Proton: 1.007276 Da
Water: 18.010565 Da
Peptide mass = sum(residues) + water
[M+nH]n+ = (peptide_mass + n × proton) / n
```

b-ions and y-ions are singly charged and skip the terminal ions (b1 and y1), following the standard convention.

### Real `.RAW ` fixture
Valid synthetic `.RAW` file cannot be generated without the ThermoFisher vendor SDK, therefore integration tests which would require a `.RAW` file are gated behind the `REAL_RAW_FIXTURE` guard. To run these tests, place a valid file at:
```
tests/fixtures/real_sample.RAW
```
If this file is absent, the relevant tests are skipped automatically.

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Unit tests
Unit tests cover logic in isolation, i.e. they do not require external binaries and do not write to the local filesystem beyond `tmp_path`. All config-touching tests use the `isolated_config_dir` fixture described [above](#config-fixtures).

### `tests/unit/test_config.py`
Unit tests covering `src/comms/commands/config.py`, and indirectly `src/comms/utils/settings.py`:

Function | Test description
-- | --
`loadDefaultConfig` | return type, required top-level sections, required search keys, correct value types, correct defaults for `score_function` and `mz_bin_width`
`_flatten` | correct dot-separated key flattening at all nesting depths
`_configCheck` | correct True/False returns for both `exists=True` and `exists=False` branches
`_writeConfig`, `_loadUserConfig` | write/read preserves content; raises `FileNotFoundError` when no config exists
`config_init` | creates config file; raises on attempt to overwrite an existing file
`config_exists` | exits non-zero when absent; does not raise when present
`config_verify` | valid config passes; missing key causes non-zero exit; no config causes non-zero exit
`config_reset` | `--force` restores defaults; without `--force`, prompts; proceeds on confirmation
`_apply_iodo` | adds/removes carbamidomethylation; replaces any existing Cys mod; handles empty specs; result has no leading/trailing commas or double commas
`_apply_protocol_flags` | all flag combinations; only relevant keys are modified; all other config sections are untouched
`config_set` | auto-creates config from defaults if absent; `--iodo`, `--no-iodo`, `--high-res`, `--low-res` all behave correctly and are idempotent; combined flags work; `--no-flags` exits non-zero

### `tests/unit/test_download.py`
Unit tests covering `src/comms/utils/download.py`:

Function | Test description
-- | --
Constants | correct types, non-empty strings, valid URL templates
`_detect_platform` | returns two non-empty strings; system is a recognised value
`_resolve_bin_dir` | returns the override when supplied; falls back to `repoBinDir()` when `None`
URL construction | tarball name for each known platform key matches expected format
`download_crux` | raises `NotImplementedError` on Windows (monkeypatched); raises `RuntimeError` on unrecognised platform

### `tests/unit/test_paths.py`
Unit tests covering `src/comms/utils/paths.py`:

Function | Test description
-- | --
`generateOutputFileStructure` | creates the expected `comms/results/<command>/` subdirectory; creates directories if absent; returns existing path unchanged if already correct; works for all supported commands
`checkUniqueFileName` | returns expected base name when no conflict; increments suffix on conflict; increments correctly through multiple conflicts; correct naming patterns for all commands (`search`, `quantify`, `rescore`, `report`); returned path is within `out_dir`

### `tests/unit/test_samples.py`
Unit tests covering `src/comms/utils/samples.py`:

Function | Test description
-- | --
`loadSampleSheet` — loads valid TSV; correct row count; column names are lowercased; required columns present; raises `ValueError` on missing column, duplicate `sample_id`, or nonexistent file; accepts CSV in addition to TSV; allows optional `batch` column; strips whitespace from column names
`getSamplesByTreatment` — filters correctly; case-insensitive; returns empty DataFrame for unknown treatment; returns a copy, not a view
`getRawFileMap` — maps existing files; omits missing files; returns `Path` objects

### `tests/unit/test_settings.py`
Unit tests covering `src/comms/utils/settings.py`:

Function | Test description
-- | --
`userConfigPath` | returns a `Path`; name is `config.toml`; parent directory is named `comms`
`loadDefaultConfig` | returns a dict; idempotent; underlying file parses as valid TOML
Module-level `config` | is a dict; contains `search` and `percolator` sections; critical keys are not `None`

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Integration tests
Integration tests call external binaries and verify that the command-level orchestration functions behave correctly end-to-end. They use the synthetic fixtures described [above](#synthetic-file-fixtures) to avoid requiring real experimental data.

Note that these tests do not validate the 'accuracy' of either external binary, as this falls outside the remit of comMS and would be covered by the binary's respective test suite.

### `tests/integration/test_convert.py`
Integration tests covering the `run_convert` function's orchestration logic, as opposed to ThermoRawFileParser internals (which are covered in [`test_trfp.py`](#testsintegrationtest_tfrppy)). All tests require ThermoRawFileParser (`pytest.mark.trfp`).

The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see more information [above](#real-raw--fixture).

Checks | Description
-- | -- 
Empty input directory | `run_convert` returns cleanly and prints a warning
Invalid `.RAW` file | a deliberately malformed file causes TRFP to exit non-zero; the summary reports a failure
Real `.RAW` file (optional) | tests verify that the output directory is created and contains at least one `.mzML` file; gated behind a real `.RAW` file being present (see [above](#real-raw--fixture))

### `tests/integration/test_crux.py`
Integration tests covering the Crux toolkit aspects used in the comMS pipeline. All tests in this file require the Crux binary (`pytest.mark.crux`).

Test | Description
-- | -- 
`TestFindCrux` | binary exists at returned path; path is executable; returns `None` for an empty `bin/` directory.
`TestTideIndex` | creates and populates the index directory; writes a log file; returns `False` for an invalid FASTA.
`TestTideSearch` | creates the target PSM file; file has at least a header and one data row; log file is written.
`TestRunRescore` | *n.b. this is currently commented out as synthetic data does not provide sufficient PSMs for Percolator to converge; the `synthetic_percolator_results` fixture provides a hand-written PSM file at the expected path so that downstream `TestSpectralCounts` can run.*
`TestSpectralCounts` | uses the synthetic Percolator PSM fixture to bypass Percolator (which requires more PSMs than the synthetic data provides); creates a spectral-counts output file with content.

### `tests/integration/test_pipeline.py`
Integration tests/smoke tests that assert the pipeline stages complete without raising errors and create the expected output directories and files. All tests in this file require the Crux binary (`pytest.mark.crux`).

Test | Description
-- | -- 
`TestRunIndex` | output directory is created and non-empty; prints a success message.
`TestRunSearch` | output directory is created; target PSM file exists; prints search summary.
`TestRunRescore` | output directory is created; prints rescore summary; log file is written. The rescore step may fail with synthetic data due to insufficient PSMs for Percolator — the test asserts on directory creation rather than success.
`TestRunQuantify` | uses synthetic Percolator results fixture; output directory is created; spectral-counts file exists; prints quantify summary.
`TestRunPipeline` | full end-to-end smoke test with `--skip-convert` and `--skip-report` to remove TRFP and Quarto dependencies; pipeline completes without raising; all expected stage directories are created under `comms/results/`.

Each test also includes a test to ensure the comMS logger was instantiated correctly.

### `tests/integration/test_tfrp.py`
Integration tests covering the comMS wrapper around ThermoRawFileParser. All tests require ThermoRawFileParser (`pytest.mark.trfp`). The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see more information [above](#real-raw--fixture).

Test | Description
-- | -- 
`TestFindTRFP` | returned path exists; suffix is `.exe`; returns `None` for an empty or nonexistent `bin/` directory
`TestConvertRawFailure` | a deliberately invalid `.RAW` file causes `convertRaw` to return `False`
`TestConvertRawRealFile` (optional) | verifies that `convertRaw` produces a non-empty `.mzML` file for a real Thermo `.RAW` input

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>