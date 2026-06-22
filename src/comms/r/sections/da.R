#!/bin/R
# da.R: differential abundance section

# Parse passed arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]
quantify_dir <- args[2]
sample_sheet <- args[3]
ref_info_path <- args[4]
cont_csv_path <- args[5]
organism_prefix <- args[6]
min_reps <- as.integer(args[7])
lfc_threshold <- as.numeric(args[8])
fdr_threshold <- as.numeric(args[9])

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
library(VennDiagram)

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
if (length(treatments) != 2) stop("DA section requires exactly two treatment levels.")

# Initialise list for differentially abundant results
da_results_all <- list()

# Loop through each fraction
for (frac in fractions) {
  frac_meta <- filter(sample_meta, fraction==frac)
  frac_cols <- frac_meta$dnsaf_col

  # Filter to primary organism; require >= min_reps detections per treatment group
  frac_data <- results_wide %>%
    select(proteinId, proteinAnnotation, all_of(frac_cols)) %>%
    filter(startsWith(proteinId, organism_prefix))

  for (trt in treatments) {
    trt_cols <- filter(frac_meta, treatment==trt)$dnsaf_col
    frac_data[[paste0("n_", trt)]] <- rowSums(select(frac_data, all_of(trt_cols)) > 0)
  }
  frac_data <- filter(frac_data, if_any(starts_with("n_"), ~. >= min_reps))

  if (nrow(frac_data) < 5) {
    message(sprintf("DA %s: too few proteins after replicate filter (%d) — skipping", frac, nrow(frac_data))); next
  }

  # log-transform dNSAF values before passing to limma
  log_mat <- frac_data %>%
    select(proteinId, all_of(frac_cols)) %>%
    column_to_rownames("proteinId") %>%
    as.matrix() %>%
    logdNSAF()
  # Reformat
  treatment_vec <- frac_meta %>%
    arrange(match(dnsaf_col, frac_cols)) %>%
    pull(treatment)
  
  # Calculate differential abundance for fraction
  da_res <- runLimmaDA(log_mat, treatment_vec) %>%
    classifyDA(lfc_threshold, fdr_threshold) %>%
    left_join(select(frac_data, proteinId, proteinAnnotation), by="proteinId")

  # Add to differentially abundant results list
  da_results_all[[frac]] <- da_res

  # Generate volcano plot
  top_labels <- filter(da_res, Abundance != "Unchanged") %>% slice_min(adj_pval, n=20)
  volcano <- ggplot(da_res, aes(x=log2FC, y=-log10(adj_pval), colour=Abundance)) +
    geom_point(alpha=0.7, size=1.5) +
    geom_hline(yintercept=-log10(fdr_threshold), linetype="dashed", colour="grey50") +
    geom_vline(xintercept=c(-lfc_threshold, lfc_threshold), linetype="dashed", colour="grey50") +
    geom_text_repel(data=top_labels, aes(label=proteinAnnotation), size=3, max.overlaps=15) +
    scale_colour_manual(values=c("Increased"="#CC6677","Decreased"="#88CCEE","Unchanged"="grey70")) +
    theme_comms() +
    labs(title=sprintf("DA — %s (%s vs %s)", frac, treatments[2], treatments[1]), x=expression(log[2](FC)), y=expression(-log[10](adj.p)))
  svglite(file.path(output_dir, sprintf("volcano_%s.svg", frac)), width=10, height=7)
  print(volcano); dev.off()
}

# Generate differentially abundant Venn diagrams
da_up_sets <- lapply(da_results_all, function(x) filter(x, Abundance=="Increased")$proteinId)
da_down_sets <- lapply(da_results_all, function(x) filter(x, Abundance=="Decreased")$proteinId)
if (length(da_up_sets) >= 2) {
  venn_up <- venn.diagram(da_up_sets, filename=NULL, disable.logging=TRUE, category.names=names(da_up_sets))
  ggsave(file.path(output_dir, "venn_da_up.svg"), venn_up)
  venn_down <- venn.diagram(da_down_sets, filename=NULL, disable.logging=TRUE, category.names=names(da_down_sets))
  ggsave(file.path(output_dir, "venn_da_down.svg"), venn_down)
}

# Export .xlsx spreadsheet containing one sheet per fraction
wb <- wb_workbook()
for (frac in names(da_results_all)) {
  sn <- substr(frac, 1, 31)
  wb$add_worksheet(sn); wb$add_data(sn, da_results_all[[frac]])
}
wb_save(wb, file.path(output_dir, "da_results.xlsx"))
message("DA section complete")