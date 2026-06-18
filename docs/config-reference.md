<div align="right">

**comMS documentation:** [Commands][docs-commands] · [Configuration][docs-config] · _Configuration reference_ · [Output structure][docs-output] · [README][docs-readme]

</div>

# Configuration reference

This page lists the values comMS reads from its configuration file: the protocol flags applied by `comms config set`, and the default index, search, and Percolator parameters. For where configuration files live and how they are resolved, see [Configuration][docs-config].

## Contents
- [Protocol flags](#protocol-flags)
- [Default index parameters](#default-index-parameters)
- [Default search parameters](#default-search-parameters)
- [Percolator settings](#percolator-settings)

## Protocol flags
`comms config set` applies experiment-specific presets. Flags can be combined in a single call, and most take a positive and a negative form (for example `--ox` / `--no-ox`).

Flag | Effect | Mass | Config key
---|---|---|---
`--iodo` / `--no-iodo` | Static cysteine carbamidomethylation | `C+57.0215` | `index.fixed_mods`
`--ox` / `--no-ox` | Variable methionine oxidation | `1M+15.9949` | `index.mods_spec`
`--phos` / `--no-phos` | Variable serine/threonine/tyrosine phosphorylation | `1STY+79.966331` | `index.mods_spec`
`--n-cyc` / `--no-n-cyc` | N-terminal Gln to pyro-Glu cyclisation | `1Q-17.027` | `index.nterm_peptide_mods_spec`
`--n-ace` / `--no-n-ace` | Protein N-terminal acetylation | `1X+42.011` | `index.nterm_protein_mods_spec`
`--clip-met` / `--no-clip-met` | Duplicate peptides with the N-terminal methionine clipped | n/a | `index.clip_n_met`
`--high-res` / `--low-res` | Instrument resolution preset | n/a | `search.mz_bin_width`, `search.score_function`
`--custom` | Add or clear a custom Tide `mods_spec` entry | user-defined | `custom_mods`
`--organism` | Define label-to-pattern pairs for per-organism FDR | n/a | `[organism]`

A few flags need more explanation:

**Cysteine alkylation (`--iodo`)** Add `--iodo` only if iodoacetamide alkylation was performed during sample preparation.

**Custom modifications (`--custom`)** Custom entries are stored separately and merged with the named-flag modifications at search time. The flag is repeatable, so several entries can be added in one call, and passing an empty string clears them all:

```bash
comms config set --custom "1K+28.0313"                         # add one entry
comms config set --custom "1K+28.0313" --custom "1R+14.0157"   # add several
comms config set --custom ""                                   # clear all custom entries
```

Passing a modification that is already managed by a named flag (for example `1M+15.9949`, which belongs to `--ox`) produces a warning and is not added. Use the named flag instead. `comms config list` shows both the named-flag and custom values.

**Instrument resolution (`--high-res` / `--low-res`)**

```bash
comms config set --high-res    # mz_bin_width = 0.02, score_function = xcorr (default)
comms config set --low-res     # mz_bin_width = 1.0005079, score_function = combined-p-value
```

Use `--high-res` for Orbitrap data, the default for modern instruments. Use `--low-res` for ion-trap MS2 data, such as that from older LTQ instruments.

**Organism patterns (`--organism`)**

```bash
comms config set --organism Org1=Pattern1 Org2=Pattern2
```

Each argument takes the form `Label=Pattern`, where `Pattern` is matched as a regular expression against FASTA headers. The pairs are used to split a combined FASTA by organism during the rescore step, which enables per-organism picked-protein FDR. Once set, they are applied automatically by `pipeline` and `rescore` unless overridden with `--organism-tags` on the command line. See the [rescore command documentation]((./commands.md#per-organism-fdr)) for the runtime form.

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

Parameter | Default | Description
-- | -- | --
Precursor tolerance | 10 ppm | Precursor mass window
Minimum peaks | 10 | Minimum peaks required per spectrum
Bin width | 0.02 | `mz_bin_width` for high-resolution data (see [instrument resolution](#protocol-flags))
Score function | xcorr | Scoring for high-resolution data (see [instrument resolution](#protocol-flags))
Threads | 2 | Default search threads

## Percolator settings
By default, PSM rescoring uses picked-protein FDR ([Savitski et al., 2015](https://doi.org/10.1074/mcp.M114.046995), doi:10.1074/mcp.M114.046995) at a 1% PSM-level FDR threshold, requiring at least two unique peptides per protein for a confident identification.

When a combined multi-species FASTA is used, picked-protein FDR is applied separately per organism. Organism patterns are configured with `comms config set --organism`, or supplied at runtime with `--organism-tags` on the `rescore` and `pipeline` commands. See the [rescore command documentation](./commands.md#per-organism-fdr) for details.

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