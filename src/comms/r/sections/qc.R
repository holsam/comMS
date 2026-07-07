#!/bin/R
# qc.R: quality checking and pre-processing section

# Parse passed arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]
quantify_dir <- args[2]
sample_sheet <- args[3]
ref_info_path <- args[4]
cont_csv_path <- args[5]
organism_prefix <- args[6]
min_reps <- as.integer(args[7])

# Get script directory for path traversal
script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  script <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", script)))
})

# Import utility functions
source(file.path(script_dir, "..", "utils", "import.R"))
source(file.path(script_dir, "..", "utils", "normalise.R"))
source(file.path(script_dir, "..", "utils", "theme.R"))

# Load libraries
library(UpSetR)
library(pheatmap)
library(svglite)

# Import files
ref_info <- loadRefInfo(ref_info_path)
cont_info <- loadContInfo(cont_csv_path)
samples <- loadSampleSheet(sample_sheet)
results_list <- importSpectralCountFiles(quantify_dir, ref_info, cont_info)
results_wide <- mergeResults(results_list)
dnsaf_cols <- colnames(results_wide)[startsWith(colnames(results_wide), "dNSAF_")]
sample_meta <- buildSampleMetadata(str_remove(dnsaf_cols, "dNSAF_"), samples)

organisms <- unique(sample_meta$organism)
for (org in organisms) {
  org_meta <- filter(sample_meta, organism == org)
  org_cols <- org_meta$dnsaf_col
  label_map <- setNames(org_meta$sample_id, org_meta$dnsaf_col)

  org_data <- results_wide %>%
    filter(rowSums(select(., all_of(org_cols)) > 0) > 0)

  # Per-sample dNSAF density plot
  dnsaf_long <- org_data %>%
    select(proteinId, all_of(org_cols)) %>%
    pivot_longer(-proteinId, names_to="Sample", values_to="dNSAF") %>%
    filter(dNSAF > 0) %>%
    mutate(log_dNSAF=log(dNSAF), Sample=label_map[Sample])
  density_plot <- ggplot(dnsaf_long, aes(x=log_dNSAF, colour=Sample)) +
    geom_density() + theme_comms() +
    labs(x="log(dNSAF)", y="Density", title=sprintf("Per-sample dNSAF distributions — %s", org)) +
    theme(legend.position="bottom")
  svglite(file.path(output_dir, sprintf("dnsaf_distributions_%s.svg", org)), width=10, height=6)
  print(density_plot); dev.off()

  # Total spectral counts per sample
  spec_counts <- bind_rows(lapply(org_cols, function(col) {
    nm <- str_remove(col, "dNSAF_")
    if (!nm %in% names(results_list)) return(NULL)
    tibble(Sample=label_map[col], TotalSpectra=sum(results_list[[nm]]$`RAW`, na.rm=TRUE))
  })) %>% compact() %>% bind_rows()
  counts_plot <- ggplot(spec_counts, aes(x=Sample, y=TotalSpectra)) +
    geom_col(fill="#88CCEE") + theme_comms() +
    theme(axis.text.x=element_text(angle=45, hjust=1)) +
    labs(x=NULL, y="Total spectral counts", title=sprintf("Spectral counts per sample — %s", org))
  svglite(file.path(output_dir, sprintf("spectral_counts_per_sample_%s.svg", org)), width=10, height=5)
  print(counts_plot); dev.off()

  # Missing-value upset plot
  presence_matrix <- org_data %>%
    select(all_of(org_cols)) %>%
    mutate(across(everything(), ~as.integer(. > 0)))
  colnames(presence_matrix) <- label_map[colnames(presence_matrix)]
  svglite(file.path(output_dir, sprintf("missing_values_upset_%s.svg", org)), width=12, height=7)
  upset(as.data.frame(presence_matrix), nsets=ncol(presence_matrix), order.by="freq", mainbar.y.label="Proteins", sets.x.label="Proteins detected")
  dev.off()

  # Presence/absence heatmap
  svglite(file.path(output_dir, sprintf("presence_absence_heatmap_%s.svg", org)), width=10, height=8)
  pheatmap(as.matrix(presence_matrix), color=c("white", "#117733"), legend_breaks=c(0, 1), legend_labels=c("Absent", "Present"), main=sprintf("Protein presence/absence — %s", org), fontsize=10)
  dev.off()

  # QC summary Excel
  n_detected <- org_data %>%
    summarise(across(all_of(org_cols), ~sum(. > 0))) %>%
    pivot_longer(everything(), names_to="dnsaf_col", values_to="ProteinsDetected") %>%
    mutate(Sample=label_map[dnsaf_col]) %>%
    select(Sample, ProteinsDetected)
  qc_summary <- left_join(spec_counts, n_detected, by="Sample")
  wb <- wb_workbook()
  wb$add_worksheet(org); wb$add_data(org, qc_summary)
  wb_save(wb, file.path(output_dir, sprintf("qc_summary_%s.xlsx", org)))
}
message("QC section complete")