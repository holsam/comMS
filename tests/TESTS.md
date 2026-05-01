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

---
<p align="right"><a href="#comms-test-suite">^ Back to top</a></p>