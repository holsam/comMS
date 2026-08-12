# comMS test suite
This document outlines the comMS test suite: its structure, shared fixtures, and what each module covers.

## Contents
- [Running the test suite](#running-the-test-suite)
- [Test markers](#test-markers)
- [Shared fixtures](#shared-fixtures)
    - [Bin directory and binary availability fixtures](#bin-directory-and-binary-availability-fixtures)
    - [Synthetic file fixtures](#synthetic-file-fixtures)
    - [Sample sheet fixtures](#sample-sheet-fixtures)
    - [Config fixtures](#config-fixtures)
    - [Synthetic Percolator results](#synthetic-percolator-results)
    - [PSM directory fixtures](#psm-directory-fixtures)
    - [GUI fixtures](#gui-fixtures)
    - [Experiment context fixtures](#experiment-context-fixtures)
    - [Experiment builder fixture](#experiment-builder-fixture)
    - [Rescore/crux integration fixtures](#rescorecrux-integration-fixtures)
- [Synthetic fixture generator](#synthetic-fixture-generator)
    - [Running standalone](#running-standalone)
    - [Synthetic proteome](#synthetic-proteome)
    - [Synthetic mzML](#synthetic-mzml)
    - [Mass calculations](#mass-calculations)
    - [Real `.RAW` fixture](#real-raw--fixture)
- [Unit tests](#unit-tests)
    - [`tests/unit/test_config.py`](#testsunittest_configpy)
    - [`tests/unit/test_modspec.py`](#testsunittest_modspecpy)
    - [`tests/unit/test_context.py`](#testsunittest_contextpy)
    - [`tests/unit/test_experiment.py`](#testsunittest_experimentpy)
    - [`tests/unit/test_fasta.py`](#testsunittest_fastapy)
    - [`tests/unit/test_installrdeps.py`](#testsunittest_installrdepspy)
    - [`tests/unit/test_lfq.py`](#testsunittest_lfqpy)
    - [`tests/unit/test_license.py`](#testsunittest_licensepy)
    - [`tests/unit/test_parammedic.py`](#testsunittest_parammedicpy)
    - [`tests/unit/test_paths.py`](#testsunittest_pathspy)
    - [`tests/unit/test_readiness.py`](#testsunittest_readinesspy)
    - [`tests/unit/test_report.py`](#testsunittest_reportpy)
    - [`tests/unit/test_rescore.py`](#testsunittest_rescorepy)
    - [`tests/unit/test_samples.py`](#testsunittest_samplespy)
    - [`tests/unit/test_settings.py`](#testsunittest_settingspy)
    - [`tests/unit/test_sheet.py`](#testsunittest_sheetpy)
    - [`tests/unit/test_uninstall.py`](#testsunittest_uninstallpy)
    - [`tests/unit/test_validate.py`](#testsunittest_validatepy)
    - [`tests/unit/test_version.py`](#testsunittest_versionpy)
    - [`tests/unit/gui/test_gui_models.py`](#testsunitguitest_gui_modelspy)
    - [`tests/unit/gui/test_gui_panels.py`](#testsunitguitest_gui_panelspy)
    - [`tests/unit/gui/test_gui_readiness.py`](#testsunitguitest_gui_readinesspy)
    - [`tests/unit/gui/test_gui_status.py`](#testsunitguitest_gui_statuspy)
    - [`tests/unit/gui/test_gui_widgets.py`](#testsunitguitest_gui_widgetspy)
- [Integration tests](#integration-tests)
    - [`tests/integration/test_convert.py`](#testsintegrationtest_convertpy)
    - [`tests/integration/test_crux.py`](#testsintegrationtest_cruxpy)
    - [`tests/integration/test_pipeline.py`](#testsintegrationtest_pipelinepy)
    - [`tests/integration/test_trfp.py`](#testsintegrationtest_trfppy)
- [R tests](#r-tests)
    - [`tests/r/helper.R`](#testsrhelperr)
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
| `crux` | Requires the Crux binary under `tests/bin/` |
| `trfp` | Requires ThermoRawFileParser under `tests/bin/` |

Tests decorated with these markers are skipped automatically (with a message) if the corresponding binary is not found, and the rest of the suite continue unaffected. To run only unmarked tests (i.e. those with no external dependency):

```bash
uv run pytest -m "not crux and not trfp"
```

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Shared fixtures
Shared fixtures are defined in `tests/conftest.py` and are described below.

### Bin directory and binary availability fixtures
A session-scoped, autouse fixture (`_comms_bin_dir_env`) sets the `COMMS_BIN_DIR` environment variable to `tests/bin` for the whole test session, so every test — not just those requesting `crux_bin`/`trfp_exe` directly — resolves binaries against the bundled test `bin/` directory rather than a real installation.

Two session-scoped fixtures locate external binaries within that directory, mirroring the resolution logic in `comms.utils.crux.findCrux` and `comms.utils.trfp.findTRFP`. If a binary is absent, any test depending on that fixture is skipped.

Fixture | Description
-- | --
`crux_bin` | Resolves to the highest-versioned `crux*/bin/crux` under `tests/bin/`; requires `pytest.mark.crux`
`trfp_exe` | Resolves to `*/ThermoRawFileParser(.exe)` under `tests/bin/`; requires `pytest.mark.trfp`

### Synthetic file fixtures
Fixture | Description
---|---
`synthetic_fasta(tmp_path)` | Writes `synthetic_proteome.fasta` to a temporary directory and returns its path
`synthetic_mzml(tmp_path)` | Writes `synthetic.mzML` to a temporary directory and returns its path
`synthetic_fixtures(tmp_path)` | Writes both files to the same temporary directory; returns `(fasta_path, mzml_path)`

### Sample sheet fixtures
Fixture | Description
---|---
`sample_sheet_factory(tmp_path)` | Returns a function `_make(fractions=('WCL',), batch=True)` that writes a minimal TSV sample sheet (two treatments, `MOCK`/`TREAT`, one replicate each, per given fraction) and returns its path. Replaces the old fixed `valid_sample_sheet*` fixtures, letting each test ask for exactly the fractions it needs
`sample_sheet_missing_col(tmp_path)` | Missing the required `treatment` column; used to test validation errors
`sample_sheet_duplicate_ids(tmp_path)` | Duplicate `sample_id` values; used to test duplicate detection

### Config fixtures
Fixture | Description
---|---
`isolated_config_dir(tmp_path, monkeypatch)` | Monkeypatches `globalConfigPath()` in the `settings`, `config`, and `uninstall` modules to point at a temporary directory, so tests don't touch the real OS config file

### Synthetic Percolator results
Fixture | Description
---|---
`synthetic_percolator_results(tmp_path)` | Writes a minimal synthetic Percolator PSM file at `rescore/EUK/synthetic.EUK.percolator.target.psms.txt`, matching the per-organism subdirectory structure produced by `run_rescore` round 2 and bypassing the need to run Percolator on synthetic data (which does not provide enough PSMs for convergence)

### PSM directory fixtures
Fixture | Description
---|---
`psm_dir_factory(tmp_path)` | Returns a function `_make(stems)` that writes one synthetic Percolator PSM file per given stem to `comms/results/rescore/` and returns that directory. Replaces the old fixed `single_fraction_psm_dir`/`multi_fraction_psm_dir` fixtures

### GUI fixtures
`QT_QPA_PLATFORM=minimal` is set at the top of `conftest.py` so Qt widgets can be constructed and painted without a display. A custom Qt message handler (installed at import time via `qInstallMessageHandler`) silently drops the small set of known-harmless warnings the offscreen/minimal platform plugin emits (e.g. "does not support grabbing the keyboard/mouse") and forwards everything else to stderr as Qt would by default.

Fixture | Description
-- | --
`qapp` | Session-scoped `QApplication` (created with `QApplication.instance() or QApplication([''])`) so GUI widgets can be built in tests; requested via `pytestmark = pytest.mark.usefixtures('qapp')` at the top of each GUI test module

### Experiment context fixtures
Fixture | Description
-- | --
`experiment_ctx(tmp_path, isolated_config_dir)` | Returns `ExperimentContext.resolve(tmp_path)`: an experiment context rooted at `tmp_path` with no `experiment.toml`, so config resolves to the bundled defaults and `bin_dir` is `None`. Also depends on `isolated_config_dir` so global-config fallback in tests never touches the real OS config

### Experiment builder fixture
Fixture | Description
-- | --
`experiment_builder(tmp_path, isolated_config_dir, sample_sheet_factory, psm_dir_factory)` | Returns a chainable builder for composing a `comms/` directory from only the pieces a test needs: `.with_sample_sheet(fractions, batch)` writes a sample sheet and records it under `[files]`; `.with_stage_output(stage, files)` writes placeholder output for a pipeline stage (PSM files via `psm_dir_factory` for `'rescore'`, otherwise empty placeholder files); `.with_metadata(**kwargs)` merges arbitrary sections into `experiment.toml`; `.build()` writes `experiment.toml` and returns `(root, ctx)` via `ExperimentContext.resolve`

### Rescore/crux integration fixtures
The following fixtures are defined within `tests/integration/test_pipeline.py` and `tests/integration/test_crux.py` for use by their respective integration test classes.

Fixture | Description
---|---
`two_organism_fasta(tmp_path)` | Writes a combined FASTA containing one TESTEUK protein, one TESTPRO protein, and one cRAP contaminant; returns the path
`synthetic_tide_search_dir(tmp_path)` | Writes a minimal synthetic Tide-search target PSM file to `tmp_path / 'search'` and returns the directory path, bypassing the need to run `tide-search` in rescore tests
`pipeline_index(crux_bin, tmp_path_factory)` | Module-scoped: builds one shared Tide index for all `TestRunSearch*` tests in `test_pipeline.py`, skipping the module's tests if `run_index` fails
`pipeline_search(crux_bin, pipeline_index, tmp_path_factory)` | Module-scoped: runs `run_search` once and shares `(search_dir, fasta, work)` across `TestRunRescore` tests, skipping if `run_search` fails
`built_index(crux_bin, tmp_path_factory)` | Module-scoped, in `test_crux.py`: builds one shared Tide index via `tideIndex` for all `TestTideSearch` tests
`search_results(crux_bin, built_index, tmp_path_factory)` | Module-scoped, in `test_crux.py`: runs `tideSearch` once and returns `(out_dir, target_file, fasta)`

Module-level helper functions `_write_combined_percolator_output`, `_write_split_psm_files`, and `_write_combined_psm` are also defined in `test_pipeline.py`/`test_rescore.py`. These are not fixtures but are used as mock side effects to write synthetic per-round output so that downstream logic (`_splitPsmsByOrganism`, the per-organism Percolator round) has something to read without Percolator or Tide-search actually running.

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
The synthetic proteome is written to `synthetic_proteome.fasta`. It contains five protein sequences; PROT1's sequence (`ACDEFGHIKLMNPQRSTVWYK`) is a single tryptic run yielding two of the target peptides, so that a multi-peptide protein is represented without duplicating sequence content. The protein IDs and peptide sequences are:

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
Valid synthetic `.RAW` file cannot be generated without the ThermoFisher vendor SDK, therefore integration tests which would require a `.RAW` file are gated behind the `REAL_RAW_FIXTURE` guard (a constant defined in `test_trfp.py` and imported by `test_convert.py`). To run these tests, place a valid file at:
```
tests/fixtures/real_sample.RAW
```
If this file is absent, the relevant tests are skipped automatically.

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Unit tests
Unit tests cover logic in isolation, i.e. they do not require external binaries and do not write to the local filesystem beyond `tmp_path`. All config-touching tests use the `isolated_config_dir` fixture described [above](#config-fixtures).

### `tests/unit/test_config.py`
Unit tests covering `src/comms/commands/config.py` following the config system overhaul (mod/protocol-flag logic has moved to `comms/utils/modspec.py`, covered separately below):

Class | Test description
-- | --
`TestFlatten` | flat dict unchanged; nested dict flattened; deeply nested; empty dict; the bundled default config flattens without error
`TestPrintTable` | renders without raising when current matches defaults; renders without raising when a value diverges from defaults
`TestPrintDiffSummary` | no-changes case prints a "No changes" message; a changed key shows both old and new values; multiple changes are all reported (one ✓ per change)
`TestResolveOrCreate` | `use_global=True` resolves to the global config path; `use_global=False` resolves to `<root>/comms/config.toml`; creates a defaults-derived file if none exists; raises `SystemExit` when both a bare `config.toml` and a nested `comms/config.toml` are present (ambiguous); prefers the bare config when only that is present; prompts and creates the nested config when neither is present (accepted via `_confirm`); declining the prompt exits with code 0
`TestConfigList` | prints the config path and a table (`config_list`)
`TestConfigVerify` | a config created from defaults passes; missing a required key exits non-zero; an unexpected/extra key exits non-zero
`TestConfigReset` | `--force` resets to bundled defaults without prompting; without force, prompts via `_confirm` and exits with code 0 only when declined
`TestConfigSet` | all-`None` flags returns `False` and writes nothing; a protocol flag (`iodo`) round-trips into `index.fixed_mods`; `organism` round-trips into the `organism` section; `custom` round-trips into `index.custom_mods`; direct flags (`gzip`, `threads`, `picked_protein`, `measure`, `lfc_threshold`) round-trip into their respective sections (parametrised); unrelated sections (`search`, `rescore`, `quantify`, `convert`) are untouched by an unrelated flag; a diff summary (✓) is printed after a successful set
`TestConfigSetLocalTarget` | writes to the local `<root>/comms/config.toml`, not the global user config, which remains untouched

---

### `tests/unit/test_modspec.py`
Unit tests covering `src/comms/utils/modspec.py` — the modification-spec and protocol-flag logic previously tested as part of `test_config.py`, now in its own module alongside the mod-name constants (`CARBAMIDOMETHYL_MOD`, `MET_OX_MOD`, `PHOSPHO_MOD`, `NCYC_MOD`, `NACE_MOD`) and resolution constants (`MZ_BIN_WIDTH_HIGH_RES`/`LOW_RES`, `SCORE_FUNC_HIGH_RES`/`LOW_RES`):

Class | Test description
-- | --
`TestApplyMod` | adds mod to empty spec; adds to existing spec; prepends mod; duplicate entry not added; removal via exclusive pattern; exclusive pattern replaces on add; no leading/trailing commas; removal of an absent mod is a no-op
`TestApplyIodo` | adds carbamidomethyl when `iodo=True`; removes it when `iodo=False`; `iodo=False` on an empty spec adds `C+0`; idempotent (re-applying does not duplicate)
`TestApplyCustomMod` | adds entry to empty string; empty string clears all; duplicate not added; managed mods (Met ox, carbamidomethyl, STY phospho) are rejected and silently dropped (parametrised); `MANAGED_MOD_PATTERNS` is a `dict[str, str]` of pattern to flag name
`TestApplyOrganism` | sets the `organism` section; replaces an existing one; does not touch other sections
`TestParseOrganismArg` | single and multiple `key=value` pairs; strips whitespace; raises `SystemExit` on a missing `=`, empty key, or empty pattern; empty list returns an empty dict
`TestApplyProtocolFlags` | `low_res=True`/`False` sets `mz_bin_width` and `score_function` to the low-/high-res constants; `None` flags are a no-op; **new:** `clip_met=True`/`False` sets `index.clip_n_met` as a genuine bool (never a string) and `None` is a no-op; **new:** `missed_cleavages` sets `index.missed_cleavages` and `None` is a no-op; `clip_met` and `missed_cleavages` coexist and don't disturb mod-flag handling (`ox` still writes to `mods_spec`)

---

### `tests/unit/test_context.py`
Unit tests covering `src/comms/utils/context.py`:

Class | Test description
--  | --
`TestNormaliseDirs` | a plain root returns `(root, root/comms)`; a path whose final component is `comms` returns `(parent, comms)`; a directory containing `experiment.toml` directly is treated as a `comms` directory and returns `(parent, dir)`
`TestResolve` | with no `experiment.toml` present, config falls back to the bundled default, `bin_dir` is `None`, and root equals the input directory; a local `comms/config.toml` is preferred and `config_source` begins with `"local"`; a `bin_dir` set in `experiment.toml` is parsed to a `Path` and exposed on the context
`TestResolveResultsInput` | delegates to `results_dir` for the default (no-override) case; `must_exist=False` suppresses the existence check even though the directory doesn't exist; an explicit override wins over the computed path
`TestResolveReport` | `report_enabled=True` and no override means do-not-skip (`resolve_report` returns `False`); `report_enabled=False` means skip (`True`); `report_enabled=None` (unset) defaults to do-not-skip; an override agreeing with the context logs no warning; an override disagreeing with the context wins and logs a warning; the polarity is pinned explicitly — `resolve_report` returns *skip*, not *enabled*
`TestExperimentContextProperties` | each stored-input `@property` (`data_files`, `database`, `sample_sheet`, `analysis_mode`, `multispecies`, `organism_prefix`, `ref_info`, `cont_csv`, `report_enabled`) returns the correct typed value when the corresponding metadata key is present, and `None`/empty list when absent; `multispecies` falls back to checking whether `config['organism']` is non-empty when no `[experiment].analysis` mode is stored; properties are read from `self.metadata`, not constructor parameters
`TestResultsDir` | `results_dir(ctx, command)` returns the canonical `<root>/comms/results/<command>` path; correct even when the directory does not yet exist
`TestChoose` | `_choose` returns the override when given; logs a warning naming the label when override differs from stored; no warning when override equals stored; returns stored when no override; raises `SystemExit` when neither is supplied; raises `SystemExit` when the resolved path is missing and `must_exist=True`; returns a non-existent path without raising when `must_exist=False`
`TestCheckFiles` | all-existing files returns a `list[Path]` equal to the inputs (not `True`); a missing file raises `SystemExit`; empty input returns an empty list (not `True`)
`TestResolveDataFiles` | stored list returned when no override; override wins and a warning is logged when it differs from stored; raises `SystemExit` when neither stored nor override is present; raises `SystemExit` when any file is missing; result is a `list[Path]`
`TestResolveMzmlFiles` | explicit override list returned directly; raises when an override file is missing; globs `*.mzML` and `*.mzML.gz` from the convert results directory when no override; raises when no files found in the convert directory
`TestResolveSingleFileInputs` | `resolve_database` and `resolve_sample_sheet` return the stored value; override wins with a warning; raises when neither is supplied; raises when the resolved file is missing
`TestResolveOrganismPrefix` | stored prefix returned; override wins with a warning; raises when neither is available; return type is `str`

---

### `tests/unit/test_experiment.py`
Unit tests covering `src/comms/commands/experiment.py` and the main-window close log. The launch tests mock `comms.gui.app.run_app` so no event loop runs; the close-logging tests use the `qapp` fixture.

Class | Test description
-- | --
`TestLaunchExperimentGui` | exits with `run_app`'s return code; logs a launch message; `logMsg` instance is named `'experiment'`
`TestMainWindowCloseLogging` | closing the window logs a message containing "closed"; `logMsg` instance is named `'experiment'`
`TestRunExperimentHeadless` | with `typer.prompt`/`typer.confirm` patched and a temporary `.mzML` file, writes `sample_sheet.tsv`, `config.toml` and `experiment.toml` under `<base>/comms/`; the prompt sequence includes the combined database FASTA prompt (between bin-dir and treatments) and an explicit data-file list via `_prompt_list('data file')` (between the input directory and per-file assignment); records a `bin_dir` in `experiment.toml` only when one is supplied

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

### `tests/unit/test_installrdeps.py`
Unit tests covering `src/comms/utils/installrdeps.py` — checking, printing and installing the R package dependencies used by the `report` command. No R installation is required; `shutil.which`, `subprocess.run`/`Popen` are mocked throughout.

Class | Test description
-- | --
`TestCheckRDependencies` | returns `None` when `Rscript` is not on `PATH`; parses a well-formed JSON `{installed, missing}` payload from stdout; a non-zero return code returns `None`; malformed JSON returns `None`
`TestPrintDependencyTable` | only an "Installed" line is logged when nothing is missing; both "Installed" and "Missing" lines (plus the `r-utils install` hint) are logged when something is missing; nothing is logged when both lists are empty
`TestInstallRDependencies` | returns `False` when `Rscript` is not on `PATH`; streams `Popen` stdout lines to the log as they arrive and returns `True` on a zero exit code; a non-zero exit code returns `False`
`TestInstallRDependenciesTerminal` | nothing missing informs the user without prompting; something missing and the user confirms (`logMsg.input` returns `'y'`) calls `install_r_dependencies`; the user declining (`'n'`) does not call it; malformed check output logs an error without raising

---

### `tests/unit/test_lfq.py`
Unit tests covering `_groupPsmsByFraction` in `src/comms/commands/lfq.py`. No external binaries are required.

Class | Test description
-- | --
`TestGroupPsmsByFraction` | returns a `dict`; groups files into three fractions correctly; each fraction key maps to the correct subset of PSM file paths; values are lists of `Path` objects; the returned paths match the input paths; single-fraction input produces a dict with one key containing all files; a PSM file with no matching sample sheet row is excluded from all groups; known files are still grouped correctly when an unmatched file is also present; all files unmatched returns `{}`; empty PSM list returns `{}`; empty sample sheet returns `{}`; files whose `raw_file` column includes `.RAW` extension match correctly after suffix stripping; files whose `raw_file` column includes `.mzML` extension match correctly after suffix stripping; files whose `raw_file` column has no extension match the PSM stem directly

---

### `tests/unit/test_license.py`
Unit tests covering `src/comms/commands/license.py`:

Class | Test description
-- | --
`TestPrintLicense` | raises `SystemExit` with code 0; reads and pages the license file without raising (`pydoc.pager` is mocked and asserted called once)

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
`TestGenerateOutputFileStructure` | creates the expected `comms/results/<command>/` subdirectory; creates directories if absent; returns existing path unchanged if already correct; works for `convert`, `index`, `search`, `rescore`, `quantify` (parametrised)
`TestCheckUniqueFileName` | returns the expected base name when there's no conflict; increments the numeric suffix on conflict, and again through multiple conflicts; `quantify` naming (`<name>.spectral-counts.txt`); `rescore` naming (`<name>.percolator.psms.txt`); `report` naming takes a `fmt` kwarg instead of `orig_name` (`comms-report.<fmt>`); an unrecognised command still produces a usable fallback name (`comms-<command>-output...`) rather than raising; the returned path's parent is `out_dir`
`TestRepoBinDir` | an explicit `experiment_bin_dir` takes precedence over everything and is returned unchanged; explicit value beats `COMMS_BIN_DIR` even when both are set; `COMMS_BIN_DIR` is used when no explicit value is given; falls back to repo-root `bin/` path when neither is set; `experiment_bin_dir=None` is equivalent to omitting the argument; returns a `Path` object

---

### `tests/unit/test_readiness.py`
Unit tests covering `src/comms/utils/readiness.py` — the command-readiness gap calculator that backs the GUI readiness panel (and, indirectly, the CLI's pre-flight checks):

Class | Test description
-- | --
`TestMissingRequirements` | `missing_requirements(**all_true)` returns an empty gap list for every command in `COMMANDS`; a missing `has_data` flag surfaces "data files" only in `convert`/`search`/`lfq`, not `index`/`quantify`; a missing `has_crux` flag surfaces "Crux" in every Crux-dependent command (`index`, `search`, `rescore`, `lfq`, `quantify`) but not `convert`/`report`; a missing `has_trfp` flag surfaces "ThermoRawFileParser" only in `convert`; a missing `has_r_deps` flag surfaces "R dependencies" only in `report`; `pipeline`'s gap list is exactly the union of every other command's gaps; rescore requires "organism patterns" only when `multispecies=True` (pinned explicitly as a regression guard for the §1.2 assumption)

---

### `tests/unit/test_report.py`
Unit tests covering helper functions and `run_report` in `src/comms/commands/report.py`. This module now tracks and reports per-organism outcomes for each report section, not just a single pass/fail per section.

Class | Test description
-- | --
`TestResolveRScript` | returns a `Path`; path ends with the requested script name; auxiliary scripts under `aux/` (e.g. `aux/ev-markers.R`) are resolved correctly
`TestWriteIndex` | creates `index.md`; contains all section names; a failed section is marked `FAILED`; a passed section is marked with `✓`; a `partial` section (mixed per-organism outcomes) is marked `PARTIAL`; a `skipped` section is marked `SKIPPED`; per-organism outcome lines are nested under their parent section line in the rendered output; the parameters block is included
`TestRunReportValidation` | raises `SystemExit` when no spectral-counts files are in the quantify directory; raises `SystemExit` when the output directory exists without `--overwrite`; raises `SystemExit` when the `Rscript` binary is not on `PATH`; the `concordance` section is silently dropped when no `--lfq-dir` is available (falls back to the conventional `comms/results/lfq` location, and only drops the section if that's also absent); `ref_info` falls back to the value stored on the experiment context when not passed explicitly; creates the output directory and writes `index.md`; passes `lfc_threshold` and `fdr_threshold` as positional args (not kwargs) to the `da` section; `logMsg` instance is named `'report'`; a config override (e.g. `lfc_threshold`) writes a `report.config.toml` sidecar recording the overridden value, while an unmodified run (all overrides `None`) writes no sidecar
`TestReadStatus` | a missing `_status.json` returns `({}, {})`; malformed JSON returns `({}, {})`; a well-formed file returns its `organisms` and `reasons` dicts; unrecognised status values are dropped from the parsed `organisms` dict
`TestSectionStatus` | no organisms and `proc_ok=True` is `'skipped'`; no organisms and `proc_ok=False` is `'failed'`; all-`ok` organisms is `'succeeded'`; a mix of `ok`/`failed` is `'partial'`; all-`failed` is `'failed'`; all-`skipped` (none ok or failed) is `'skipped'`
`TestLogOrganismOutcomes` | logs one line per organism; includes the failure reason in parentheses when present; omits the empty parenthetical when there's no reason

---

### `tests/unit/test_rescore.py`
Unit tests covering helper functions in `src/comms/commands/rescore.py`. No external binaries are required; tests use synthetic PSM files written directly to `tmp_path`. Note the organism split now happens on **Tide-search** target/decoy output (`_splitPsmsByOrganism`, ahead of the per-organism Percolator round), not on already-rescored Percolator PSMs — the protein-ID column position is located dynamically via `_findProteinIdsIndex` rather than assumed to be the last column.

Class | Test description
-- | --
`TestParseOrganismTags` | parses two-organism comma-separated string; parses single-organism string; strips internal and leading/trailing whitespace; preserves regex characters in values; raises `SystemExit` on odd item count, single item, or empty string; returns `dict[str, str]`
`TestClassifyPsmRow` | `_classifyPsmRow(row, id_index, organism_tags)` returns a `list` for matching rows; returns `['EUK']`/`['PRO']` for matching rows; returns `['contaminants']` for an unmatched or empty row; uses the column at the supplied `id_index` for the protein ID (rather than assuming the last column); returns a list with multiple labels when the protein ID matches more than one organism tag
`TestFindProteinIdsIndex` | `_findProteinIdsIndex(header, 'protein id')` returns the correct 0-based column index for a mid-row column; returns `0` when it's the first column
`TestSplitPsmsByOrganism` | operates on a combined Tide-search target/decoy file pair; returns `True` on success; creates per-organism target and decoy files under labelled subdirectories, named `<fileroot>.<label>.tide-search.<target/decoy>.txt`; each organism's file contains only that organism's rows; contaminant rows go to a `contaminants/` subdirectory; the header row is preserved in each output file; returns a `bool` (not raising) when the target file is missing; skips a missing decoy file gracefully and still succeeds for the target; output files are non-empty; with `shared_policy='drop'`, rows matching more than one organism tag are excluded from all output files; with `shared_policy='include'`, such rows appear in every matching organism's file
`TestRunCombinedPercolatorRound` | `_run_combined_percolator_round` returns the sorted list of output PSM files produced by a mocked `cruxutil.percolator` across multiple Tide-search target files; an empty input list returns an empty list; a failed file (mocked `percolator` returning `False`) does not stop processing of the remaining files, and only the successful files' outputs are returned

---

### `tests/unit/test_samples.py`
Unit tests covering `src/comms/utils/samples.py`. Sample sheets are now built via the `sample_sheet_factory` fixture rather than the fixed `valid_sample_sheet` fixture:

Class | Test description
-- | --
`TestLoadSampleSheet` | loads valid TSV; correct row count; column names are lowercased; required columns present (including `fraction`); raises `ValueError` on missing column, duplicate `sample_id`, or nonexistent file; accepts CSV in addition to TSV; allows optional `batch` column; strips whitespace from column names
`TestGetSamplesByTreatment` | filters correctly; case-insensitive; returns empty DataFrame for unknown treatment; returns a copy, not a view
`TestGetSamplesByFraction` | filters correctly; case-insensitive; returns empty DataFrame for unknown fraction; returns a copy, not a view
`TestGetRawFileMap` | maps existing files; omits missing files; returns `Path` objects

---

### `tests/unit/test_settings.py`
Unit tests covering `src/comms/utils/settings.py`. Mod-spec-flag logic (`applyMod`, `applyIodo`, etc.) has moved to `comms/utils/modspec.py` (see [above](#testsunittest_modspecpy)); this file now covers only config location/resolution and the assembled modifications string:

Class | Test description
-- | --
`TestUserConfigPath` | returns a `Path`; path name is `config.toml`; parent directory is named `comms`
`TestLoadDefaultConfig` | returns a dict; idempotent (calling twice gives equal dicts); the underlying bundled file parses as valid TOML
`TestResolveConfig` | falls back to bundled default when neither a local nor a global config exists and the source label mentions the default; prefers a local `comms/config.toml` over the global config and the source begins with "local"; uses the global user config when present and no local config exists, and the source begins with "global"
`TestResolveConfigValue` | an explicit override value is returned when given; falls back to the config value when the override is `None`; raises `KeyError` when the key is absent from both override and config
`TestConfigFallback` | loads bundled defaults when `globalConfigPath()` points to a non-existent file
`TestInitComms` | `initComms()` runs without raising; prints the string `comMS` to stdout
`TestResolvedModsSpec` | returns string; base only when no custom; custom appended to base; custom duplicate of base not repeated; empty base returns custom only; both empty returns `C+0`; no leading/trailing commas

---

### `tests/unit/test_sheet.py`
Unit tests covering `src/comms/utils/sheet.py` — a standalone `SampleRow`/`render_sample_sheet`/`parse_sample_sheet` implementation used outside the GUI (e.g. for round-tripping a sample sheet when loading a saved experiment), distinct from the GUI's own `sample_table.render_sample_sheet` (see [`test_gui_models.py`](#testsunitguitest_gui_modelspy)):

Class | Test description
-- | --
`TestRenderSampleSheet` | header uses the canonical column order (`sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch`); a row renders tab-joined; a `None` replicate renders as an empty field; output ends with a trailing newline; an empty row list still writes the header line only
`TestParseSampleSheet` | round-trips a rendered row back through `parse_sample_sheet`; empty text returns an empty list; a numeric replicate value sets `replicate_overridden=True`; an empty replicate field parses to `None` with `replicate_overridden=False`; whitespace is stripped from fields; a missing `batch` column defaults to `''`

---

### `tests/unit/test_uninstall.py`
Unit tests covering `src/comms/commands/uninstall.py`:

Class | Test description
-- | --
`TestGeneratedTargets` | includes the global config file when it exists; returns an empty list when no config is present
`TestDetectUninstallCommand` | returns the `uv tool uninstall` command when the launching path is under a uv tools directory; returns the `pip uninstall` command when installed via pip; falls back to the unknown message when comMS is not listed in pip output; falls back to the unknown message when pip is unavailable
`TestRunUninstall` | a dry run does not delete the config file; `--force` deletes the global config without prompting; the `logMsg` instance is named `'uninstall'`

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
`TestProbeCrux` / `TestProbeTrfp` | `probe_crux`/`probe_trfp` return the resolved path when a binary is found (via a monkeypatched version getter); return `None` without raising when nothing is found — the non-raising counterparts to `_check_crux`/`_check_trfp` used by the GUI readiness panel

---

### `tests/unit/test_version.py`
Unit tests covering `src/comms/commands/version.py`:

Class | Test description
-- | --
`TestPrintVersion` | exits with code zero; prints the installed version string; handles `PackageNotFoundError` gracefully by printing an 'unknown' fallback message

---

### `tests/unit/gui/test_gui_models.py`
Unit tests covering `src/comms/gui/models/experiment_state.py` and `src/comms/gui/models/sample_table.py`. `SampleRow`/`render_sample_sheet` are imported from `sample_table` here (the GUI-facing copy, backed by `COLUMNS`/`COL_*` constants) — see [`test_sheet.py`](#testsunittest_sheetpy) for the standalone `comms.utils.sheet` counterpart used outside the GUI:

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
Unit tests covering `src/comms/gui/panels/config_panel.py`, `src/comms/gui/panels/experiment_panel.py`, `src/comms/gui/panels/sample_panel.py` and `src/comms/gui/panels/save_panel.py`. (The readiness panel, `src/comms/gui/panels/readiness_panel.py`, has its own dedicated file — see below.)

Class | Test description
-- | --
`TestConfigPanel` | defaults to single species; organism table is disabled for single species and enabled for multispecies; single species is complete without organisms; multispecies is incomplete without organisms; incomplete with a half-filled organism row; complete with a full organism row; `_build_config` returns a dict with a `search` section; default includes Met oxidation; a custom mod is written to `index.custom_mods`; single species writes an empty organism section; multispecies writes the organism patterns; `changed` signal fires and the tracker becomes complete; `summary` reports "single species"; **new:** `load_from_config` accepts `clip_n_met` as either the string `'true'`/`'false'` or a genuine bool and sets the checkbox accordingly; `_build_config` always re-serialises `clip_n_met` as a bool, never a string, regardless of how it was loaded
`TestExperimentPanel` | name strips whitespace; `base_dir` is `None` when empty; `output_dir` appends `comms`; `is_valid` requires **all three** of name, base directory, and database path (tracker remains `INCOMPLETE` until all three are set); the bin-directory field is optional and does not affect `is_valid`; a supplied bin directory is written to `experiment.toml` under `[experiment].bin_dir`; an empty bin directory is omitted from metadata; `write_metadata` coerces list-valued `files` entries to lists of strings, and scalar `Path` values to plain strings
`TestSamplePanel` | `is_complete` proxies the model; `contentChanged` is re-emitted; the tracker moves from incomplete to complete; `write` creates `sample_sheet.tsv`; `data_files()` returns source paths in insertion order; `data_files()` skips rows with an empty `source_path`; **new:** `load(rows, treatments, fractions, data_files=None)` populates the treatment/fraction group lists from a saved experiment; matches each loaded row's `source_path` to a supplied data file by filename when the row doesn't already have one set; never overwrites a row's existing `source_path`; leaves `source_path` empty for a row with no matching data file; works correctly even when `data_files` is omitted entirely (rows are still set)
`TestSavePanel` | save button disabled when incomplete; enabled when all three panels are complete (requires name, dir, **and** database on `ExperimentPanel`); `_save_all` writes the sample sheet, config and metadata together; output paths recorded under `[files]` and the experiment name under `[experiment]` in `experiment.toml`; all three trackers marked saved; the `saved` signal is emitted (`QMessageBox.information` is patched throughout)

---

### `tests/unit/gui/test_gui_readiness.py`
Unit tests covering `src/comms/gui/panels/readiness_panel.py` (`CommandReadinessPanel`) — the GUI counterpart to `test_readiness.py`'s `missing_requirements`, which additionally probes for Crux/TRFP/R availability and re-resolves the bin directory on demand:

Class | Test description
-- | --
`TestReadinessPanel` | `refresh_dependencies()` resolves the bin directory via `repoBinDir(experiment_bin_dir=<experiment's bin_dir>)` and probes `probe_crux`/`probe_trfp` against the resolved path; **regression test:** changing the experiment's `bin_dir` and calling `refresh_dependencies()` again re-probes against the *new* path, not a stale cached one; found/not-found states for Crux and TRFP are reflected on `panel._crux_found`/`panel._trfp_found`; the dependencies label's tooltip names the directory that was searched; missing requirements (e.g. no data files) are reflected per-command in `panel._details['convert']`

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
`TestGroupComboDelegate` | `createEditor` returns a `QComboBox` with a blank first item and the provider's options; options reflect live provider changes; the show-popup callback is scheduled via `QTimer.singleShot`; `setEditorData` selects the cell's current value and falls back to blank when it is not an option; `setModelData` writes the combo text back to the model. A `teardown_method` drains pending Qt events (including the deferred `singleShot` popup callback) while the parent/editor widgets are still referenced on `self`, avoiding a "C++ object already deleted" error during pytest teardown

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>

## Integration tests
Integration tests call external binaries and verify that the command-level orchestration functions behave correctly end-to-end. They use the synthetic fixtures described [above](#synthetic-file-fixtures) to avoid requiring real experimental data. Command-level functions under test now take an `ExperimentContext` (`ctx=experiment_ctx`) rather than a raw output directory, and sample sheets/PSM directories are built via `sample_sheet_factory`/`psm_dir_factory` rather than fixed fixtures.

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
Integration tests covering the Crux toolkit aspects used in the comMS pipeline. All tests in this file require the Crux binary (`pytest.mark.crux`). Module-scoped `built_index`/`search_results` fixtures (see [above](#rescorecrux-integration-fixtures)) share a Tide index and search output across the classes below.

Class | Description
-- | --
`TestFindCrux` | binary exists at returned path; path is executable; returns `None` for an empty `bin/` directory.
`TestTideIndex` | creates and populates the index directory; writes a log file; returns `False` for an invalid FASTA.
`TestTideSearch` | creates the target PSM file; file has at least a header and one data row; log file is written.
`TestPercolator` | *n.b. this class is currently commented out entirely — synthetic data does not provide sufficient PSMs for Percolator to converge; the `synthetic_percolator_results` fixture provides a hand-written PSM file at the expected path so that `TestSpectralCounts` can run without depending on it.*
`TestSpectralCounts` | uses the `synthetic_percolator_results` fixture (which produces `EUK/synthetic.EUK.percolator.target.psms.txt`) to bypass Percolator; creates a spectral-counts output file with content

---

### `tests/integration/test_pipeline.py`
Integration tests and smoke tests that assert the pipeline stages complete without raising errors and create the expected output directories and files. All tests in this file require the Crux binary (`pytest.mark.crux`). Module-scoped `pipeline_index`/`pipeline_search` fixtures (see [above](#rescorecrux-integration-fixtures)) share a built index/search output across the `TestRunSearch*`/`TestRunRescore` classes, skipping their tests if the shared setup step fails.

Class | Description
-- | --
`TestRunIndex` | output directory is created and non-empty; logs a completion message; `logMsg` instance is named `'index'`
`TestRunSearch` | output directory is created; target PSM file exists; logs a completion message; `logMsg` instance is named `'search'`; data files supplied as `data_files=[synthetic_mzml]`
`TestRunSearchParamMedic` | full `--param-medic` path completes without raising; search output directory and target PSM file are created; a `param-medic/` output directory is created; warns and falls back to config defaults when param-medic yields no usable estimates; summary reports numeric tolerance values; output is identical to a non-param-medic run when estimates are unavailable; data files supplied as `data_files=[synthetic_mzml]`
`TestRunSearchParamMedicMocked` | mocks `_runParamMedic` to return known values and verifies those values appear in the log summary; verifies that `(None, None)` from `_runParamMedic` falls back to config defaults without raising; data files supplied as `data_files=[synthetic_mzml]`
`TestRunRescoreDirectories` | verifies that `comms/results/rescore/` is created; verifies that per-organism subdirectories (`EUK/`, `PRO/`) are created when `_splitPsmsByOrganism` runs after the combined Percolator round; `cruxutil.percolator` is mocked with a counter-based side effect that writes combined output files on the first (combined) call and returns `True` on subsequent (per-organism) calls
`TestRunRescorePerOrganismPercolator` | verifies that `cruxutil.percolator` is called three times total for a one-file, two-organism run (1 combined + 2 per-organism) when both the combined Percolator mock and `_splitPsmsByOrganism` write the files each round expects; verifies that `run_rescore` raises `SystemExit` when the combined round produces no output files, which prevents round 2 from running
`TestRunRescoreOrganismTags` | raises `SystemExit` on no PSM files in input directory; raises `SystemExit` on an invalid (odd-count) tag string; raises `SystemExit` when neither `organism_tags` nor config organism is available (monkeypatched to empty dict) if `analysis_mode` is explicitly set to "multi"; uses config organism when `organism_tags` is falsy; verifies Percolator is called exactly once per file
`TestRunRescoreOutput` | success summary is printed; warning is printed when Percolator fails (and `SystemExit` is caught); warning is printed when `_splitPsmsByOrganism` returns `False`; `logMsg` instance is named `'rescore'`
`TestRunRescore` | real (unmocked) integration path with synthetic data, run against `pipeline_search`'s shared search output: verifies the output directory is created (requires `organism_tags='EUK,SP'`; the directory is created after tag resolution); verifies that round-1 progress is logged even though Percolator fails on synthetic data; verifies the log file is written; `logMsg` instance is named `'rescore'`
`TestRunRescoreSingleSpecies` | verifies that only the combined Percolator round runs for single-species analysis (percolator called once per input file, not per organism); verifies no per-organism subdirectories are created under the rescore root; verifies that supplied `organism_tags` are ignored with a warning; no `assignConfidence` mock is used
`TestRunLfqOutputDirectories` | `run_lfq` creates one subdirectory per fraction under `comms/results/lfq/`; a single-fraction run creates exactly one subdirectory; the `comms/results/lfq/` root itself is created; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqCruxCalls` | `cruxutil.lfq` is called exactly once per fraction; each call receives only the PSM files belonging to that fraction; an orphaned PSM file with no sample sheet entry does not produce an extra call; the `fileroot` kwarg equals the fraction label for each call; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqEarlyExit` | raises `SystemExit` when the rescore directory contains no PSM files; verifies that `cruxutil.lfq` is called once per fraction even when the supplied mzML file does not match any PSM stem (`cruxutil.lfq` is mocked to return `False`)
`TestRunLfqWarnings` | a `WARNING`-level message is logged when `cruxutil.lfq` returns `False` for a fraction; processing continues for remaining fractions even when one fails; mzML files supplied as `data_files=[synthetic_mzml]`
`TestRunLfqLogger` | the `logMsg` instance is named `'lfq'`
`TestRunQuantify` | uses `synthetic_percolator_results` fixture; output directory is created; spectral-counts file exists; logs a completion message; `logMsg` instance is named `'quantify'`
`TestQuantifyFlatOutput` | `run_quantify` discovers and processes flat `.percolator.target.psms.txt` output files from single-species analysis
`TestRunPipeline` | full end-to-end smoke test with `--skip-convert`, `--skip-lfq`, `--skip-quantify`/`--skip-report` flag combinations; data supplied as `data=[mzml]`; pipeline completes without raising; all expected stage directories (`index`, `search`, `rescore`, `quantify`) are created under `comms/results/`; `logMsg` instance is named `'pipeline'`

Note: `run_report` itself is not exercised here — its orchestration logic (sections, per-organism status, config sidecars) is covered directly in [`test_report.py`](#testsunittest_reportpy).

---

### `tests/integration/test_trfp.py`
Integration tests covering the comMS wrapper around ThermoRawFileParser. All tests require ThermoRawFileParser (`pytest.mark.trfp`). The test `TestConvertRawRealFile` is gated behind `tests/fixtures/real_sample.RAW` - for more information see [above](#real-raw--fixture). `REAL_RAW_FIXTURE` is defined here and imported by `test_convert.py`.

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

### `tests/r/helper.R`
Shared setup, loaded automatically by `testthat` before the test files below. Defines `.find_repo_root()`, which walks up from the working directory until it finds `pyproject.toml`, and exposes the result as `REPO_ROOT`. This lets the R test files `source()` the scripts under `src/comms/r/utils/` by an absolute, repo-relative path regardless of which directory `testthat::test_dir()` is invoked from.

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