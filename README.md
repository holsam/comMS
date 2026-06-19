<div align="right">

![Version][version-shield]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

**comMS documentation:** [Commands][docs-commands] · [Configuration][docs-config] · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · _README_

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
- [How comMS works](#how-comms-works)
- [Documentation](#documentation)
- [Getting help & contributing](#getting-help--contributing)
- [License](#license)

## Overview
comMS is a command-line tool for automated proteomic analysis and quantification, wrapping the [Crux toolkit](https://crux.ms) and [ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) into a single reproducible pipeline. comMS was designed to enable rapid and accurate proteomic analysis and quantification, particularly from multi-species experiments where samples may originate from more than one organism. 

comMS was originally written to allow comparative analysis of samples derived from experiments investigating arbuscular mycorrhizal symbiosis (a plant-fungal mutualism) in *Medicago truncatula*, but the pipeline is applicable to any shotgun proteomics experiment that uses tryptic digestion.

## Requirements
### Python
comMS requires Python 3.14 or later. The recommended way to manage comMS and its Python dependencies is using the package manager [`uv`](https://docs.astral.sh/uv/). If `uv` is not already installed, follow the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/). 

### External tools
comMS wraps two external binaries that must be available within a `bin/` directory. Both tools must be downloaded manually and placed there, as described in [Installing external tools](#installing-external-tools).

Tool | Minimum version | Purpose | Platform notes
---|---|---|---
[Crux toolkit][crux-url] | 4.0.0 (5.0.0 for `lfq`) | Peptide index, spectrum search, PSM rescoring, quantification | Uses platform-specific binaries
[ThermoRawFileParser][trfp-url] | 1.4.5 | `.RAW` → `.mzML` conversion | Versions < 2.0.0 require [Mono](https://mono-project.com) on Linux/macOS

### `comms report` dependencies
The `report` command requires R (≥ 4.3.0) and a set of R packages (listed in the [report command documentation](./docs/commands.md#the-report-command)). Required R packages can be installed by running:
```bash
Rscript src/comms/r/install_deps.R
```

## Installation
The recommended installation method is `uv tool install`, which installs comMS as an isolated command available on your `PATH`:

```bash
uv tool install git+https://github.com/holsam/comMS
```

Once installed, verify the installation:

```bash
comms version
```

### Installing external tools
Download [Crux][crux-url] and [ThermoRawFileParser][trfp-url] and place them in a single `bin/` directory (this directory can be anywhere, it does not have to be with your data or the comMS installation). The expected layout is:
```
bin/
  crux-v.v.platform.arch/
    bin/
      crux
  ThermoRawFileParser-v.v.v/  # versions ≥2.0.0 ship a platform subdirectory which is supported
    ThermoRawFileParser.exe
```

comMS locates binaries by patterns, so version subdirectories are supported and exact names are flexible. If multiple versions of either tool are installed under `bin/`, comMS will automatically select the recent version.

Once downloaded, point comMS at the `bin/` directory by either:
- Setting it for an experiment via `bin_dir` in `experiment.toml` (see [Configuration](./docs/configuration.md#bin-directory-resolution)).
- Exporting an environment variable: `export COMMS_BIN_DIR=/absolute/path/to/bin`

#### External tool version considerations
On Linux and macOS, [ThermoRawFileParser][trfp-url] versions <2.0.0 require [Mono](https://mono-project.com). Install it via your system package manager (e.g. `brew install mono` on macOS or `apt install mono-complete` on Debian/Ubuntu). ThermoRawFileParser versions ≥2.0.0 and later are native binaries and do not require Mono.

The `lfq` command requires Crux >= 5.0.0, which introduced the `crux lfq` subcommand wrapping FlashLFQ. All other comMS commands are compatible with Crux >= 4.0.0. comMS will raise an error at startup if the installed Crux version does not meet the requirement for the command being run.

## Quick start
### Using an experiment
```bash
# 1. Create a comMS experiment
comms experiment                    # via GUI
comms experiment --headless         # via terminal

# 2. Run comMS analysis pipeline
comms pipeline -e /path/to/experiment/dir
```
Use `--skip-convert` if `.mzML` files are already available, and `--skip-report` to omit the report step.

You need two inputs to run the pipeline: a sample sheet (TSV or CSV) and a combined FASTA database containing your proteome(s) and contaminants. Both are described in [Input files](./docs/commands.md#input-files). The `--experiment-dir` option sets where comMS reads its configuration and writes its results, explained in [Configuration][docs-config].

### Using command line options
Alternatively, each file that a comMS experiment resolves can be passed directly:
```bash
comms pipeline \
    --sample-sheet sample_sheet.tsv \
    --fasta combined_proteome.fasta \
    --data /path/to/sample1.RAW \
    --data /path/to/sample2.RAW \
    --experiment-dir /path/to/experiment/directory/ \
    --organism-tags "<Org1>,<Pattern1>,<Org2>,<Pattern2>"
```

The `-d`/`--data` flag is repeatable and, as above, `--skip-convert` should be used if `.mzML` files are already available and `--skip-report` can be used to omit the report step.

## How comMS works
Running `comms pipeline` carries out the following stages:

1. `.RAW` to `.mzML` conversion (ThermoRawFileParser)
2. Peptide index construction (Crux `tide-index`)
3. Peptide-spectrum matching (Crux `tide-search`)
4. PSM rescoring (Crux `percolator` with picked-protein FDR)
5. Quantification by MS1 label-free quantification (`lfq`) and dNSAF spectral counting (`quantify`)

An optional report stage then generates figures and spreadsheets from the quantification output.

### single- and multi-species analysis modes
comMS supports two analysis modes for single- and multi-species experiments, which are selected via the analysis field in `experiment.toml`:

Mode | `[analysis]` value | Pipeline runs | Suitable for
-- | -- | --
Single-species | `single` | Percolator and `assign-confidence` on the combined protein database, resulting in one set of PSMs per sample | Analysing proteins from one organism or where cross-organism FDR control is not a priority
Multi-species | `multi` | Percolator is called on the combined protein database, with results split by organism before `assign-confidence` runs on individual organisms to apply per-organism picked-protein FDR | Analysing proteins from two (or more) organisms where target/decoy ratios differ substantially

Analysis mode is resolved when `rescore` runs: if `analysis` is not set, the pipeline infers `multi` if organism tags are supplied or configured, otherwise defaults to `single`. N.B. contaminants should not be counted as an organism.

## Documentation
Page | Contents
---|---
[Configuration][docs-config] | Experiment context, experiment directories, global vs local configuration and resolution order, the `config` and `experiment` commands
[Configuration reference][docs-config-ref] | Protocol flags and the default index, search and Percolator parameters
[Commands][docs-commands] | Input file formats, the full command list, and the `report` command in detail
[Output structure][docs-output] | The results directory layout and logging behaviour

Developer guidance is in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Getting help & contributing
If you come across any bugs/issues while using comMS, or if you have a feature request, please open an [issue via GitHub][issues-url].

Any contributions to this project are also very welcome! Specific guidance for developers is provided in `CONTRIBUTING.md`, please read this beforehand.

## License
This repository is distributed under the GPL-3.0 license. See [LICENSE][license-url] for more information.

<div align="right">

**comMS documentation:** [Commands][docs-commands] · [Configuration][docs-config] · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · _README_

</div>


<!-- MARKDOWN LINKS & IMAGES -->
[docs-commands]: ./docs/commands.md#commands
[docs-config-ref]: ./docs/config-reference.md#configuration-reference
[docs-config]: ./docs/configuration.md#configuration
[docs-output]: ./docs/output-structure.md#output-structure
[version-shield]: https://img.shields.io/badge/dynamic/toml?url=https://raw.githubusercontent.com/holsam/comMS/refs/heads/main/pyproject.toml&query=$.project.version&style=for-the-badge&label=Current%20version&color=important
[issues-shield]: https://img.shields.io/github/issues/holsam/comMS.svg?style=for-the-badge&color=critical
[issues-url]: https://github.com/holsam/comMS/issues
[license-shield]: https://img.shields.io/badge/GPL--3.0-informational?style=for-the-badge&label=License
[license-url]: https://github.com/holsam/comMS/blob/main/LICENSE
[crux-url]: https://crux.ms
[trfp-url]: https://github.com/compomics/ThermoRawFileParser