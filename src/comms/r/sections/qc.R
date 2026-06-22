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

# Per-sample NSAF density plot
dnsaf_long <- results_wide %>%
  select(proteinId, all_of(dnsaf_cols)) %>%
  pivot_longer(-proteinId, names_to="Sample", values_to="dNSAF") %>%
  filter(dNSAF > 0) %>%
  mutate(log_dNSAF=log(dNSAF), Sample=str_remove(Sample, "dNSAF_"))
density_plot <- ggplot(dnsaf_long, aes(x=log_dNSAF, colour=Sample)) +
  geom_density() + theme_comms() +
  labs(x="log(dNSAF)", y="Density", title="Per-sample dNSAF distributions") +
  theme(legend.position="bottom")
svglite(file.path(output_dir, "dnsaf_distributions.svg"), width=10, height=6)
print(density_plot); dev.off()

# Total spectral counts per sample
spec_counts <- bind_rows(lapply(names(results_list), function(nm) {
  tibble(Sample=nm, TotalSpectra=sum(results_list[[nm]]$spec_count_all, na.rm=TRUE))
}))
counts_plot <- ggplot(spec_counts, aes(x=Sample, y=TotalSpectra)) +
  geom_col(fill="#88CCEE") + theme_comms() +
  theme(axis.text.x=element_text(angle=45, hjust=1)) +
  labs(x=NULL, y="Total spectral counts", title="Spectral counts per sample")
svglite(file.path(output_dir, "spectral_counts_per_sample.svg"), width=10, height=5)
print(counts_plot); dev.off()

# Missing-value upset plot
presence_matrix <- results_wide %>%
  select(all_of(dnsaf_cols)) %>%
  mutate(across(everything(), ~as.integer(. > 0)))
colnames(presence_matrix) <- str_remove(dnsaf_cols, "dNSAF_")
svglite(file.path(output_dir, "missing_values_upset.svg"), width=12, height=7)
upset(as.data.frame(presence_matrix), nsets=ncol(presence_matrix),
      order.by="freq", mainbar.y.label="Proteins", sets.x.label="Proteins detected")
dev.off()

# Presence/absence heatmap
svglite(file.path(output_dir, "presence_absence_heatmap.svg"), width=10, height=8)
pheatmap(as.matrix(presence_matrix), color=c("white","#117733"),
         legend_breaks=c(0,1), legend_labels=c("Absent","Present"),
         main="Protein presence/absence", fontsize=10)
dev.off()

# QC summary Excel
n_detected <- results_wide %>%
  summarise(across(all_of(dnsaf_cols), ~sum(.>0))) %>%
  pivot_longer(everything(), names_to="Sample", values_to="ProteinsDetected") %>%
  mutate(Sample=str_remove(Sample, "dNSAF_"))
qc_summary <- left_join(spec_counts, n_detected, by="Sample")
wb <- wb_workbook()
wb$add_worksheet("QC_Summary"); wb$add_data("QC_Summary", qc_summary)
wb_save(wb, file.path(output_dir, "qc_summary.xlsx"))
message("QC section complete")