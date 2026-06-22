#!/bin/R
# concordance.R: determine LFQ vs dNSAF concordance

# Parse passed arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]
quantify_dir <- args[2]
sample_sheet <- args[3]
ref_info_path <- args[4]
cont_csv_path <- args[5]
organism_prefix <- args[6]
min_reps <- as.integer(args[7])
lfq_dir <- args[8]
lfc_threshold <- as.numeric(args[9])
fdr_threshold <- as.numeric(args[10])

# Get script directory for path traversal
script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  script <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", script)))
})

# Import utility functions
source(file.path(script_dir, "..", "utils", "import.R"))
source(file.path(script_dir, "..", "utils", "limma_da.R"))
source(file.path(script_dir, "..", "utils", "normalise.R"))
source(file.path(script_dir, "..", "utils", "theme.R"))

# Load libraries
library(ggrepel)
library(svglite)

# Import files
ref_info <- loadRefInfo(ref_info_path)
cont_info <- loadContInfo(cont_csv_path)
samples <- loadSampleSheet(sample_sheet)
results_list <- importSpectralCountFiles(quantify_dir, ref_info, cont_info)
results_wide <- mergeResults(results_list)
dnsaf_cols <- colnames(results_wide)[startsWith(colnames(results_wide), "dNSAF_")]
sample_meta <- buildSampleMetadata(str_remove(dnsaf_cols, "dNSAF_"), samples)

# Calculate sample fractions and treatments
fractions  <- unique(sample_meta$fraction)
treatments <- sort(unique(sample_meta$treatment))

# Load LFQ files (one per fraction subdirectory)
lfq_files <- list.files(lfq_dir, pattern="QuantifiedProteins\\.tsv", full.names=TRUE, recursive=TRUE)
if (length(lfq_files) == 0) stop("No QuantifiedProteins.tsv files found under: ", lfq_dir)
lfq_data <- bind_rows(lapply(lfq_files, function(f) {
  read_tsv(f, show_col_types=FALSE) %>% mutate(Fraction=basename(dirname(f)))
}))

# Initialise list for concordance statistics
concordance_stats <- list()

# Loop through each fraction
for (frac in fractions) {
  frac_meta <- filter(sample_meta, fraction==frac)
  frac_cols <- frac_meta$dnsaf_col

  # dNSAF DA via limma
  frac_data <- results_wide %>%
    select(proteinId, all_of(frac_cols)) %>%
    filter(startsWith(proteinId, organism_prefix))
  log_mat_dnsaf <- frac_data %>%
    column_to_rownames("proteinId") %>%
    as.matrix() %>%
    logdNSAF()
  treatment_vec <- frac_meta %>%
    arrange(match(dnsaf_col, frac_cols)) %>%
    pull(treatment)
  da_dnsaf <- runLimmaDA(log_mat_dnsaf, treatment_vec) %>%
    classifyDA(lfc_threshold, fdr_threshold) %>%
    select(proteinId, log2FC_dNSAF=log2FC, adj_pval_dNSAF=adj_pval,
           Abundance_dNSAF=Abundance)

  # LFQ DA via limma
  lfq_frac <- filter(lfq_data, Fraction==frac)
  if (nrow(lfq_frac) == 0) {
    message(sprintf("Concordance %s: no LFQ data found — skipping", frac)); next
  }
  intensity_cols <- colnames(lfq_frac)[str_starts(colnames(lfq_frac), "Intensity")]
  log_mat_lfq <- lfq_frac %>%
    select(proteinId=ProteinGroups, all_of(intensity_cols)) %>%
    column_to_rownames("proteinId") %>%
    as.matrix()
  log_mat_lfq[log_mat_lfq == 0] <- NA
  log_mat_lfq <- log2(log_mat_lfq)
  lfq_stems <- str_remove(colnames(log_mat_lfq), "^Intensity[_ ]?")
  lfq_treatment_vec <- sample_meta$treatment[match(lfq_stems, sample_meta$stem)]
  if (anyNA(lfq_treatment_vec)) {
    message(sprintf("Concordance %s: %d LFQ column(s) unmatched to sample sheet — skipping", frac, sum(is.na(lfq_treatment_vec)))); next
  }
  da_lfq <- runLimmaDA(log_mat_lfq, lfq_treatment_vec) %>%
    classifyDA(lfc_threshold, fdr_threshold) %>%
    select(proteinId, log2FC_LFQ=log2FC, adj_pval_LFQ=adj_pval, Abundance_LFQ=Abundance)
  combined <- inner_join(da_dnsaf, da_lfq, by="proteinId")
  concordance_stats[[frac]] <- combined
  r_val <- cor(combined$log2FC_dNSAF, combined$log2FC_LFQ, use="complete.obs")
  # Generate scatter plot
  scatter <- ggplot(combined, aes(x=log2FC_dNSAF, y=log2FC_LFQ)) +
    geom_point(aes(colour=Abundance_dNSAF), alpha=0.6) +
    geom_smooth(method="lm", se=FALSE, colour="black", linewidth=0.5) +
    scale_colour_manual(values=c("Increased"="#CC6677","Decreased"="#88CCEE","Unchanged"="grey70")) +
    theme_comms() +
    labs(title=sprintf("LFQ vs dNSAF concordance — %s", frac), x=expression(log[2](FC)~dNSAF), y=expression(log[2](FC)~LFQ), colour="DA (dNSAF)") +
    annotate("text", x=Inf, y=-Inf, hjust=1.1, vjust=-0.5, size=3.5, label=sprintf("r = %.2f (n=%d proteins)", r_val, nrow(combined)))
  svglite(file.path(output_dir, sprintf("lfq_vs_dnsaf_%s.svg", frac)), width=8, height=7)
  print(scatter); dev.off()
}

# Export .xlsx spreadsheet
wb <- wb_workbook()
for (frac in names(concordance_stats)) {
  sn <- substr(frac, 1, 31)
  wb$add_worksheet(sn); wb$add_data(sn, concordance_stats[[frac]])
}
wb_save(wb, file.path(output_dir, "concordance_stats.xlsx"))
message("Concordance section complete")