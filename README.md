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
    - [Sample sheet format](#sample-sheet-format)
    - [Running the pipeline](#running-the-pipeline)
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
### Sample sheet format

### Running the pipeline


---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Commands

### Pipeline

### Individual commands

### Utilities

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Configuration

### Viewing and verifying user configuration

### Protocol flags

### Default search parameters

### Percolator settings

---
<p align="right"><a href="#comms">^ Back to top</a></p>

## Output structure


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