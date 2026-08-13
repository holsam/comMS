<div align="right">

**comMS documentation:** [Commands][docs-commands] · [Configuration][docs-config] · _Configuration reference_ · [Output structure][docs-output] · [README][docs-readme]

</div>

# Configuration reference

This page lists the values comMS reads from its configuration file: the protocol flags applied by `comms config`, and the default convert, index, search, rescore, quantify, and report parameters. For where configuration files live and how they are resolved, see [Configuration][docs-config].

## Contents
- [Protocol flags](#protocol-flags)
- [Other configuration flags](#other-configuration-flags)
- [Default convert parameters](#default-convert-parameters)
- [Default index parameters](#default-index-parameters)
- [Default search parameters](#default-search-parameters)
- [Default rescore parameters](#default-rescore-parameters)
- [Default quantify parameters](#default-quantify-parameters)
- [Default report parameters](#default-report-parameters)

## Protocol flags
`comms config` applies experiment-specific presets when passed value-setting flags (see [Editing configuration][docs-config] for how the target file is resolved). Flags can be combined in a single call, and most take a positive and a negative form (for example `--ox` / `--no-ox`). This first table covers the peptide-modification and digestion presets used by `index`; the full set of remaining configuration flags, covering `convert`, `search`, `rescore`, `quantify`, and `report`, is in [Other configuration flags](#other-configuration-flags) below.

Flag | Effect | Mass | Config key
---|---|---|---
`--iodo` / `--no-iodo` | Static cysteine carbamidomethylation | `C+57.0215` | `index.fixed_mods`
`--ox` / `--no-ox` | Variable methionine oxidation | `1M+15.9949` | `index.mods_spec`
`--phos` / `--no-phos` | Variable serine/threonine/tyrosine phosphorylation | `1STY+79.966331` | `index.mods_spec`
`--n-cyc` / `--no-n-cyc` | N-terminal Gln to pyro-Glu cyclisation | `1Q-17.027` | `index.nterm_peptide_mods_spec`
`--n-ace` / `--no-n-ace` | Protein N-terminal acetylation | `1X+42.011` | `index.nterm_protein_mods_spec`
`--clip-met` / `--no-clip-met` | Duplicate peptides with the N-terminal methionine clipped | n/a | `index.clip_n_met`
`--missed-cleavages` | Number of missed enzymatic cleavages allowed | n/a | `index.missed_cleavages`
`--high-res` / `--low-res` | Instrument resolution preset | n/a | `search.mz_bin_width`, `search.score_function`
`--custom` | Add or clear a custom Tide `mods_spec` entry | user-defined | `index.custom_mods`
`--organism` | Define label-to-pattern pairs for per-organism FDR | n/a | `[organism]`

A few flags need more explanation:

**Cysteine alkylation (`--iodo`)** Add `--iodo` only if iodoacetamide alkylation was performed during sample preparation.

**Custom modifications (`--custom`)** Custom entries are stored separately and merged with the named-flag modifications at search time. The flag is repeatable, so several entries can be added in one call, and passing an empty string clears them all:

```bash
comms config --custom "1K+28.0313"                         # add one entry
comms config --custom "1K+28.0313" --custom "1R+14.0157"   # add several
comms config --custom ""                                   # clear all custom entries
```

Passing a modification that is already managed by a named flag (for example `1M+15.9949`, which belongs to `--ox`) produces a warning and is not added. Use the named flag instead. Running `comms config` with no flags shows both the named-flag and custom values.

**Instrument resolution (`--high-res` / `--low-res`)**

```bash
comms config --high-res    # mz_bin_width = 0.02, score_function = xcorr (default)
comms config --low-res     # mz_bin_width = 1.0005079, score_function = combined-p-value
```

Use `--high-res` for Orbitrap data, the default for modern instruments. Use `--low-res` for ion-trap MS2 data, such as that from older LTQ instruments.

**Organism patterns (`--organism`)**

```bash
comms config --organism Org1=Pattern1 Org2=Pattern2
```

Each argument takes the form `Label=Pattern`, where `Pattern` is matched as a regular expression against FASTA headers. The pairs are used to split a combined FASTA by organism during the rescore step, which enables per-organism picked-protein FDR. Once set, they are applied automatically by `pipeline` and `rescore` unless overridden with `--organism-tags` on the command line. See the [rescore command documentation]((./commands.md#per-organism-fdr)) for the runtime form.

## Other configuration flags
These flags configure `convert`, `search`, `rescore`, `quantify`, and `report` behaviour. As with the protocol flags above, each can be set on a config file via `comms config`, and most can also be overridden for a single run by passing the same flag directly to the corresponding command.

Flag | Effect | Config key
---|---|---
`--gzip` / `--no-gzip` | Gzip-compress mzML output | `convert.gzip`
`--format` | ThermoRawFileParser output format code | `convert.format`
`--metadata` | ThermoRawFileParser metadata capture code | `convert.metadata`
`--score-function` | Tide-search score function | `search.score_function`
`--min-peaks` | Minimum peaks required per spectrum | `search.min_peaks`
`--precursor-tolerance-ppm` | Precursor mass tolerance (ppm) | `search.precursor_tolerance_ppm`
`--mz-bin-width` | Fragment m/z bin width (Da) | `search.mz_bin_width`
`--threads` | Default number of threads | `search.threads`
`--protein-enzyme` | Enzyme used for protein-level picked-FDR grouping | `rescore.protein_enzyme`
`--picked-protein` / `--no-picked-protein` | Use picked-protein FDR | `rescore.picked_protein`
`--shared-psm` | Policy for PSMs shared between organisms (`drop`/`include`) | `rescore.shared_psm`
`--measure` | Spectral-counting measure (`NSAF`/`dNSAF`/`SIN`/`EMPAI`) | `quantify.measure`
`--qvalue-threshold` | PSM q-value threshold for quantification | `quantify.qvalue_threshold`
`--unique-mapping` / `--no-unique-mapping` | Require unique peptide-to-protein mapping | `quantify.unique_mapping`
`--min-reps` | Minimum replicates per fraction-treatment group | `report.min_reps`
`--lfc-threshold` | \|log2FC\| threshold for differential abundance | `report.lfc_threshold`
`--fdr-threshold` | BH-FDR threshold for differential abundance | `report.fdr_threshold`
`--top-n` | Number of top DA proteins labelled per volcano plot | `report.top_n_proteins`

`--score-function`, `--min-peaks`, `--precursor-tolerance-ppm`, and `--mz-bin-width` are also accepted directly by `search`, where `--precursor-tolerance-ppm`/`--mz-bin-width` take priority over `--param-medic` if both are given for the same run.

## Default convert parameters

Parameter | Default | Description | Config key
-- | -- | -- | --
Format | 2 | ThermoRawFileParser output format code (2 = indexed mzML) | `convert.format`
Gzip | True | Compress mzML output | `convert.gzip`
Metadata | 0 | ThermoRawFileParser metadata capture code (0 = JSON metadata) | `convert.metadata`

## Default index parameters
Peptide indices are generated with the following parameters:

Parameter | Default | Description | Crux equivalent | Config flag
-- | -- | -- | -- | --
Protease | trypsin | Use tryptic digestion rules | `--enzyme` | n/a
Digestion | full | Completely digest proteins | `--digestion` | n/a
Missed cleavages | 2 | Maximum missed cleavage sites | `--missed-cleavages` | n/a
Leading peptide clipping | True | Duplicate leading peptides with one lacking N-terminal methionine | `--clip-nterm-methionine` | `--clip-met` / `--no-clip-met`
Duplicate decoys | True | Allow duplicated decoy proteins | `--allow-dups` | n/a
Number of decoys | 1 | Decoy peptides per target | `--num-decoys-per-target` | n/a
Decoy strategy | reverse | Generate decoys by reversing residues | `--decoy-format` | n/a
M oxidation | True | Variable methionine oxidation (`1M+15.9949`) | `--mods-spec` | `--ox` / `--no-ox`
STY phosphorylation | False | Variable STY phosphorylation (`1STY+79.966331`) | `--mods-spec` | `--phos` / `--no-phos`
Cys carbamidomethylation | False | Static cysteine carbamidomethylation (`C+57.0215`) | `--fixed-modifications` | `--iodo` / `--no-iodo`
Peptide N-cyclisation | True | Cyclisation of Gln to pyro-Glu at peptide N-termini (`1Q-17.027`) | `--nterm-peptide-mods-spec` | `--n-cyc` / `--no-n-cyc`
Protein N-acetylation | True | Acetylation of the protein N-terminal residue (`1X+42.011`) | `--nterm-protein-mod-spec` | `--n-ace` / `--no-n-ace`

Any proteome processed with the `index` command should also include contaminant protein sequences, such as those in the [cRAP contaminant dataset](https://www.thegpm.org/crap/).

## Default search parameters
The default configuration applies the following search parameters, informed by [Svozil & Baerenfaller, 2017](https://doi.org/10.1016/bs.mie.2016.11.007) (doi:10.1016/bs.mie.2016.11.007):

Parameter | Default | Description | Config key
-- | -- | -- | --
Precursor tolerance | 10 ppm | Precursor mass window | search.precursor_tolerance_ppm
Minimum peaks | 10 | Minimum peaks required per spectrum | search.min_peaks
Bin width | 0.02 | `mz_bin_width` for high-resolution data (see [instrument resolution](#protocol-flags)) | search.mz_bin_width
Score function | xcorr | Scoring for high-resolution data (see [instrument resolution](#protocol-flags)) | search.score_function
Threads | 2 | Default search threads | search.threads

## Default rescore parameters
By default, PSM rescoring uses picked-protein FDR ([Savitski et al., 2015](https://doi.org/10.1074/mcp.M114.046995), doi:10.1074/mcp.M114.046995) at a 1% PSM-level FDR threshold, requiring at least two unique peptides per protein for a confident identification.

When a combined multi-species FASTA is used, picked-protein FDR is applied separately per organism. Organism patterns are configured with `comms config --organism`, or supplied at runtime with `--organism-tags` on the `rescore` and `pipeline` commands. See the [rescore command documentation](./commands.md#per-organism-fdr) for details. For multi-species analyses, the handling policy used in the case of shared PSMs can be set to `'drop'` (default; do not include in either organism) or `'include'` (include in both organisms). The latter option may inflate downstream spectral counts for shared PSMs, so the default option is `'drop'`.

Parameter | Default | Description | Config key
-- | -- | -- | --
Protease | Trypsin | Protease used for protein digestion | rescore.protein_enzyme
Picked-protein FDR |  True | Enable picked-protein FDR | rescore.picked_protein
Shared PSM strategy | drop | Strategy used to handle PSMs shared between organisms | rescore.shared_psm

## Default quantify parameters

Parameter | Default | Description | Config key
-- | -- | -- | --
Measure | `dNSAF` | Spectral-counting measure | `quantify.measure`
Q-value threshold | 0.01 | PSM q-value threshold for inclusion | `quantify.qvalue_threshold`
Unique mapping | True | Require unique peptide-to-protein mapping | `quantify.unique_mapping`

## Default report parameters

Parameter | Default | Description | Config key
-- | -- | -- | --
Minimum replicates | 3 | Minimum replicates per fraction-treatment group | `report.min_reps`
Log2FC threshold | 1.0 | \|log2FC\| threshold for differential abundance | `report.lfc_threshold`
FDR threshold | 0.05 | BH-FDR threshold for differential abundance | `report.fdr_threshold`
Top-N proteins | 20 | Number of top DA proteins labelled per volcano plot | `report.top_n_proteins`

---

<div align="right">

**comMS documentation:** [Commands][docs-commands] · [Configuration][docs-config] · _Configuration reference_ · [Output structure][docs-output] · [README][docs-readme]

</div>

<!-- MARKDOWN LINKS & IMAGES -->
[docs-commands]: ./commands.md#commands
[docs-config-ref]: ./config-reference.md#configuration-reference
[docs-config]: ./configuration.md#configuration
[docs-output]: ./output-structure.md#output-structure
[docs-readme]: ../README.md#comms