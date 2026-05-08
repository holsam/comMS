#!/bin/R
# secondary_species.R — secondary species protein detection

# Parse passed arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]
quantify_dir <- args[2]
sample_sheet <- args[3]
ref_info_path <- args[4]
cont_csv_path <- args[5]
organism_prefix <- args[6]
min_reps <- as.integer(args[7])

# Import utility functions
script_dir <- dirname(sys.frame(1)$ofile)
source(file.path(script_dir, "../utils/import.R"))
source(file.path(script_dir, "../utils/theme.R"))

# Load libraries
library(svglite)
library(VennDiagram)

# Import files
ref_info <- loadRefInfo(ref_info_path)
cont_info <- loadContInfo(cont_csv_path)
samples <- loadSampleSheet(sample_sheet)
results_list <- importSpectralCountFiles(quantify_dir, ref_info, cont_info)
results_wide <- mergeResults(results_list)
dnsaf_cols <- colnames(results_wide)[startsWith(colnames(results_wide), "dNSAF_")]
sample_meta <- buildSampleMetadata(str_remove(dnsaf_cols, "dNSAF_"), samples)

# Filter for proteins from secondary species
secondary <- results_wide %>%
  filter(!startsWith(proteinId, organism_prefix))

fractions <- unique(sample_meta$fraction)
fraction_sets <- list()
for (frac in fractions) {
  frac_cols <- intersect(filter(sample_meta, fraction==frac)$dnsaf_col, colnames(secondary))
  fraction_sets[[frac]] <- secondary %>%
    filter(rowSums(select(., all_of(frac_cols)) > 0) >= min_reps) %>%
    pull(proteinId)
}

# Generate Venn diagram of secondary species proteins across fractions
if (length(fraction_sets) >= 2) {
  venn_data <- venn.diagram(fraction_sets, filename=NULL, disable.logging=TRUE, category.names=names(fraction_sets))
  ggsave(file.path(output_dir, "secondary_species_venn.svg"), venn_data)
}

# Export .xlsx spreadsheet: all detected secondary species proteins, annotated by fraction
all_candidates <- bind_rows(lapply(names(fraction_sets), function(frac) {
  filter(secondary, proteinId %in% fraction_sets[[frac]]) %>% mutate(Fraction=frac)
})) %>% distinct(proteinId, Fraction, .keep_all=TRUE)

wb <- wb_workbook()
wb$add_worksheet("Secondary_Species")
wb$add_data("Secondary_Species", all_candidates)
wb_save(wb, file.path(output_dir, "secondary_species_candidates.xlsx"))
message("Secondary species section complete")