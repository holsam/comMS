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
    - [GUI fixtures](#gui-fixtures)
- [Synthetic fixture generator](#synthetic-fixture-generator)
    - [Running standalone](#running-standalone)
    - [Synthetic proteome](#synthetic-proteome)
    - [Synthetic mzML](#synthetic-mzml)
    - [Mass calculations](#mass-calculations)
    - [Real `.RAW` fixture](#real-raw--fixture)
- [Unit tests](#unit-tests)
    - [`tests/unit/test_config.py`](#testsunittest_configpy)
    - [`tests/unit/test_context.py`](#testsunittest_contextpy)
    - [`tests/unit/test_experiment.py`](#testsunittest_experimentpy)
    - [`tests/unit/test_fasta.py`](#testsunittest_fastapy)
    - [`tests/unit/test_lfq.py`](#testsunittest_lfqpy)
    - [`tests/unit/test_parammedic.py`](#testsunittest_parammedicpy)
    - [`tests/unit/test_paths.py`](#testsunittest_pathspy)
    - [`tests/unit/test_report.py`](#testsunittest_reportpy)
    - [`tests/unit/test_rescore.py`](#testsunittest_rescorepy)
    - [`tests/unit/test_samples.py`](#testsunittest_samplespy)
    - [`tests/unit/test_settings.py`](#testsunittest_settingspy)
    - [`tests/unit/test_uninstall.py`](#testsunittest_uninstallpy)
    - [`tests/unit/test_validate.py`](#testsunittest_validatepy)
    - [`tests/unit/test_version.py`](#testsunittest_versionpy)
    - [`tests/unit/gui/test_gui_models.py`](#testsunitguitest_gui_modelspy)
    - [`tests/unit/gui/test_gui_panels.py`](#testsunitguitest_gui_panelspy)
    - [`tests/unit/gui/test_gui_status.py`](#testsunitguitest_gui_statuspy)
    - [`tests/unit/gui/test_gui_widgets.py`](#testsunitguitest_gui_widgetspy)
- [Integration tests](#integration-tests)
    - [`tests/integration/test_convert.py`](#testsintegrationtest_convertpy)
    - [`tests/integration/test_crux.py`](#testsintegrationtest_cruxpy)
    - [`tests/integration/test_pipeline.py`](#testsintegrationtest_pipelinepy)
    - [`tests/integration/test_trfp.py`](#testsintegrationtest_trfppy)
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
`isolated_config_dir(tmp_path, monkeypatch)` | Monkeypatches `globalConfigPath()` in both `settings` and `config` modules to point at a temporary directory, so tests don't access the real OS config file

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

### GUI fixtures
`QT_QPA_PLATFORM=offscreen` is set at the top of `conftest.py` so Qt widgets can be constructed and painted without a display

Fixture | Description
-- | --
`qapp` | Session-scoped `QApplication` (created with `QApplication.instance() or QApplication([])`) so GUI widgets can be built in tests; requested via `pytestmark = pytest.mark.usefixtures('qapp')` at the top of each GUI test module

### Experiment context fixtures

A bare experiment context is provided for the command-level integration tests, which now receive an ExperimentContext rather than a raw output directory.

Fixture | Description
-- | --
`experiment_ctx(tmp_path)` | Returns ExperimentContext.resolve(tmp_path): an experiment context rooted at tmp_path with no experiment.toml, so config resolves to the bundled defaults and bin_dir is None

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

Class | Test description
-- | --
`TestLoadDefaultConfig` | returns a dict; contains expected top-level sections; search section has required keys; `fragment_tolerance_da` key has been removed; key values have correct types; default score function is xcorr; default mz_bin_width is high-res; default fixed_mods does not contain carbamidomethyl
`TestFlatten` | flat dict unchanged; nested dict flattened; deeply nested; mixed depth; empty dict; default config flattens without error
`TestConfigCheck` | returns `True`/`False` correctly for exists/absent file under both `exists=True` and `exists=False` modes
`TestWriteLoadConfig` | round-trip preserves content; raises `FileNotFoundError` when no config present
`TestApplyMod` | adds mod to empty spec; adds to existing spec; prepends mod; duplicate entry not added; removal with exclusive pattern; exclusive pattern replaces on add; no leading/trailing commas; no double commas; empty mod with no pattern is no-op; removal of absent mod is no-op
`TestApplyIodo` | adds carbamidomethyl to empty and non-empty `fixed_mods` string; prepends; removes carbamidomethyl; no-op when not present; idempotent; result has no count prefix; no leading/trailing commas; no double commas
`TestApplyCustom` | adds entry to empty string; adds to existing; empty string clears all; duplicate not added; managed Met/Cys/phos mods rejected with warning; unmanaged entry accepted; no leading/trailing commas
`TestApplyOrganism` | sets organism section; replaces existing; does not touch other sections; empty dict clears; returns cfg
`TestApplyProtocolFlags` | iodo/low_res/mbr None leaves keys unchanged; low_res True/False sets bin width and score function; combined iodo+low_res; only relevant keys touched; non-search sections untouched
`TestApplyProtocolFlagsMods` | iodo True/False writes to `fixed_mods`, not `mods_spec`; ox/phos/n_cyc/n_ace True adds correct mod to correct key; False removes; None is no-op; n_cyc/n_ace do not touch mods_spec; ox and iodo coexist across different keys; iodo does not remove ox; all flags None changes nothing
`TestParseOrganismArg` | single and multiple pairs; strips whitespace; preserves regex chars; raises `SystemExit` on no `=`, empty key, empty pattern; returns dict; empty list returns empty dict; `=` in pattern preserved
`TestConfigInit` | creates config file; file is valid TOML; does not overwrite existing
`TestConfigExists` | exits nonzero when absent; does not raise when present
`TestConfigVerify` | valid config passes; missing key exits nonzero; exits nonzero when no config
`TestConfigReset` | `--force` restores defaults; without force prompts; confirms and resets on accept
`TestConfigSet` | creates config if absent; created config is valid TOML; all named mod flags add/remove correct mod in correct key; idempotent for ox/phos/n_cyc/n_ace; n_cyc/n_ace do not change mods_spec; custom adds entry; custom is additive; custom empty string clears; custom managed mod not added; iodo flags unchanged from original tests; low_res/organism/mbr unchanged from original tests; combined flags work together; no-flags exits nonzero; all unrelated config keys unchanged after set
`TestResolveConfigTarget` | None resolves to the global user config path; "global"/"GLOBAL" resolve case-insensitively to the global path; any other string is returned verbatim as a Path
`TestConfigSetLocalTarget` | writes to the supplied local path and produces valid TOML; the global user config is left untouched when a local target is given


---

### `tests/unit/test_context.py`
Unit tests covering `src/comms/utils/context.py`.

Class | Test description
--  | --
`TestNormaliseDirs` | a plain root returns `(root, root/comms)`; a path whose final component is `comms` returns `(parent, comms)`; a directory containing `experiment.toml` directly is treated as a `comms` directory and returns `(parent, dir)`
`TestResolve` | with no `experiment.toml` present, config falls back to the bundled default, `bin_dir` is `None`, and root equals the input directory; a local `comms/config.toml` is preferred and `config_source` begins with `"local"`; a `bin_dir` set in `experiment.toml` is parsed to a `Path` and exposed on the context
`TestStoredInputs` | each stored-input `@property` (`data_files`, `database`, `sample_sheet`, `organism_prefix`, `ref_info`, `cont_csv`) returns the correct typed value when the corresponding `metadata` key is present, and `None` / empty list when absent; properties are **not** constructor parameters — they are read from `self.metadata`
`TestResultsDir` | returns the canonical `<root>/comms/results/<command>` path; the path is correct even when the directory does not yet exist
`TestChoose` | override is returned when given; a warning containing the label is logged when override differs from stored; no warning when override equals stored; stored is returned when no override; raises `SystemExit` when neither is supplied; raises `SystemExit` when resolved path is missing and `must_exist=True`; returns a non-existent path without raising when `must_exist=False`
`TestCheckFiles` | all-existing files returns a `list[Path]` equal to the inputs (not `True`); a missing file raises `SystemExit`; empty input returns an empty list (not `True`)
`TestResolveDataFiles` | stored list returned when no override; override wins and a warning is logged when it differs from stored; raises `SystemExit` when neither stored nor override is present; raises `SystemExit` when any file is missing; result is a `list[Path]`
`TestResolveMzmlFiles` | explicit override list returned directly; raises when override file missing; globs `*.mzML` and `*.mzML.gz` from the convert results directory when no override; raises when no files found in convert directory
`TestResolveSingleFileInputs` | `resolve_database` and `resolve_sample_sheet` return stored value; override wins with warning; raises when neither supplied; raises when resolved file is missing
`TestResolveOrganismPrefix` | stored prefix returned; override wins with warning; raises when neither is available; return type is `str`

---

### `tests/unit/test_experiment.py`
Unit tests covering `src/comms/commands/experiment.py` and the main-window close log. The launch tests mock `comms.gui.app.run_app` so no event loop runs; the close-logging tests use the `qapp` fixture.

Class | Test description
-- | --
`TestLaunchExperimentGui` | exits with `run_app`'s return code; logs a launch message; `logMsg` instance is named `'experiment'`
`TestMainWindowCloseLogging` | closing the window logs a message containing "closed"; `logMsg` instance is named `'experiment'`
`TestRunExperimentHeadless` | with `typer.prompt`/`typer.confirm` patched and a temporary `.mzML` file, writes `sample_sheet.tsv`, `config.toml` and `experiment.toml` under `<base>/comms/`; the prompt sequence now includes the database FASTA prompt (between bin-dir and treatments) and an explicit data-file list via `_prompt_list('data file')` (between the input directory and per-file assignment); requires at least one treatment and one fraction (exits non-zero otherwise); records a `bin_dir` in `experiment.toml` only when one is supplied

---

### `tests/unit/test_fasta.py`
Unit tests covering `src/comms/utils/fasta.py`. No external binaries are required.

Class | Test description
-- | --
`TestReadFasta` | returns a list; single entry returns one item; multi-entry returns correct count; entry is a two-element list; header does not contain leading `>`; header content is correct; sequence content is correct; wrapped sequences are joined into a single string with no newlines; empty sequence returns `''`; multi-entry order is preserved
`TestWriteFasta` | creates file at specified path; headers are prefixed with `>`; header and sequence are on separate lines; all entries present after multi-entry write; round-trips correctly via `readFasta`
`TestSearchHeaderForTag` | returns `True` on match; returns `False` on no match; adds matching entry to the correct organism key; creates key on first match; appends to existing key; uses regex matching (anchored patterns do not match longer strings); assigns entry to the first matching tag only
`TestSplitFastaByOrganism` | returns `dict[str, Path]`; one key per organism (contaminants key absent); sub-FASTAs contain only the correct organism's proteins; contaminants are appended to all organism sub-FASTAs; output files exist on disk; output files use `.fa` extension; files are named `<label>.fa`; no crash when no contaminants are present; empty FASTA returns `{}`

---

### `tests/unit/test_lfq.py`
Unit tests covering `_groupPsmsByFraction` in `src/comms/commands/lfq.py`. No external binaries are required.

Class | Test description
-- | --
`TestGroupPsmsByFraction` | returns a `dict`; groups files into three fractions correctly; each fraction key maps to the correct subset of PSM file paths; values are lists of `Path` objects; the returned paths match the input paths; single-fraction input produces a dict with one key containing all files; a PSM file with no matching sample sheet row is excluded from all groups; known files are still grouped correctly when an unmatched file is also present; all files unmatched returns `{}`; empty PSM list returns `{}`; empty sample sheet returns `{}`; files whose `raw_file` column includes `.RAW` extension match correctly after suffix stripping; files whose `raw_file` column includes `.mzML` extension match correctly after suffix stripping; files whose `raw_file` column has no extension match the PSM stem directly

---

### `tests/unit/test_parammedic.py`
Unit tests covering `_parseParamMedicOutput` and `_runParamMedic` in `src/comms/commands/search.py`. No external binaries are required; `cruxutil.paramMedic` is mocked throughout `TestRunParamMedic`.

Class | Test description
-- | --
`TestParseParamMedicOutput` | returns `(None, None)` when output file is absent; parses well-formed output correctly; handles precursor-only or bin-width-only files; returns `(None, None)` for empty or malformed files; is case-insensitive; returns `float` types for both values
`TestRunParamMedic` | single file returns that file's values; odd and even file counts return the correct median; all-`None` parse results return `(None, None)`; mixed `None` and valid values exclude `None` from the median; `paramMedic` is called once per file; files where `paramMedic` returns `False` are excluded from estimates; per-file output subdirectories are created under a `param-medic/` directory

---

### `tests/unit/test_paths.py`
Unit tests covering `src/comms/utils/paths.py`:

Class | Test description
-- | --
`TestGenerateOutputFileStructure` | creates the expected `comms/results/<command>/` subdirectory; creates directories if absent; returns existing path unchanged if already correct; works for all supported commands
`TestCheckUniqueFileName` | returns expected base name when no conflict; increments suffix on conflict; increments correctly through multiple conflicts; correct naming patterns for all commands (`search`, `quantify`, `rescore`, `report`); returned path is within `out_dir`
`TestRepoBinDir` | an explicit `experiment_bin_dir` takes precedence over everything and is returned unchanged; explicit value beats `COMMS_BIN_DIR` even when both are set; `COMMS_BIN_DIR` is used when no explicit value is given; falls back to repo-root `bin/` path when neither is set; `experiment_bin_dir=None` is equivalent to omitting the argument; returns a `Path` object

---

### `tests/unit/test_report.py`
Unit tests covering `src/comms/commands/report.py`:

Class | Test description
-- | --
`TestResolveRScript` | returns a `Path`; path ends with the requested script name; auxiliary scripts under `aux/` subdirectory are resolved correctly
`TestWriteIndex` | creates `index.md`; contains all section names; failed sections marked FAILED; passed sections marked ✓; parameters block is included
`TestRunReportValidation` | raises `SystemExit` when no spectral-counts files in quantify directory; raises `SystemExit` when output directory exists without `--overwrite`; raises `SystemExit` when Rscript binary is not on PATH; silently drops concordance when `--lfq-dir` absent; creates output directory; writes `index.md`; passes `lfc_threshold` and `fdr_threshold` as positional args to the `da` section; `logMsg` instance is named `'report'`

N.B. `_run_r_section` and `shutil.which` are mocked throughout — no R installation is required.

---

### `tests/unit/test_rescore.py`
Unit tests covering helper functions in `src/comms/commands/rescore.py`. No external binaries are required; tests use synthetic PSM files written directly to `tmp_path`.

Class | Test description
-- | --
`TestParseOrganismTags` | parses two-organism comma-separated string; parses single-organism string; strips internal and leading/trailing whitespace; preserves regex characters in values; raises `SystemExit` on odd item count, single item, or empty string; returns `dict[str, str]`; keys and values are strings
`TestClassifyPsmRow` | returns the correct organism label for a matching EUK row; returns the correct label for a PRO row; returns `'contaminants'` for an unmatched row; returns a string; returns `'contaminants'` for an empty row; uses the last tab-delimited column as the protein ID; first matching tag wins when multiple tags could match
`TestSplitPsmsByOrganism` | returns `True` on success; creates per-organism target files in labelled subdirectories; creates per-organism decoy files; EUK file contains only EUK rows; PRO file contains only PRO rows; contaminant rows go to a `contaminants/` bucket; header is preserved in each output file; returns a bool without raising when the target file is missing; skips a missing decoy file gracefully and still succeeds for the target; output files are non-empty

---

### `tests/unit/test_samples.py`
Unit tests covering `src/comms/utils/samples.py`:

Class | Test description
-- | --
`TestLoadSampleSheet` | loads valid TSV; correct row count; column names are lowercased; required columns present (including `fraction`); raises `ValueError` on missing column, duplicate `sample_id`, or nonexistent file; accepts CSV in addition to TSV; allows optional `batch` column; strips whitespace from column names
`TestGetSamplesByTreatment` | filters correctly; case-insensitive; returns empty DataFrame for unknown treatment; returns a copy, not a view
`TestGetSamplesByFraction` | filters correctly by fraction label; case-insensitive; returns empty DataFrame for unknown fraction; returns a copy, not a view
`TestGetRawFileMap` | maps existing files; omits missing files; returns `Path` objects

---

### `tests/unit/test_settings.py`
Unit tests covering `src/comms/utils/settings.py`:

Class | Test description
-- | --
`TestUserConfigPath` | returns a `Path`; path name is `config.toml`; parent directory is named `comms`
`TestLoadDefaultConfig` | returns a dict; idempotent; underlying file parses as valid TOML
`TestResolveConfig` | falls back to bundled default when neither a local nor a global config exists and the source label mentions the default; uses the global user config when present and the source begins with "global"; prefers a local `comms/config.toml` over the global config and the source begins with "local"
`TestConfigFallback` | loads bundled defaults when `globalConfigPath()` points to a non-existent file
`TestResolvedModsSpec` | returns string; base only when no custom; custom appended to base; custom duplicate of base not repeated; empty base returns custom only; both empty returns `C+0`; no leading/trailing commas

---

### `tests/unit/test_uninstall.py`
Unit tests covering `src/comms/commands/uninstall.py`:

Class | Test description
-- | --
`TestGeneratedTargets` | includes the global config file when it exists; returns an empty list when no config is present
`TestDetectUninstallCommand` | returns the `uv tool uninstall` command when the launching path is under a uv tools directory; returns the `pip uninstall` command when installed via pip; falls back to the unknown message when comMS is not listed in pip output; falls back to the unknown message when pip is unavailable
`TestRunUninstall` | a dry run lists targets without deleting them; `--force` deletes the global config without prompting; the logMsg instance is named `'uninstall'`

---

### `tests/unit/test_validate.py`
Unit tests covering `src/comms/utils/validate.py`:

Class | Test description
-- | --
`TestParseVersion` | parses three-part and two-part dotted version strings; parses a version embedded in a longer string; returns `None` for strings with no digits or empty strings; returns a tuple of `int`; supports comparison with version constraint tuples
`TestFindAllCrux` | returns empty list when no installations present; returns single installation; returns multiple installations; returns list of `Path` objects
`TestFindAllTrfp` | returns empty list when no installations present; finds legacy `.exe` binary; finds native binary without `.exe` extension; finds both legacy and native together; returns list of `Path` objects
`TestSelectBest` | returns `None` for empty candidate list; returns `None` when all versions unparseable; returns path and version for a single candidate; selects highest-versioned candidate from multiple; skips candidates with unparseable versions; returns `(Path, tuple)`; result is independent of candidate order
`TestGetCruxVersion` | parses well-formed `crux version` stdout; returns `None` when no "Crux version" line present; returns `None` when subprocess raises; falls back to stderr when stdout is empty
`TestGetTrfpVersion` | parses plain version string from stdout; returns `None` when output unparseable; returns `None` when subprocess raises
`TestCheckCrux` | raises `SystemExit` when no candidates found; not-found error message names all three resolution sources (experiment.toml, `COMMS_BIN_DIR`, walk-up path); raises `SystemExit` when all versions unparseable; returns correct path for single installation; returns highest-versioned path for multiple installations; logs info message when multiple installations found; no info message for single installation; raises `SystemExit` with `allow_lfq=True` when best version is below `_CRUX_MIN_LFQ`; does not raise with `allow_lfq=True` when best version meets `_CRUX_MIN_LFQ`; does not enforce minimum version when `allow_lfq=False`; `_get_crux_version` called once per candidate
`TestCheckTrfp` | raises `SystemExit` when no candidates found; raises `SystemExit` when all versions unparseable; returns correct path for single installation; returns highest-versioned path for multiple installations; prints info message when multiple installations found; no info message for single installation; does not raise when version is at Mono threshold; raises `SystemExit` when below Mono threshold on Linux without Mono; does not raise when below threshold on Linux with Mono; does not raise when below threshold on Windows; does not raise when below threshold on macOS with Mono; `_get_trfp_version` called once per candidate
`TestValidate` | returns `(None, None)` when no checks requested; does not call `_find_all_crux` when no checks requested; returns `crux_bin` and `None` when `check_crux=True` only; returns `None` and `trfp_path` when `check_trfp=True` only; returns both paths when both checks requested; raises `SystemExit` when Crux not found; raises `SystemExit` when TRFP not found; raises `SystemExit` with `allow_lfq=True` and old Crux; does not raise with `allow_lfq=True` and Crux at minimum; raises when old TRFP without Mono on Linux; does not raise when old TRFP with Mono on Linux; does not raise when old TRFP on Windows; `_find_all_crux` not called when `check_crux=False`; `_find_all_trfp` not called when `check_trfp=False`; correct `ERROR` message logged for each failure mode
`TestValidateBinDirForwarding` | `validate(bin_dir=<path>)` forwards its `bin_dir` argument to `repoBinDir` as `experiment_bin_dir`; `bin_dir=None` calls `repoBinDir(experiment_bin_dir=None)`, which falls through to env-var/walk-up resolution; the resolved bin directory is passed into `_find_all_crux` as its search root; the resolved bin directory is passed into `_find_all_trfp` as its search root

---

### `tests/unit/test_version.py`
Unit tests covering `src/comms/commands/version.py`:

Class | Test description
-- | --
`TestPrintVersion` | exits with code zero; prints the installed version string; handles `PackageNotFoundError` gracefully by printing an 'unknown' fallback message

---

### `tests/unit/gui/test_gui_models.py`
Unit tests covering `src/comms/gui/models/experiment_state.py` and `src/comms/gui/models/sample_table.py`:

Class | Test description
-- | --
`TestModelsExperimentState` | `add_treatment` returns `True` and stores the value; duplicate returns `False`; empty/whitespace returns `False`; `remove_treatment` removes; `add_fraction` stores; `groupsChanged` emitted on add; group accessors return a defensive copy
`TestSampleTableAddFiles` | appends one row per path; `sample_id` is the filename stem; `raw_file` is the filename; duplicate filenames are skipped; emits `contentChanged`
`TestSampleTableRemoveRows` | deletes a single row; deletes multiple rows
`TestSampleTableIsComplete` | empty model is incomplete; incomplete without a treatment; complete when all fields are set; duplicate `sample_id` values are incomplete
`TestTestSampleTableRenumberReplicates` | sequential within a treatment/fraction group; separate counters per group; a manual override is preserved
`TestTestSampleTableHeaderData` | the batch column is labelled "batch (optional)"; other columns use their canonical names
`TestTestSampleTableRenderSampleSheet` | header uses the canonical columns; a row is tab-joined; a `None` replicate renders as empty; output ends with a trailing newline

---

### `tests/unit/gui/test_gui_panels.py`
Unit tests covering `src/comms/gui/panels/config_panel.py`, `src/comms/gui/panels/experiment_panel.py`, `src/comms/gui/panels/sample_panel.py` and `src/comms/gui/panels/save_panel.py`:

Class | Test description
-- | --
`TestConfigPanel` | defaults to single species; organism table is disabled for single species and enabled for multispecies; single species is complete without organisms; multispecies is incomplete without organisms; incomplete with a half-filled organism row; complete with a full organism row; `_build_config` returns a dict with a `search` section; default includes Met oxidation; single species writes an empty organism section; multispecies writes the organism patterns; `changed` signal fires and the tracker becomes complete; `summary` reports the analysis type
`TestExperimentPanel` | name strips whitespace; `base_dir` is `None` when empty; `output_dir` appends `comms`; `is_valid` requires **all three** of name, base directory, and database path (tracker remains `INCOMPLETE` until all three are set); the bin-directory field is optional and does not affect `is_valid`; a supplied bin directory is written to `experiment.toml` under `[experiment].bin_dir`; an empty bin directory is omitted from metadata; `write_metadata` coerces list-valued `files` entries to lists of strings, and scalar `Path` values to plain strings
`TestSamplePanel` | `is_complete` proxies the model; `contentChanged` is re-emitted; the tracker moves from incomplete to complete; `write` creates `sample_sheet.tsv`; `data_files()` returns source paths in insertion order; `data_files()` skips rows with an empty `source_path`
`TestSavePanel` | save button disabled when incomplete; enabled when all three panels are complete (requires name, dir, **and** database on `ExperimentPanel`); `_save_all` writes the sample sheet, config and metadata together; output paths recorded under `[files]` and the experiment name under `[experiment]` in `experiment.toml`; all three trackers marked saved; the `saved` signal is emitted (`QMessageBox.information` is patched throughout)

---

### `tests/unit/gui/test_gui_status.py`
Unit tests covering `src/comms/gui/status.py`:

Class | Test description
-- | --
`TestPanelStateTracker` | starts unedited; a partial change is incomplete; a complete change is complete; `mark_saved` is saved; editing after save returns to complete; reverting to the saved signature is saved again; `statusChanged` is emitted; `is_saveable` is true for complete/saved and false for unedited/incomplete

---

### `tests/unit/gui/test_gui_widgets.py`
Unit tests covering `src/comms/gui/widgets/status_indicator.py` and
`src/comms/gui/widgets/combo_delegate.py`:

Class | Test description
-- | --
`TestStatusIndicator` | default size is 18×18; `setStatus` for every state does not raise; renders to a non-null pixmap
`TestStatusIcon` | returns a non-null `QIcon`; the icon renders at the requested pixel size
`TestGroupComboDelegate` | `createEditor` returns a `QComboBox` with a blank first item and the provider's options; options reflect live provider changes; the show-popup callback is scheduled via `QTimer.singleShot`; `setEditorData` selects the cell's current value and falls back to blank when it is not an option; `setModelData` writes the combo text back to the model

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Integration tests
Integration tests call external binaries and verify that the command-level orchestration functions behave correctly end-to-end. They use the synthetic fixtures described [above](#synthetic-file-fixtures) to avoid requiring real experimental data.

Note that these tests do not validate the 'accuracy' of either external binary, as this falls outside the remit of comMS and would be covered by the binary's respective test suite.

### `tests/integration/test_convert.py`
Integration tests covering the `run_convert` function's orchestration logic, as opposed to ThermoRawFileParser internals (which are covered in [`test_trfp.py`](#testsintegrationtest_trfppy)). All tests require ThermoRawFileParser (`pytest.mark.trfp`). Data files are supplied via the `data_files` parameter (a list of `Path` objects) rather than a directory.

The test `TestRunConvertRealFile` is gated behind `tests/fixtures/real_sample.RAW` — for more information see [above](#real-raw--fixture).

Class | Description
-- | --
`TestRunConvertNoFiles` | `run_convert` returns cleanly with a warning logged when a non-`.RAW` file is supplied; the `.RAW` filter produces an empty list and the function exits early without calling TRFP
`TestRunConvertInvalidFile` | a deliberately malformed `.RAW` file causes TRFP to exit non-zero; the failure count is captured in the log
`TestRunConvertRealFile` (optional) | verifies that the output directory is created; verifies that at least one `.mzML` file is produced; verifies that the completion summary is logged; gated behind a real `.RAW` file being present (see [above](#real-raw--fixture))

---

### `tests/integration/test_crux.py`
Integration tests covering the Crux toolkit aspects used in the comMS pipeline. All tests in this file require the Crux binary (`pytest.mark.crux`).

Class | Description
-- | -- 
`TestFindCrux` | binary exists at returned path; path is executable; returns `None` for an empty `bin/` directory.
`TestTideIndex` | creates and populates the index directory; writes a log file; returns `False` for an invalid FASTA.
`TestTideSearch` | creates the target PSM file; file has at least a header and one data row; log file is written.
`TestPercolator` | *n.b. this class is currently commented out as synthetic data does not provide sufficient PSMs for Percolator to converge; the `synthetic_percolator_results` fixture provides a hand-written PSM file at the expected path so that downstream `TestSpectralCounts` can run.*
`TestSpectralCounts` | uses the synthetic Percolator PSM fixture to bypass Percolator (which requires more PSMs than the synthetic data provides); creates a spectral-counts output file with content.

---

### `tests/integration/test_pipeline.py`
Integration tests and smoke tests that assert the pipeline stages complete without raising errors and create the expected output directories and files. All tests in this file require the Crux binary (`pytest.mark.crux`).

Class | Description
-- | -- 
`TestRunIndex` | output directory is created and non-empty; logs a completion message; `logMsg` instance is named `'index'`
`TestRunSearch` | output directory is created; target PSM file exists; logs a completion message; `logMsg` instance is named `'search'`; data files supplied as `data_files=[synthetic_mzml]`
`TestRunSearchParamMedic` | full `--param-medic` path completes without raising; search output directory and target PSM file are created; a `param-medic/` output directory is created; warns and falls back to config defaults when param-medic yields no usable estimates; summary reports numeric tolerance values; output is identical to a non-param-medic run when estimates are unavailable; data files supplied as `data_files=[synthetic_mzml]`
`TestRunSearchParamMedicMocked` | mocks `_runParamMedic` to return known values and verifies those values appear in the log summary; verifies that `(None, None)` from `_runParamMedic` falls back to config defaults without raising; data files supplied as `data_files=[synthetic_mzml]`
`TestRunRescoreDirectories` | verifies that `comms/results/rescore/` is created; verifies that per-organism subdirectories (`EUK/`, `PRO/`) are created when the real `_splitPsmsByOrganism` runs on the combined Percolator output; Percolator is mocked with a side effect that writes combined PSM files; `assignConfidence` is also mocked
`TestRunRescoreAssignConfidence` | verifies that `assignConfidence` is called once per organism (twice for a two-organism run) when both Percolator and `_splitPsmsByOrganism` are mocked with side effects that write the files each round expects to find; verifies that `run_rescore` raises `SystemExit` when Percolator fails and produces no output files, which prevents round 2 from running
`TestRunRescoreOrganismTags` | raises `SystemExit` on no PSM files in input directory; raises `SystemExit` on an invalid (odd-count) tag string; raises `SystemExit` when neither `organism_tags` nor config organism is available (monkeypatched to empty dict); uses config organism when `organism_tags` is falsy; verifies Percolator is called exactly once per file
`TestRunRescoreOutput` | success summary is printed; warning is printed when Percolator fails (and `SystemExit` is caught); warning is printed when `_splitPsmsByOrganism` returns `False`; `logMsg` instance is named `'rescore'`
`TestRunRescore` | real (unmocked) integration path with synthetic data: verifies the output directory is created (requires `organism_tags='EUK,SP'`; the directory is created after tag resolution); verifies that round-1 progress is logged even though Percolator fails on synthetic data; verifies the log file is written; `logMsg` instance is named `'rescore'`
`TestRunLfqOutputDirectories` | `run_lfq` creates one subdirectory per fraction under `comms/results/lfq/`; a single-fraction run creates exactly one subdirectory; the `comms/results/lfq/` root itself is created; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqCruxCalls` | `cruxutil.lfq` is called exactly once per fraction; each call receives only the PSM files belonging to that fraction; an orphaned PSM file with no sample sheet entry does not produce an extra call; the `fileroot` kwarg equals the fraction label for each call; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqEarlyExit` | raises `SystemExit` when the rescore directory contains no PSM files; verifies that `cruxutil.lfq` is called once per fraction even when the supplied mzML file does not match any PSM stem (`cruxutil.lfq` is mocked to return `False`)
`TestRunLfqWarnings` | a `WARNING`-level message is logged when `cruxutil.lfq` returns `False` for a fraction; processing continues for remaining fractions even when one fails; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqLogger` | the `logMsg` instance is named `'lfq'`
`TestRunQuantify` | uses `synthetic_percolator_results` fixture; output directory is created; spectral-counts file exists; logs a completion message; `logMsg` instance is named `'quantify'`
`TestRunPipeline` | full end-to-end smoke test with `--skip-convert`, `--skip-lfq` and `--skip-report` flags; data supplied as `data=[mzml]`; pipeline completes without raising; all expected stage directories (`index`, `search`, `rescore`, `quantify`) are created under `comms/results/`; `logMsg` instance is named `'pipeline'`

---

### `tests/integration/test_trfp.py`
Integration tests covering the comMS wrapper around ThermoRawFileParser. All tests require ThermoRawFileParser (`pytest.mark.trfp`). The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see more information [above](#real-raw--fixture).

Class | Description
-- | -- 
`TestFindTRFP` | returned path exists; suffix is `.exe` or none; returns `None` for an empty `bin/` directory; returns `None` for a nonexistent `bin/` directory
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