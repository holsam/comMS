<div align="right">

![Version][version-shield]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

</div>

# comMS
<ins>com</ins>parative <ins>M</ins>ass <ins>S</ins>pectrometry analysis pipeline

## Contents
- [Overview](#overview)
- [Requirements](#requirements)
    - [Python](#python)
    - [External tools](#external-tools)
    - [comms report dependencies](#comms-report-dependencies)
- [Installation](#installation)
    - [Installing external tools](#installing-external-tools)
- [Quick start](#quick-start)
- [Input files](#input-files)
- [Commands](#commands)
    - [Pipeline](#pipeline)
    - [Individual commands](#individual-commands)
    - [Utilities](#utilities)
- [Configuration](#configuration)
    - [Viewing and verifying user configuration](#viewing-and-verifying-user-configuration)
    - [Protocol flags](#protocol-flags)
    - [Default search parameters](#default-search-parameters)
    - [Percolator settings](#percolator-settings)
    - [Report settings](#report-settings)
- [Output structure](#output-structure)
- [Limitations](#limitations)
- [Getting help & contributing](#getting-help--contributing)
- [License](#license)

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Overview
comMS is a command-line tool for automated proteomic analysis and quantification, wrapping the [Crux toolkit](https://crux.ms) and [ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) into a single reproducible pipeline. comMS was designed to enable rapid and accurate proteomic analysis and quantification, particularly from multi-species experiments where samples may originate from different species. 

comMS was originally written to allow comparative analysis of samples derived from experiments investigating arbuscular mycorrhizal symbiosis (a plant-fungal mutualism) in *Medicago truncatula*, but should be applicable to any shotgun proteomics experiment that uses tryptic digestion.

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Requirements
### Python
comMS requires Python 3.14 or later. The recommended way to manage comMS and its Python dependencies is using the package manager [`uv`](https://docs.astral.sh/uv/). If `uv` is not already installed, follow the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/). 

### External tools
comMS wraps two external binaries that must be available under the `bin/` directory at the repository root. Both tools must currently be downloaded and placed under `bin/` manually. See [Installing external tools](#installing-external-tools) below.

Tool | Minimum version | Purpose | Platform notes
---|---|---|---
[Crux toolkit][crux-url] | 4.0.0 (5.0.0 for `lfq`) | Peptide index, spectrum search, PSM rescoring, quantification | Uses platform-specific binaries
[ThermoRawFileParser][trfp-url] | 1.4.5 | `.RAW` → `.mzML` conversion | Versions < 2.0.0 require [Mono](https://mono-project.com) on Linux/macOS

### `comms report` dependencies
The `report` command requires R (≥ 4.3.0) and a set of R packages. Required R packages can be installed by running:
```bash
Rscript src/comms/r/install_deps.R
```
If R is not available, `report` will exit with an informative error.

The packages installed are:
Package | Source
-- | --
`tidyverse` | CRAN
`openxlsx2` | CRAN
`svglite` | CRAN
`limma` | Bioconductor
`ggrepel` | CRAN
`ggfortify` | CRAN
`cluster` | CRAN
`UpSetR` | CRAN
`pheatmap` | CRAN
`VennDiagram` | CRAN

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Installation
The recommended installation method is `uv tool install`, which installs comMS as an isolated command available on your `PATH`:

```bash
uv tool install git+https://github.com/holsam/comMS
```

To install from a local checkout:

```bash
git clone https://github.com/holsam/comMS
cd comMS
uv tool install .
```

Once installed, verify the installation:

```bash
comms version
```

### Installing external tools
Download [Crux][crux-url] and [ThermoRawFileParser][trfp-url] and place them under the `bin/` directory at the project root. The expected layout is:
```
bin/
  crux-v.v.platform.arch/
    bin/
      crux
  ThermoRawFileParser-v.v.v/  # for versions ≥2.0.0, the subdirectory will have the platform for the given binary - comMS is compatible with this
    ThermoRawFileParser.exe
```

comMS locates binaries using regular expressions, so version subdirectories are expected but exact names are flexible. If multiple versions of either tool are installed under `bin/`, comMS will automatically select the most up-to-date installation.

On Linux and macOS, [ThermoRawFileParser][trfp-url] versions <2.0.0 require [Mono](https://mono-project.com). Install it via your system package manager (e.g. `brew install mono` on macOS or `apt install mono-complete` on Debian/Ubuntu). ThermoRawFileParser versions ≥2.0.0 and later are native binaries and do not require Mono.

The `lfq` command requires Crux >= 5.0.0, which introduced the `crux lfq` subcommand wrapping FlashLFQ. All other comMS commands are compatible with Crux >= 4.0.0. comMS will raise an error at startup if the installed Crux version does not meet the requirement for the command being run.

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Quick start
```bash
comms pipeline sample_sheet.tsv \
    --database combined_proteome.fasta \
    --input /path/to/raw_files/ \
    --out-dir /path/to/results/ \
    --organism-tags "<Org1>,<Pattern1>,<Org2>,<Pattern2>"
```
This runs all pipeline stages in sequence: 
1. `.RAW` to `.mzML` conversion
2. Peptide index construction
3. Peptide-spectrum matching (via Tide-search)
4. Per-organism PSM rescoring (via Percolator picked-protein)
5. Quantification (via dNSAF spectral counting). 

Use `--skip-convert` if `.mzML` files are already available, and `--skip-report` to omit the report step (which is not yet implemented).

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Input files
### Mass spectrometry data files
comMS expects mass spectrometry data in Thermo `.RAW` format as input to the `convert` command. If `.mzML` files are already available, the conversion step can be skipped with `--skip-convert` when running the full pipeline. Other mass spectrometry data file formats should be converted to `.mzML` externally before continuing as described above.

### Sample information
comMS also requires a sample sheet in either `.TSV` or `.CSV` format with the following columns:

Column | Required | Description
---|---|---
`sample_id` | Required | Unique identifier for each sample
`raw_file` | Required | Filename of the `.RAW` (or `.mzML`) source file
`treatment` | Required | Experimental group label
`fraction` | Required | Sample fraction/type label used for LFQ grouping
`replicate` | Required | Replicate number within treatment/fraction
`batch` | Optional | Batch label

Example:

```
sample_id	raw_file	treatment	fraction replicate	batch
S1  sample_mock_1.RAW	MOCK	WCL 1   A
S2	sample_treat_1.RAW	TREAT	WCL 1   A
```

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Commands
comMS provides the following commands. Run `comms --help` or `comms <command> --help` for full option descriptions.
### Pipeline
Command | Description
-- | --
`pipeline`| Run the full analysis pipeline end-to-end from a sample sheet

### Individual commands
Command | Description
-- | --
`convert` | Convert `.RAW` files to indexed `.mzML` files using ThermoRawFileParser
`index` | Build a tryptic peptide index from a FASTA file using Crux `tide-index`
`search` | Match spectra to peptides using Crux `tide-search`
`rescore` | Rescore PSMs using Crux `percolator` with picked-protein FDR
`lfq` | Run MS1 label-free quantification using grouped fractions
`quantify` | Compute dNSAF spectral counts using Crux `spectral-counts`
`report` | Generate a static analysis report (SVG figures + Excel workbooks) from `comms quantify` and optionally `comms lfq` output

### Utilities
Command | Description
-- | --
`config` | Manage a user configuration file
`license` | Print the comMS license
`version` | Print the installed comMS version

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Configuration
comMS reads settings from a TOML configuration file, and provides the `config` command and its subcommands to interact with this file. 

A default configuration file is bundled with comMS, but any modifications should be made to a user config file. Initialise a user config file at the OS-appropriate location by using:

```bash
comms config init
```

Config file locations:

| OS | Path |
|---|---|
| Linux/macOS | `~/.config/comms/config.toml` |
| Windows | `%APPDATA%\comms\config.toml` |

If no user config file exists, comMS falls back to its bundled defaults.

### Viewing and verifying user configuration
```bash
comms config list      # print current values vs defaults
comms config verify    # check all expected keys are present
comms config reset     # overwrite with defaults (prompts for confirmation)
```
### Protocol flags
The `config set` command applies experiment-specific presets. Multiple flags can be combined in a single call.

#### Cysteine alkylation
```bash
comms config set --iodo        # add static carbamidomethylation (C+57.0215 Da)
comms config set --no-iodo     # remove carbamidomethylation
```
Add `--iodo` only if iodoacetamide alkylation was performed during sample preparation.

#### Methionine oxidation
```bash
comms config set --ox          # add variable methionine oxidation (M+15.9949 Da)
comms config set --no-ox       # remove methionine oxidation
```

#### Serine/threonine/tyrosine phosphorylation
```bash
comms config set --phos        # add variable STY phosphorylation (STY+79.966331 Da)
comms config set --no-phos     # remove STY phosphorylation
```

#### N-terminal glutamine cyclisation
```bash
comms config set --n-cyc       # add N-terminal Gln → pyro-Glu cyclisation (Q-17.027 Da)
comms config set --no-n-cyc    # remove N-terminal Gln cyclisation
```

#### Protein N-terminal acetylation
```bash
comms config set --n-ace       # add protein N-terminal acetylation (X+42.011 Da)
comms config set --no-n-ace    # remove protein N-terminal acetylation
```

#### Custom modifications
```bash
comms config set --custom "1K+28.0313"     # add a custom Tide mods_spec entry
comms config set --custom "1K+28.0313" --custom "1R+14.0157"  # add multiple entries
comms config set --custom ""               # remove all custom modifications
```
Custom modifications are stored separately and merged with the named-flag modifications at search time. The `config list` command shows both the individual values. Passing a modification that is already managed by a named flag (e.g. `1M+15.9949` for `--ox`) will produce a warning and the entry will not be added, please use the appropriate named flag instead.

#### Instrument resolution
```bash
comms config set --high-res    # mz_bin_width=0.02, score_function=xcorr (default)
comms config set --low-res     # mz_bin_width=1.0005079, score_function=combined-p-value
```

Use `--low-res` for ion-trap MS2 data (e.g. older LTQ instruments). Use `--high-res` for Orbitrap data (default for modern instruments).

#### Organism protein patterns
```bash
comms config set --organism Org1=Pattern1 Org2=Pattern2 # defines two organisms whose proteins will use the supplied patterns
```
Sets the label-to-pattern pairs used to split the combined FASTA by organism during the rescore step, enabling per-organism picked-protein FDR. Each `--organism` argument takes the format Label=Pattern, where `Pattern` is matched as a regular expression against FASTA headers. Once set, these patterns are used automatically by `pipeline` and `rescore` unless overridden with `--organism-tags` at the command line.

### Default index parameters
Peptide indices are generated using the following parameters:

Parameter | Default | Description | Crux equivalent | Config flag
--|--|--|--|--
Protease | trypsin | Use tryptic digestion rules | `--enzyme` | —
Digestion | full | Completely digest proteins | `--digestion` | —
Missed cleavages | 2 | Maximum missed cleavage sites | `--missed-cleavages` | —
Leading peptide clipping | True | Duplicate leading peptides with one lacking N-terminal methionine | `--clip-nterm-methionine` | —
Duplicate decoys | True | Allow duplicated decoy proteins | `--allow-dups` | —
Number decoys | 1 | Number of decoy peptides per target | `--num-decoys-per-target` | —
Decoy strategy | reverse | Generate decoy peptides by reversing residues | `--decoy-format` | —
M oxidation | True | Variable methionine oxidation (`1M+15.9949`) | `--mods-spec` | `--ox` / `--no-ox`
STY phosphorylation | False | Variable STY phosphorylation (`1STY+79.966331`) | `--mods-spec` | `--phos` / `--no-phos`
Cys carbamidomethylation | False | Static cysteine carbamidomethylation (`C+57.0215`) | `--fixed-modifications` | `--iodo` / `--no-iodo`
Peptide N-cyclicisation | True | Cyclisation of Gln to pyro-Glu at peptide N-termini (`1Q-17.027`) | `--nterm-peptide-mods-spec` | `--n-cyc` / `--no-n-cyc`
Protein N-acetylation | True | Acetylation of protein N-terminal residue (`1X+42.011`) | `--nterm-protein-mod-spec` | `--n-ace` / `--no-n-ace`

It is recommended that any proteomes processed using the `index` command include a contaminant protein sequences, such as those in the [cRAP contaminant protein dataset](https://www.thegpm.org/crap/).

### Default search parameters
The default configuration applies the following search parameters, informed by *[Svozil & Baerenfaller, 2017](https://doi.org/10.1016/bs.mie.2016.11.007)*:

Parameter | Default | Description
---|---|---
Protease | trypsin | Full tryptic digestion
Missed cleavages | 2 | Maximum missed cleavage sites
Precursor tolerance | 10 ppm | Precursor mass window

### Percolator settings
By default, PSM rescoring uses picked-protein FDR *[Savitski et al., 2015](https://doi.org/10.1021/acs.jproteome.5b00135)* at a 1% PSM-level FDR threshold, requiring at least two unique peptides per protein for confident identification.

Picked-protein FDR is applied separately per organism when a combined multi-species FASTA is used. Organism patterns are configured via `comms config set --organism` or supplied at runtime with `--organism-tags` to the `rescore` and `pipeline` commands. The format for `--organism-tags` is a comma-separated list of alternating label and pattern pairs:
```bash
comms rescore search_dir/ --database combined_proteome.fasta --organism-tags "Org1,Pattern1,Org2,Pattern2"
```
This instructs comMS to split the combined FASTA into one sub-FASTA per organism (with contaminants appended to each), run Percolator separately against each, and merge the rescored PSMs into a single output file per sample.

### Report settings
The `report` command performs several analyses:

Section | Content
---|---
`qc` | Per-sample NSAF density plots, total spectral count bar charts, missing-value upset plot, presence/absence heatmap
`pca` | PCA with k-means clustering overlay, Euclidean distance dendrogram
`da` | limma-based differential abundance ±treatment within each fraction; volcano plots, DA Venn diagrams
`secondary-species` | Secondary organism proteins per fraction; Venn diagram, candidate table
`concordance` | LFQ vs dNSAF log₂FC concordance scatter and Venn diagrams (skipped automatically if no `--lfq-dir` provided)

#### Pre-processing
Normalisation is deliberately NOT applied across fractions, due to the genuine differences in protein composition anticipated.
#### Differential abundance
For differential abundance, limma with empirical Bayes shrinkage is used to support statistical analysis of samples where *n* = 3 (c.f. Ritchie et al. 2015, doi:10.1093/nar/gkv007). Benjamini-Hochberg false-discovery rate is applied within each fraction independently, as across fraction comparisons are likely to be confounded by run-order influences.
#### Auxiliary scripts
An auxiliary script for analysis of EV marker proteins is provided under `r/aux/...`, the contents of which are informed by MISEV 2023 guidelines (c.f. Welsh et al. 2024, doi:10.1002/jev2.12404).

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Output structure
comMS accepts an output directory option (defaults to the current working directory), and writes all outputs following the below directory structure:
```
<out_dir>/
  comms/
    results/
      convert/               # indexed .mzML files
      index/                 # Crux tide-index output
      search/                # Crux tide-search target PSM files
      rescore/               # Merged Percolator rescored PSM files
        organism_n/          # Percolator rescored PSM files for specific organism
      lfq/                   # MS1 label-free quantification output
        fraction_n/          # FlashLFQ output for each sample fraction
      quantify/              # dNSAF spectral-counts output
      report/                # report output files
        index.md             # index of all produced files
        qc/                  # quality check plots and spreadsheet
        pca/                 # principal component analysis and dendrogram plots
        da/                  # differential abundance plots and spreadsheet
        secondary-species/   # secondary species plots and spreadsheet
        concordance/         # concordance of MS1 LFQ and dNSAF quantification (only if --lfq-dir provided)
```

If an output directory for a given command already exists, comMS will not overwrite existing directories and instead add an incremental suffix (e.g. `search-1/`, `search-2/`).

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Limitations
comMS is still being developed and has several known limitations, which are detailed below:

### Path resolution
comMS commands resolve the `bin/` directory relative to the package installation path. This works but is a crude way of resolving the path, and may break in differnt installtion environments. A more robust method of resolving the path to this directory will be implemented in future updates.

### Input file requirements
comMS requires both a sample sheet (in `.tsv` or `.csv` format) and a FASTA file (containing proteomes and contaminants). Additional functionality will be added to validate any such files before beginning processing, and to assist in generating them.

### `param-medic` output parsing

The `--param-medic` flag estimates mass tolerances from data before searching, and the `search` command using regular expressions to parse this where available. While comMS will fall back to default values if parsing fails, this requires further validation.

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Getting help & contributing
If you come across any bugs/issues while using comMS, or if you have a feature request, please open an [issue via GitHub][issues-url].

Any contributions to this project are also very welcome! Specific guidance for developers is provided in `CONTRIBUTING.md`, please read this beforehand.

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## License
This repository is distributed under the GPL-3.0 license. See [LICENSE][license-url] for more information.

<br>

---
<p align="right"><a href="#comms">^ Back to top</a></p>

<!-- MARKDOWN LINKS & IMAGES -->
[version-shield]: https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/holsam/comMS/refs/heads/main/pyproject.toml&query=$.project.version&style=for-the-badge&label=Current%20version&color=important
[issues-shield]: https://img.shields.io/github/issues/holsam/comMS.svg?style=for-the-badge&color=critical
[issues-url]: https://github.com/holsam/comMS/issues
[license-shield]: https://img.shields.io/github/license/holsam/comMS.svg?style=for-the-badge&color=informational
[license-url]: https://github.com/holsam/comMS/blob/main/LICENSE
[crux-url]: https://crux.ms
[trfp-url]: https://github.com/compomics/ThermoRawFileParser