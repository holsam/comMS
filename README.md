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
    - [Input files](#input-files)
- [Installation](#installation)
    - [Installing external tools](#installing-external-tools)
- [Quick start](#quick-start)
- [Commands](#commands)
    - [Pipeline](#pipeline)
    - [Individual commands](#individual-commands)
    - [Utilities](#utilities)
- [Configuration](#configuration)
    - [Viewing and verifying user configuration](#viewing-and-verifying-user-configuration)
    - [Protocol flags](#protocol-flags)
    - [Default search parameters](#default-search-parameters)
    - [Percolator settings](#percolator-settings)
- [Output structure](#output-structure)
- [Limitations](#limitations)
- [Contributing](#contributing)
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

Tool | Purpose | Platform notes
---|---|---
[Crux toolkit][crux-url] | Peptide index, spectrum search, PSM rescoring, quantification | Uses platform-specific binaries
[ThermoRawFileParser][trfp-url] | `.RAW` → `.mzML` conversion | Requires [Mono](https://mono-project.com) on Linux/macOS

### Input files
#### Mass spectrometry data files
comMS expects mass spectrometry data in Thermo `.RAW` format as input to the `convert` command. If `.mzML` files are already available, the conversion step can be skipped with `--skip-convert` when running the full pipeline. Other mass spectrometry data file formats should be converted to `.mzML` externally before continuing as described above.

#### Sample information
comMS also requires a sample sheet in either `.TSV` or `.CSV` format with the following columns:

Column | Description
---|---
`sample_id` | Unique identifier for each sample
`raw_file` | Filename of the `.RAW` (or `.mzML`) source file
`treatment` | Experimental group label
`replicate` | Replicate number within treatment
`batch` | Batch label (optional)

Example:

```
sample_id	raw_file	treatment	replicate	batch
S1	sample_mock_1.RAW	MOCK	1	A
S2	sample_treat_1.RAW	TREAT	1	A
```

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
  crux-4.3.Linux.x86_64/
    bin/
      crux
  ThermoRawFileParser-1.4.5/
    ThermoRawFileParser.exe
```

comMS locates binaries using regular expressions, so version subdirectories are expected but exact names are flexible.

On Linux and macOS, [ThermoRawFileParser][trfp-url] versions below 2.0.0 require [Mono](https://mono-project.com). Install it via your system package manager (e.g. `brew install mono` on macOS or `apt install mono-complete` on Debian/Ubuntu).

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Quick start
```bash
comms pipeline sample_sheet.tsv \
    --database combined_proteome.fasta \
    --input /path/to/raw_files/ \
    --out-dir /path/to/results/
```
This runs all pipeline stages in sequence: 
1. `.RAW` to `.mzML` conversion
2. Peptide index construction
3. Peptide-spectrum matching (via Tide-search)
4. PSM rescoring (via Percolator)
5. Quantification (via dNSAF spectral counting). 

Use `--skip-convert` if `.mzML` files are already available, and `--skip-report` to omit the report step (which is not yet implemented).

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
`quantify` | Compute dNSAF spectral counts using Crux `spectral-counts`
`report` | Generate an HTML report containing visualisations *(not yet implemented)*

### Utilities
Command | Description
-- | --
`config` | Manage a user configuration file
`license` | Print the comMS license
`setup` | Verify setup is correct *(not yet implemented)*
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
#### Instrument resolution
```bash
comms config set --high-res    # mz_bin_width=0.02, score_function=xcorr (default)
comms config set --low-res     # mz_bin_width=1.0005079, score_function=combined-p-value
```

Use `--low-res` for ion-trap MS2 data (e.g. older LTQ instruments). Use `--high-res` for Orbitrap data (default for modern instruments).

#### Cysteine alkylation

```bash
comms config set --iodo        # add static carbamidomethylation (C+57.0215 Da)
comms config set --no-iodo     # remove carbamidomethylation
```

Add `--iodo` only if iodoacetamide alkylation was performed during sample preparation.

### Default search parameters
The default configuration applies the following search parameters, informed by *[Svozil & Baerenfaller, 2017](https://doi.org/10.1016/bs.mie.2016.11.007)*:

Parameter | Default | Description
---|---|---
Protease | trypsin | Full tryptic digestion
Missed cleavages | 2 | Maximum missed cleavage sites
Precursor tolerance | 10 ppm | Precursor mass window
Methionine oxidation | `1M+15.9949` | Variable modification
Glutamine cyclisation | `1Q-17.027` | (N-terminal) Pyro-glutamic acid formation |
Protein N-terminal acetylation | `1X+42.011` | Variable modification
Cysteine carbamidomethylation | not set by default | Add with `--iodo` if applicable


It is recommended that any proteomes processed using the `index` command include a contaminant protein sequences, such as those in the [cRAP contaminant protein dataset](https://www.thegpm.org/crap/).

### Percolator settings
By default, PSM rescoring uses picked-protein FDR *[Savitski et al., 2015](https://doi.org/10.1021/acs.jproteome.5b00135)* at a 1% PSM-level FDR threshold, requiring at least two unique peptides per protein for confident identification.

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Output structure
comMS accepts an output directory option (defaults to the current working directory), and writes all outputs following the below directory structure:
```
<out_dir>/
  comms/
    results/
      convert/      # indexed .mzML files
      index/        # Crux tide-index output
      search/       # Crux tide-search target PSM files
      rescore/      # Percolator rescored PSM files
      quantify/     # dNSAF spectral-counts output
```

If an output directory for a given command already exists, comMS will not overwrite existing directories and instead add an incremental suffix (e.g. `search-1/`, `search-2/`).

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Contributing

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Limitations


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