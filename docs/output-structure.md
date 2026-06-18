<div align="right">

**comMS documentation:** [Configuration](./configuration.md) · [Configuration reference](./config-reference.md) · [Commands](./commands.md) · _Output structure_ · [README](../README.md)

</div>

# Output structure

This page describes the directory structure that comMS uses to write results and logs. For how the output root is chosen, see [experiment context](./configuration.md#experiment-context).

## Contents
- [Results layout](#results-layout)
- [Logging](#logging)

## Results layout
All outputs are written under the experiment root, inside `comms/results/`. Each command has its own subdirectory:
```
<experiment_root>/
  └─ comms/
     └─ results/
        ├─ convert/                # indexed .mzML files
        ├─ index/                  # Crux tide-index output
        ├─ search/                 # Crux tide-search target PSM files
        ├─ rescore/                # combined Percolator rescored PSM files
        │  └─ <organism>/          # per-organism split PSMs and assign-confidence output
        ├─ lfq/                    # MS1 label-free quantification output
        │  └─ <fraction>/          # FlashLFQ output for each fraction
        ├─ quantify/               # dNSAF spectral-counts output
        └─ report/                 # report output
           ├─ index.md             # index of produced files, parameters, and section status
           ├─ qc/                  # quality-control plots and spreadsheet
           ├─ pca/                 # PCA and dendrogram plots
           ├─ da/                  # differential abundance plots and spreadsheet
           ├─ secondary_species/   # secondary-species plots and spreadsheet
           └─ concordance/         # LFQ vs dNSAF concordance (only if --lfq-dir is provided)
```

If a command's output directory already exists, comMS does not overwrite it. Instead it adds an incremental suffix, for example `search-1/`, then `search-2/`, so earlier results are preserved.

## Logging
comMS logs to both the terminal and a file.

### Log levels
Errors, warnings, and high-level information are always shown. Verbosity flags enable more detail:

Level | Enabled with | Used for
---|---|---
`debug` | `-vv` | Detailed program state for debugging: the command invoked, paths scanned, resolved parameters, and per-item detail
`progress` | `-v` | Step-wise progress: per-file and per-stage markers
`info` | always on | High-level overview: processing counts and final results
`warn` | always on | A part of a command did not succeed but comMS continued, for example a single item failed, an optional input was missing, or a fallback value was used
`error` | always on | A part of a command did not succeed and comMS could not continue

`-vv` implies `-v`.

### Log files
comMS logs to standard output (the terminal you ran the command from) and to a file named after the command (`comms convert`, for example, writes to `convert.log`). The log file is saved alongside that command's other output, so running the same command again does not overwrite an earlier log.

---

<div align="right">

**comMS documentation:** [Configuration](./configuration.md) · [Configuration reference](./config-reference.md) · [Commands](./commands.md) · _Output structure_ · [README](../README.md)

</div>