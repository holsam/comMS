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
    - [`tests/unit/test_rescore.py`](#testsunittest_rescorepy)
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
`synthetic_percolator_results(tmp_path)` | Writes a minimal synthetic Percolator PSM file at the expected path, bypassing the need to run Percolator on synthetic data (which does not provide enough PSMs for Percolator to converge); shared between `test_crux.py` and `test_pipeline.py`

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

### `tests/unit/test_rescore.py`
Unit tests covering helper functions in `src/comms/commands/rescore.py`. No external binaries are required; tests use synthetic PSM files written directly to `tmp_path`.

Function/class | Test description
-- | --
`_parseOrganismTags` | parses two-organism comma-separated string; parses single-organism string; strips internal and leading/trailing whitespace; preserves regex characters in values; raises `SystemExit` on odd item count, single item, or empty string; returns `dict[str, str]`
`_mergeTypeRescoredPsms` | returns a list; all elements end with `\n`; first element is the modified header prefixed with `organism\t`; header appears exactly once; data rows are prefixed with the organism label; rows from both organisms are present; works for both `target` and `decoy` match types
`_mergeRescoredPsms` | returns `True` on success; returns `False` when an input file is missing; writes both `target` and `decoy` merged files; merged files are non-empty; merged file content is valid text

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
`TestRunRescoreDirectories` | verifies that `comms/results/rescore/` is created; verifies that per-organism subdirectories (`EUK/`, `PRO/`) are created for a two-organism run. Both Percolator and `_mergeRescoredPsms` are mocked.
`TestRunRescoreMergedOutput` | verifies that `<file_base>.percolator.target.psms.txt` and `<file_base>.percolator.decoy.psms.txt` are written at the top level of the rescore directory. Percolator is mocked with a side effect that writes synthetic per-organism PSM files.
`TestRunRescoreOrganismTags` | raises `SystemExit` on no PSM files in input directory; raises `SystemExit` on an invalid (odd-count) tag string; raises `SystemExit` when neither `org_tags` nor config organism is available; uses config organism when `org_tags` is falsy (monkeypatched); verifies Percolator is called exactly once per organism per file.
`TestRunRescoreOutput` | success summary is printed; warning is printed when Percolator fails for a file; warning is printed when merge fails; `logMsg` instance is named `'rescore'`.
`TestRunLfqOutputDirectories` | `run_lfq` creates one subdirectory per fraction under `comms/results/lfq/`; a single-fraction run creates exactly one subdirectory; the `comms/results/lfq/` root itself is created
`TestRunLfqCruxCalls` | `cruxutil.lfq` is called exactly once per fraction; each call receives only the PSM files belonging to that fraction; an orphaned PSM file with no sample sheet entry does not produce an extra call; the `fileroot` kwarg equals the fraction label for each call
`TestRunLfqMbrFlag` | `mbr=True` is forwarded as `match_between_runs=True` to `cruxutil.lfq`; `mbr=False` is forwarded as `match_between_runs=False`
`TestRunLfqEarlyExit` | raises `SystemExit` when the rescore directory contains no PSM files; raises `SystemExit` when the mzML directory contains no mzML files
`TestRunLfqWarnings` | a `WARNING`-level message is logged when `cruxutil.lfq` returns `False` for a fraction; processing continues for remaining fractions even when one fails
`TestRunLfqLogger` | the `logMsg` instance is named `'lfq'`
`TestRunQuantify` | uses `synthetic_percolator_results` fixture; output directory is created; spectral-counts file exists; prints quantify summary; `logMsg` instance is named `'quantify'`.
`TestRunPipeline` | full end-to-end smoke test with `--skip-convert` and `--skip-report` to remove TRFP and Quarto dependencies; pipeline completes without raising; all expected stage directories (`index`, `search`, `rescore`, `quantify`) are created under `comms/results/`; `logMsg` instance is named `'pipeline'`.

---

### `tests/integration/test_tfrp.py`
Integration tests covering the comMS wrapper around ThermoRawFileParser. All tests require ThermoRawFileParser (`pytest.mark.trfp`). The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see more information [above](#real-raw--fixture).

Test | Description
-- | -- 
`TestFindTRFP` | returned path exists; suffix is `.exe`; returns `None` for an empty or nonexistent `bin/` directory
`TestConvertRawFailure` | a deliberately invalid `.RAW` file causes `convertRaw` to return `False`
`TestConvertRawRealFile` (optional) | verifies that `convertRaw` produces a non-empty `.mzML` file for a real Thermo `.RAW` input

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>