<div align="right">

**comMS documentation:** _Commands_ · [Configuration][docs-config] · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · [README][docs-readme]

</div>

# Commands

comMS provides the commands listed below. Run `comms --help` or `comms <command> --help` for full option descriptions.

## Contents
- [Input files](#input-files)
- [Command list](#command-list)
- [Per-organism FDR](#per-organism-fdr)
- [The report command](#the-report-command)

## Input files

### Mass spectrometry data files
comMS expects Thermo `.RAW` files as input to the `convert` command. If `.mzML` files are already available, the conversion step can be skipped with `--skip-convert` when running the full pipeline. Data in other formats should be converted to `.mzML` externally first.

### Sample sheet
comMS requires a sample sheet in `.tsv` or `.csv` format. Files with a `.tsv` or `.txt` extension are read as tab-separated; anything else is read as comma-separated. The following columns are expected:

Column | Required | Description
---|---|---
`sample_id` | Required | Unique identifier for each sample
`raw_file` | Required | Filename of the `.RAW` (or `.mzML`) source file
`treatment` | Required | Experimental group label
`fraction` | Required | Sample fraction or type label, used for LFQ grouping
`replicate` | Required | Replicate number within a treatment and fraction
`batch` | Optional | Batch label, used for batch correction

Sample identifiers must be unique. comMS warns if only one fraction is present, since fraction-aware grouping then has no effect. A short tab-separated example:

```tsv
sample_id	raw_file	treatment	fraction	replicate	batch
S1	sample_mock_1.RAW	MOCK	WCL	1	A
S2	sample_treat_1.RAW	TREAT	WCL	1	A
```

The [`experiment` command](./configuration.md#creating-an-experiment-the-experiment-command) can create this to avoid manually writing it.

## Command list

### comMS Configuration
Command | Description
---|---
`experiment` | Build a sample sheet, configuration, and metadata (see [Configuration](./configuration.md#creating-an-experiment-the-experiment-command))
`config` | Manage a configuration file (see [Configuration][docs-config])

### Pipeline
Command | Description
---|---
`pipeline` | Run the full analysis pipeline end-to-end from a sample sheet

### Analysis commands
Command | Description
---|---
`convert` | Convert `.RAW` files to indexed `.mzML` using ThermoRawFileParser
`index` | Build a tryptic peptide index from a FASTA file using Crux `tide-index`
`search` | Match spectra to peptides using Crux `tide-search`
`rescore` | Rescore PSMs using Crux `percolator` on the combined database, then split by organism and run `percolator` per organism for calibrated per-organism FDR
`lfq` | Run MS1 label-free quantification using grouped fractions
`quantify` | Compute dNSAF spectral counts using Crux `spectral-counts`
`report` | Generate a static analysis report from `quantify` and, optionally, `lfq` output

### Utilities
Command | Description
---|---
`license` | Print the comMS license
`uninstall` | Remove comMS-generated files and print the uninstall command where possible
`version` | Print the installed comMS version

## Per-organism FDR
When a combined multi-species FASTA is searched, comMS can apply picked-protein FDR separately per organism. The patterns that split the database can be set once in configuration (`comms config set --organism`, see the [configuration reference](./config-reference.md#protocol-flags)), or supplied at runtime to `rescore` and `pipeline` with `--organism-tags` which takes a comma-separated list of alternating label and pattern pairs:
```bash
comms rescore search_dir/ \
    --database combined_proteome.fasta \
    --organism-tags "Org1,Pattern1,Org2,Pattern2"
```

comMS then splits the combined FASTA into one sub-FASTA per organism (appending contaminants to each), runs Percolator against each separately, and merges the rescored PSMs into a single output file per sample. This feature is optional, however, and single-species analyses are supported.


## The report command
The `report` command runs a set of R-based analysis sections over the quantification output, writing figures and spreadsheets. It requires R (≥ 4.3.0) and the packages listed below.

### Enabling the report command
The report command can be run manually via `comms report` or as part of a `comms pipeline` run. Creating an experiment via `comms experiment` allows selection of reference protein annotation and contaminant files, which are recorded in experiment.toml under [report] and picked up automatically by the `report` command. They can also be supplied at runtime via the `-r`/`--ref-info` and `-c`/`--cont-csv` option flags.

### Sections
By default the `qc`, `pca`, and `da` sections run. Use `--section` (repeatable) to choose specific sections, or `--all` to run every section.

Section | Content
---|---
`qc` | Per-sample NSAF density plots, total spectral count bar charts, a missing-value upset plot, and a presence/absence heatmap
`pca` | PCA with a k-means clustering overlay and a Euclidean-distance dendrogram
`da` | limma-based differential abundance per fraction, with volcano plots and DA Venn diagrams
`secondary-species` | Secondary-organism proteins per fraction, with a Venn diagram and candidate table
`concordance` | LFQ vs dNSAF log₂FC concordance scatter and Venn diagrams (skipped automatically if no `--lfq-dir` is provided)

### Analysis notes
**Normalisation.** Normalisation is deliberately not applied across fractions, because the fractions are expected to differ genuinely in protein composition.

**Differential abundance.** limma with empirical Bayes shrinkage supports analysis at *n* = 3 ([Ritchie et al., 2015](https://doi.org/10.1093/nar/gkv007), doi:10.1093/nar/gkv007). A Benjamini-Hochberg false-discovery rate is applied within each fraction independently, since across-fraction comparisons are likely confounded by run order.

**EV markers (auxiliary).** A script for analysis of extracellular vesicle marker proteins is provided at `r/sections/aux/ev-markers.R`, informed by the MISEV 2023 guidelines ([Welsh et al., 2024](https://doi.org/10.1002/jev2.12404), doi:10.1002/jev2.12404). It is run manually rather than through `--section`.

### R packages
Install the required R packages by running:

```bash
Rscript src/comms/r/install_deps.R
```

If R is not available, `report` exits with an informative error.

Package | Source
---|---
`tidyverse` | CRAN
`openxlsx2` | CRAN
`svglite` | CRAN
`ggrepel` | CRAN
`ggfortify` | CRAN
`cluster` | CRAN
`UpSetR` | CRAN
`pheatmap` | CRAN
`VennDiagram` | CRAN
`limma` | Bioconductor

---

<div align="right">

**comMS documentation:** _Commands_ · [Configuration][docs-config] · [Configuration reference][docs-config-ref] · [Output structure][docs-output] · [README][docs-readme]

</div>

<!-- MARKDOWN LINKS & IMAGES -->
[docs-commands]: ./commands.md#commands
[docs-config-ref]: ./config-reference.md#configuration-reference
[docs-config]: ./configuration.md#configuration
[docs-output]: ./output-structure.md#output-structure
[docs-readme]: ../README.md#comms