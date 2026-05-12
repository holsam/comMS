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
    - [LFQ fixtures](#lfq-fixtures)
    - [Rescore integration fixtures](#rescore-integration-fixtures)
- [Synthetic fixture generator](#synthetic-fixture-generator)
    - [Running standalone](#running-standalone)
    - [Synthetic proteome](#synthetic-proteome)
    - [Synthetic mzML](#synthetic-mzml)
    - [Mass calculations](#mass-calculations)
    - [Real `.RAW` fixture](#real-raw--fixture)
- [Unit tests](#unit-tests)
    - [`tests/unit/test_config.py`](#testsunittest_configpy)
    - [`tests/unit/test_download.py`](#testsunittest_downloadpy)
    - [`tests/unit/test_fasta.py`](#testsunittest_fastapy)
    - [`tests/unit/test_parammedic.py`](#testsunittest_parammedicpy)
    - [`tests/unit/test_paths.py`](#testsunittest_pathspy)
    - [`tests/unit/test_report.py](#testsunittest_reportpy)
    - [`tests/unit/test_rescore.py`](#testsunittest_rescorepy)
    - [`tests/unit/test_samples.py`](#testsunittest_samplespy)
    - [`tests/unit/test_settings.py`](#testsunittest_settingspy)
    - [`tests/unit/test_validate.py`](#testsunittest_validatepy)
    - [`tests/unit/test_version.py`](#testsunittest_versionpy)
- [Integration tests](#integration-tests)
    - [`tests/integration/test_convert.py`](#testsintegrationtest_convertpy)
    - [`tests/integration/test_crux.py`](#testsintegrationtest_cruxpy)
    - [`tests/integration/test_pipeline.py`](#testsintegrationtest_pipelinepy)
    - [`tests/integration/test_trfp.py`](#testsintegrationtest_tfrppy)
- [R tests](#r-tests)
    - [`tests/r/test_utils_import.R`](#testsrtest_utils_importr)
    - [`tests/r/test_utils_normalise.R`](#testsrtest_utils_normaliser)

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
`valid_sample_sheet(tmp_path)` | Two samples across two treatments with a `fraction` column (`WCL`) and optional `batch` column, one replicate each; written as TSV
`sample_sheet_missing_col(tmp_path)` | Missing the required `treatment` column; used to test validation errors
`sample_sheet_duplicate_ids(tmp_path)` | Duplicate `sample_id` values; used to test duplicate detection

### Config fixtures
Fixture | Description
---|---
`isolated_config_dir(tmp_path, monkeypatch)` | Monkeypatches `userConfigPath()` in both `settings` and `config` modules to point at a temporary directory, so tests don't access the real OS config file

### Synthetic Percolator results

Fixture | Description
---|---
`synthetic_percolator_results(tmp_path)` | Writes a minimal synthetic assign-confidence PSM file at `rescore/EUK/synthetic.EUK.assign-confidence.target.txt`, matching the per-organism subdirectory structure produced by `run_rescore` round 2 and bypassing the need to run Percolator and assign-confidence on synthetic data (which does not provide enough PSMs for Percolator to converge)

### LFQ fixtures

Fixture | Description
---|---
`valid_sample_sheet_single_fraction(tmp_path)` | Single fraction (`WCL`), two treatments; used to test the single-fraction edge case in `_groupPsmsByFraction`
`valid_sample_sheet_multiple_fractions(tmp_path)` | Three fractions (`WCL`, `ECF`, `PUR`), two treatments, one replicate each; written as TSV
`single_fraction_psm_dir(tmp_path)` | Writes two synthetic Percolator PSM files (one fraction) to `comms/results/rescore/`, matching `valid_sample_sheet_single_fraction`; returns the directory path
`multi_fraction_psm_dir(tmp_path)` | Writes six synthetic Percolator PSM files (two per fraction) to `comms/results/rescore/`, matching `valid_sample_sheet_multiple_fractions`; returns the directory path

### Rescore integration fixtures

The following fixtures are defined within `tests/integration/test_pipeline.py` for use by the rescore integration test classes.

Fixture | Description
---|---
`two_organism_fasta(tmp_path)` | Writes a combined FASTA containing one TESTEUK protein, one TESTPRO protein, and one cRAP contaminant; returns the path
`synthetic_tide_search_dir(tmp_path)` | Writes a minimal synthetic Tide-search target PSM file to `tmp_path / 'search'` and returns the directory path, bypassing the need to run `tide-search` in rescore tests

A module-level helper function `_write_per_organism_psm_files(rescore_dir, file_base, labels)` is also defined in `test_pipeline.py`. This is not a fixture but is used as a mock side effect within `TestRunRescoreMergedOutput` to write synthetic per-organism Percolator output files so that `_mergeRescoredPsms` has something to read without Percolator running.

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

Function/class | Test description
-- | --
`_flatten` | flat dict unchanged; nested dict flattened; deeply nested; mixed depth; empty dict; default config flattens without error
`_configCheck` | returns `True`/`False` correctly for exists/absent file under both `exists=True` and `exists=False` modes
`_writeConfig` / `_loadUserConfig` | round-trip preserves content; raises `FileNotFoundError` when no config present
`_apply_mod` | adds mod to empty spec; adds to existing spec; prepends mod; duplicate entry not added; removal with exclusive pattern; exclusive pattern replaces on add; no leading/trailing commas; no double commas; empty mod with no pattern is no-op; removal of absent mod is no-op
`_apply_iodo` | adds carbamidomethyl to empty and non-empty `fixed_mods` string; prepends; removes carbamidomethyl; no-op when not present; idempotent; result has no count prefix; no leading/trailing commas; no double commas
`_apply_custom` | adds entry to empty string; adds to existing; empty string clears all; duplicate not added; managed Met/phos mods rejected with warning; unmanaged entry accepted; no leading/trailing commas
`_apply_organism` | sets organism section; replaces existing; does not touch other sections; empty dict clears; returns cfg
`_apply_protocol_flags` (original) | low_res/mbr None leaves keys unchanged; low_res True/False sets bin width and score function; combined iodo+low_res; only relevant keys touched; non-search sections untouched
`_apply_protocol_flags` (new mods) | iodo True/False writes to `fixed_mods`, not `mods_spec`; ox/phos/n_cyc/n_ace True adds correct mod to correct key; False removes; None is no-op; n_cyc/n_ace do not touch mods_spec; ox and iodo coexist across different keys; iodo does not remove ox; all flags None changes nothing
`_parse_organism_arg` | single and multiple pairs; strips whitespace; preserves regex chars; raises `SystemExit` on no `=`, empty key, empty pattern; returns dict; empty list returns empty dict; `=` in pattern preserved
`config_init` | creates config file; file is valid TOML; does not overwrite existing
`config_exists` | exits nonzero when absent; does not raise when present
`config_verify` | valid config passes; missing key exits nonzero; exits nonzero when no config
`config_reset` | `--force` restores defaults; without force prompts; confirms and resets on accept
`config_set` | creates config if absent; created config is valid TOML; all named mod flags add/remove correct mod in correct key; idempotent for ox/phos/n_cyc/n_ace; n_cyc/n_ace do not change mods_spec; custom adds entry; custom is additive; custom empty string clears; custom managed mod not added; iodo flags unchanged from original tests; low_res/organism/mbr unchanged from original tests; combined flags work together; no-flags exits nonzero; all unrelated config keys unchanged after set

---

### `tests/unit/test_download.py`
Unit tests covering `src/comms/utils/download.py`:

Function/class | Test description
-- | --
Constants | correct types, non-empty strings, valid URL templates
`_detect_platform` | returns two non-empty strings; system is a recognised value
`_resolve_bin_dir` | returns the override when supplied; falls back to `repoBinDir()` when `None`
URL construction | tarball name for each known platform key matches expected format
`download_crux` | raises `NotImplementedError` on Windows (monkeypatched); raises `RuntimeError` on unrecognised platform

---

### `tests/unit/test_fasta.py`
Unit tests covering `src/comms/utils/fasta.py`. No external binaries are required.

Function/class | Test description
-- | --
`readFasta` | returns a list; single entry returns one item; multi-entry returns correct count; entry is a two-element list; header does not contain leading `>`; header content is correct; sequence content is correct; wrapped sequences are joined into a single string with no newlines; empty sequence returns `''`; multi-entry order is preserved
`writeFasta` | creates file at specified path; headers are prefixed with `>`; header and sequence are on separate lines; all entries present after multi-entry write; round-trips correctly via `readFasta`
`_searchHeaderForTag` | returns `True` on match; returns `False` on no match; adds matching entry to the correct organism key; creates key on first match; appends to existing key; uses regex matching (anchored patterns do not match longer strings); assigns entry to the first matching tag only
`splitFastaByOrganism` | returns `dict[str, Path]`; one key per organism (contaminants key absent); sub-FASTAs contain only the correct organism's proteins; contaminants are appended to all organism sub-FASTAs; output files exist on disk; output files use `.fa` extension; files are named `<label>.fa`; no crash when no contaminants are present; empty FASTA returns `{}`

---

### `tests/unit/test_lfq.py`
Unit tests covering `_groupPsmsByFraction` in `src/comms/commands/lfq.py`. No external binaries are required.

Function/class | Test description
-- | --
`_groupPsmsByFraction` | returns a `dict`; groups files into three fractions correctly; each fraction key maps to the correct subset of PSM file paths; values are lists of `Path` objects; the returned paths match the input paths; single-fraction input produces a dict with one key containing all files; a PSM file with no matching sample sheet row is excluded from all groups; known files are still grouped correctly when an unmatched file is also present; all files unmatched returns `{}`; empty PSM list returns `{}`; empty sample sheet returns `{}`; files whose `raw_file` column includes `.RAW` extension match correctly after suffix stripping; files whose `raw_file` column includes `.mzML` extension match correctly after suffix stripping; files whose `raw_file` column has no extension match the PSM stem directly

---

### `tests/unit/test_parammedic.py`
Unit tests covering `_parseParamMedicOutput` and `_runParamMedic` in `src/comms/commands/search.py`. No external binaries are required; `cruxutil.paramMedic` is mocked throughout `TestRunParamMedic`.

Function/class | Test description
-- | --
`_parseParamMedicOutput` | returns `(None, None)` when output file is absent; parses well-formed output correctly; handles precursor-only or bin-width-only files; returns `(None, None)` for empty or malformed files; is case-insensitive; returns `float` types for both values
`_runParamMedic` | single file returns that file's values; odd and even file counts return the correct median; all-`None` parse results return `(None, None)`; mixed `None` and valid values exclude `None` from the median; `paramMedic` is called once per file; files where `paramMedic` returns `False` are excluded from estimates; per-file output subdirectories are created under a `param-medic/` directory

---

### `tests/unit/test_paths.py`
Unit tests covering `src/comms/utils/paths.py`:

Function/class | Test description
-- | --
`generateOutputFileStructure` | creates the expected `comms/results/<command>/` subdirectory; creates directories if absent; returns existing path unchanged if already correct; works for all supported commands
`checkUniqueFileName` | returns expected base name when no conflict; increments suffix on conflict; increments correctly through multiple conflicts; correct naming patterns for all commands (`search`, `quantify`, `rescore`, `report`); returned path is within `out_dir`

---

### `tests/unit/test_report.py`
Unit tests covering `src/comms/commands/report.py`:

Function/class | Test description
-- | --
`_resolve_r_script` | returns a `Path`; path ends with the requested script name
`_write_index` | creates `index.md`; contains all section names; failed sections marked FAILED; passed sections marked ✓; parameters block is included
`run_report` | raises `SystemExit` when no spectral-counts files in quantify directory; raises `SystemExit` when output directory exists without `--overwrite`; raises `SystemExit` when Rscript binary is not on PATH; silently drops concordance when `--lfq-dir` absent; creates output directory; writes `index.md`; exits non-zero when any section fails; passes `lfc_threshold` and `fdr_threshold` as positional args to the `da` section; `logMsg` instance is named `'report'`

N.B. `_run_r_section` and `shutil.which` are mocked throughout — no R installation is required.

---

### `tests/unit/test_rescore.py`
Unit tests covering helper functions in `src/comms/commands/rescore.py`. No external binaries are required; tests use synthetic PSM files written directly to `tmp_path`.

Function/class | Test description
-- | --
`_parseOrganismTags` | parses two-organism comma-separated string; parses single-organism string; strips internal and leading/trailing whitespace; preserves regex characters in values; raises `SystemExit` on odd item count, single item, or empty string; returns `dict[str, str]`; keys and values are strings
`_classifyPsmRow` | returns the correct organism label for a matching EUK row; returns the correct label for a PRO row; returns `'contaminants'` for an unmatched row; returns a string; returns `'contaminants'` for an empty row; uses the last tab-delimited column as the protein ID; first matching tag wins when multiple tags could match
`_splitPsmsByOrganism` | returns `True` on success; creates per-organism target files in labelled subdirectories; creates per-organism decoy files; EUK file contains only EUK rows; PRO file contains only PRO rows; contaminant rows go to a `contaminants/` bucket; header is preserved in each output file; returns a bool without raising when the target file is missing; skips a missing decoy file gracefully and still succeeds for the target; output files are non-empty

---

### `tests/unit/test_samples.py`
Unit tests covering `src/comms/utils/samples.py`:

Function/class | Test description
-- | --
`loadSampleSheet` | loads valid TSV; correct row count; column names are lowercased; required columns present (including `fraction`); raises `ValueError` on missing column, duplicate `sample_id`, or nonexistent file; accepts CSV in addition to TSV; allows optional `batch` column; strips whitespace from column names
`getSamplesByTreatment` | filters correctly; case-insensitive; returns empty DataFrame for unknown treatment; returns a copy, not a view
`getSamplesByFraction` | filters correctly by fraction label; case-insensitive; returns empty DataFrame for unknown fraction; returns a copy, not a view
`getRawFileMap` | maps existing files; omits missing files; returns `Path` objects

---

### `tests/unit/test_settings.py`
Unit tests covering `src/comms/utils/settings.py`:

Function/class | Test description
-- | --
`userConfigPath` | returns a `Path`; name is `config.toml`; parent directory is named `comms`
`loadDefaultConfig` | returns a dict; idempotent; underlying file parses as valid TOML
Module-level `config` | is a dict; contains `search`, `percolator`, and `organism` sections; `organism` section is an empty dict by default; critical keys are not `None`
`resolvedModsSpec` | returns string; base only when no custom; custom appended to base; custom duplicate of base not repeated; empty base returns custom only; both empty returns empty string; no leading/trailing commas

---

### `tests/unit/test_validate.py`
Unit tests covering `src/comms/utils/validate.py`:

Function/class | Test description
-- | --
`_parse_version` | parses three-part and two-part dotted version strings; parses a version embedded in a longer string; returns `None` for strings with no digits or empty strings; returns a tuple of `int`; supports comparison with version constraint tuples
`_find_all_crux` | returns empty list when no installations present; returns single installation; returns multiple installations; returns list of `Path` objects
`_find_all_trfp` | returns empty list when no installations present; finds legacy `.exe` binary; finds native binary without `.exe` extension; finds both legacy and native together; returns list of `Path` objects
`_select_best` | returns `None` for empty candidate list; returns `None` when all versions unparseable; returns path and version for a single candidate; selects highest-versioned candidate from multiple; skips candidates with unparseable versions; returns `(Path, tuple)`; result is independent of candidate order
`_get_crux_version` | parses well-formed `crux version` stdout; returns `None` when no "Crux version" line present; returns `None` when subprocess raises; falls back to stderr when stdout is empty
`_get_trfp_version` | parses plain version string from stdout; returns `None` when output unparseable; returns `None` when subprocess raises
`_check_crux` | raises `SystemExit` when no candidates found; raises `SystemExit` when all versions unparseable; returns correct path for single installation; returns highest-versioned path for multiple installations; prints info message when multiple installations found; no info message printed for single installation; raises `SystemExit` with `allow_lfq=True` when best version is below `_CRUX_MIN_LFQ`; does not raise with `allow_lfq=True` when best version meets `_CRUX_MIN_LFQ`; does not enforce minimum version when `allow_lfq=False`; `_get_crux_version` called once per candidate
`_check_trfp` | raises `SystemExit` when no candidates found; raises `SystemExit` when all versions unparseable; returns correct path for single installation; returns highest-versioned path for multiple installations; prints info message when multiple installations found; no info message for single installation; does not raise when version is at Mono threshold; raises `SystemExit` when below Mono threshold on Linux without Mono; does not raise when below threshold on Linux with Mono; does not raise when below threshold on Windows; does not raise when below threshold on macOS with Mono; `_get_trfp_version` called once per candidate
`validate` | returns `(None, None)` when no checks requested; does not call `_find_all_crux` when no checks requested; returns `crux_bin` and `None` when `check_crux=True` only; returns `None` and `trfp_path` when `check_trfp=True` only; returns both paths when both checks requested; raises `SystemExit` when Crux not found; raises `SystemExit` when TRFP not found; raises `SystemExit` with `allow_lfq=True` and old Crux; does not raise with `allow_lfq=True` and Crux at minimum; raises when old TRFP without Mono on Linux; does not raise when old TRFP with Mono on Linux; does not raise when old TRFP on Windows; `_find_all_crux` not called when `check_crux=False`; `_find_all_trfp` not called when `check_trfp=False`; correct `ERROR` message printed for each failure mode

---

### `tests/unit/test_version.py`
Unit tests covering `src/comms/commands/version.py`:

Function/class | Test description
-- | --
`printVersion` | exits with code zero; prints the installed version string; handles `PackageNotFoundError` gracefully by printing an 'unknown' fallback message

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

---

### `tests/integration/test_crux.py`
Integration tests covering the Crux toolkit aspects used in the comMS pipeline. All tests in this file require the Crux binary (`pytest.mark.crux`).

Test | Description
-- | -- 
`TestFindCrux` | binary exists at returned path; path is executable; returns `None` for an empty `bin/` directory.
`TestTideIndex` | creates and populates the index directory; writes a log file; returns `False` for an invalid FASTA.
`TestTideSearch` | creates the target PSM file; file has at least a header and one data row; log file is written.
`TestRunRescore` | *n.b. this is currently skipped as synthetic data does not provide sufficient PSMs for Percolator to converge; the `synthetic_percolator_results` fixture provides a hand-written PSM file at the expected path so that downstream `TestSpectralCounts` can run.*
`TestSpectralCounts` | uses the synthetic Percolator PSM fixture to bypass Percolator (which requires more PSMs than the synthetic data provides); creates a spectral-counts output file with content.

---

### `tests/integration/test_pipeline.py`
Integration tests and smoke tests that assert the pipeline stages complete without raising errors and create the expected output directories and files. All tests in this file require the Crux binary (`pytest.mark.crux`).

Test | Description
-- | -- 
`TestRunIndex` | output directory is created and non-empty; prints a success message; `logMsg` instance is named `'index'`.
`TestRunSearch` | output directory is created; target PSM file exists; prints search summary; `logMsg` instance is named `'search'`.
`TestRunSearchParamMedic` | full `--param-medic` path completes without raising; search output directory and target PSM file are created; a `param-medic/` output directory is created; warns and falls back to config defaults when param-medic yields no usable estimates; summary reports numeric tolerance values.
`TestRunSearchParamMedicMocked` | mocks `_runParamMedic` to return known values and verifies those values appear in the terminal summary; verifies that `(None, None)` from `_runParamMedic` falls back to config defaults without raising.
`TestRunRescoreDirectories` | verifies that `comms/results/rescore/` is created; verifies that per-organism subdirectories (`EUK/`, `PRO/`) are created when the real `_splitPsmsByOrganism` runs on the combined Percolator output. Percolator is mocked with a side effect that writes combined PSM files; `assignConfidence` is also mocked
`TestRunRescoreAssignConfidence` | verifies that `assignConfidence` is called once per organism (twice for a two-organism run) when both Percolator and `_splitPsmsByOrganism` are mocked with side effects that write the files each round expects to find; verifies that `run_rescore` raises `SystemExit` when Percolator fails and produces no output files, which prevents round 2 from running
`TestRunRescoreOrganismTags` | raises `SystemExit` on no PSM files in input directory; raises `SystemExit` on an invalid (odd-count) tag string; raises `SystemExit` when neither `organism_tags` nor config organism is available (monkeypatched to empty dict); uses config organism when `organism_tags` is falsy; verifies Percolator is called exactly once per file
`TestRunRescoreOutput` | success summary is printed; warning is printed when Percolator fails (and `SystemExit` is caught); warning is printed when `_splitPsmsByOrganism` returns `False`; `logMsg` instance is named `'rescore'`
`TestRunLfqOutputDirectories` | `run_lfq` creates one subdirectory per fraction under `comms/results/lfq/`; a single-fraction run creates exactly one subdirectory; the `comms/results/lfq/` root itself is created
`TestRunLfqCruxCalls` | `cruxutil.lfq` is called exactly once per fraction; each call receives only the PSM files belonging to that fraction; an orphaned PSM file with no sample sheet entry does not produce an extra call; the `fileroot` kwarg equals the fraction label for each call
TestRunLfqEarlyExit` | raises `SystemExit` when the rescore directory contains no PSM files; verifies that `cruxutil.lfq` is called once per fraction even when the mzML directory is empty
`TestRunLfqWarnings` | a `WARNING`-level message is logged when `cruxutil.lfq` returns `False` for a fraction; processing continues for remaining fractions even when one fails
`TestRunLfqLogger` | the `logMsg` instance is named `'lfq'`
`TestRunQuantify` | uses `synthetic_percolator_results` fixture; output directory is created; spectral-counts file exists; prints quantify summary; `logMsg` instance is named `'quantify'`
`TestRunPipeline` | full end-to-end smoke test with `--skip-convert` and `--skip-report` to remove TRFP and Quarto dependencies; pipeline completes without raising; all expected stage directories (`index`, `search`, `rescore`, `quantify`) are created under `comms/results/`; `logMsg` instance is named `'pipeline'`

---

### `tests/integration/test_tfrp.py`
Integration tests covering the comMS wrapper around ThermoRawFileParser. All tests require ThermoRawFileParser (`pytest.mark.trfp`). The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see more information [above](#real-raw--fixture).

Test | Description
-- | -- 
`TestFindTRFP` | returned path exists; suffix is `.exe` or none; returns `None` for an empty or nonexistent `bin/` directory
`TestConvertRawFailure` | a deliberately invalid `.RAW` file causes `convertRaw` to return `False`
`TestConvertRawRealFile` (optional) | verifies that `convertRaw` produces a non-empty `.mzML` file for a real Thermo `.RAW` input

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## R tests
R unit tests live under `tests/r/` and use the `testthat` framework. Run with:
```bash
Rscript -e "testthat::test_dir('tests/r')"
```

### `tests/r/test_utils_import.R`
Tests covering `src/comms/r/utils/import.R`. 

Function | Test description
-- | --
`loadRefInfo` | returns a `tbl_df`; has `proteinId`, `proteinAnnotation`, and `proteinLength` columns; raises an error for a non-existent path
`loadContInfo` | returns a tibble with a `proteinId` column
`loadSpectralCounts` | removes contaminant proteins; retains non-contaminant proteins; attaches `proteinAnnotation` via ref info join; retains the `dNSAF` column
`mergeResults` | produces a wide tibble with one `dNSAF_<sample>` column per sample; fills proteins absent from a sample with `0`; preserves `proteinId` and `proteinAnnotation` columns

Fixtures used write synthetic files to `tempdir()`
- `make_sc_file` writes a two-protein spectral-counts file (`Mtrun001`, `Mtrun002`) plus one contaminant (`CONT001`), containing only `proteinId` and `dNSAF` columns as Crux produces.
- `make_ref_info` covers both non-contaminant protein IDs with full annotation columns.
- `make_cont_csv` contains `CONT001` only.

---

### `tests/r/test_utils_normalise.R`
Tests covering `src/comms/r/utils/normalise.R`.

Function | Test description
-- | --
`logdNSAF` | returns no `-Inf` values when epsilon is applied to zero entries; non-zero values are log-transformed correctly; accepts a custom epsilon value
`medianShiftNormalise` | leaves single-sample fractions unchanged; aligns within-fraction medians across two samples; does not modify values belonging to a different fraction

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>