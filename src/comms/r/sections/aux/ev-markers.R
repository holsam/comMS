#!/bin/R
# aux/ev_markers.R: MISEV2023-compatible EV marker assessment

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
source(file.path(script_dir, "..", "..", "utils", "import.R"))
source(file.path(script_dir, "..", "..", "utils", "normalise.R"))
source(file.path(script_dir, "..", "..", "utils", "theme.R"))

# Load libraries
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

MISEV_LEVELS <- c(
  "Category 1: transmembrane EV",
  "Category 2: cytosolic EV-associated",
  "Category 3: negative marker"
)

MISEV_CATEGORY_1 <- c("tetraspanin", "SNARE", "synaptotagmin")
MISEV_CATEGORY_2 <- c("ESCRT", "Rab", "exocyst", "flotillin")
MISEV_CATEGORY_3 <- c("GAPDH", "BiP", "histone", "Rubisco")

categorise_marker <- function(annotation) {
  a <- tolower(annotation)
  if (any(str_detect(a, tolower(MISEV_CATEGORY_1)))) return(MISEV_LEVELS[1])
  if (any(str_detect(a, tolower(MISEV_CATEGORY_2)))) return(MISEV_LEVELS[2])
  if (any(str_detect(a, tolower(MISEV_CATEGORY_3)))) return(MISEV_LEVELS[3])
  return(NA_character_)
}

organisms <- unique(sample_meta$organism)
all_marker_tables <- list()

for (org in organisms) {
  org_meta <- filter(sample_meta, organism == org)
  org_cols <- org_meta$dnsaf_col
  # EV markers are only meaningful for the primary organism: skip any organism whose dNSAF columns contain no primary-organism proteins
  primary_check <- results_wide %>%
    filter(startsWith(proteinId, organism_prefix)) %>%
    filter(rowSums(select(., all_of(org_cols)) > 0) > 0)

  if (nrow(primary_check) == 0) {
    message(sprintf("EV markers: no primary organism proteins in %s columns — skipping", org))
    next
  }

  fractions <- unique(org_meta$fraction)

  org_data <- results_wide %>%
    filter(startsWith(proteinId, organism_prefix)) %>%
    filter(rowSums(select(., all_of(org_cols)) > 0) > 0)

  # Per-fraction mean dNSAF
  for (frac in fractions) {
    cols <- intersect(filter(org_meta, fraction == frac)$dnsaf_col, colnames(org_data))
    org_data[[paste0("avg_", frac)]] <-
      if (length(cols) > 0) rowMeans(select(org_data, all_of(cols)), na.rm=TRUE) else NA_real_
  }

  marker_table <- org_data %>%
    rowwise() %>%
    mutate(MISEVCategory=categorise_marker(proteinAnnotation)) %>%
    ungroup() %>%
    filter(!is.na(MISEVCategory)) %>%
    mutate(MISEVCategory=factor(MISEVCategory, levels=MISEV_LEVELS)) %>%
    arrange(MISEVCategory)

  if (nrow(marker_table) == 0) {
    message(sprintf("EV markers %s: no marker proteins found — skipping", org)); next
  }

  # Enrichment ratios
  ev_frac <- fractions[str_detect(tolower(fractions), "ev")][1]
  wcl_frac <- fractions[str_detect(tolower(fractions), "wcl")][1]
  awf_frac <- fractions[str_detect(tolower(fractions), "awf|cr")][1]
  if (!is.na(ev_frac) && !is.na(wcl_frac))
    marker_table <- mutate(marker_table, log2_EV_vs_WCL=log2((.data[[paste0("avg_", ev_frac)]] + 1e-10) / (.data[[paste0("avg_", wcl_frac)]] + 1e-10))
  if (!is.na(ev_frac) && !is.na(awf_frac))
    marker_table <- mutate(marker_table, log2_EV_vs_AWF=log2((.data[[paste0("avg_", ev_frac)]] + 1e-10) / (.data[[paste0("avg_", awf_frac)]] + 1e-10)))

  # Per-protein heatmap with category gaps
  avg_cols <- intersect(paste0("avg_", fractions), colnames(marker_table))
  heatmap_mat <- marker_table %>%
    select(proteinAnnotation, all_of(avg_cols)) %>%
    column_to_rownames("proteinId") %>%
    as.matrix() %>%
    logdNSAF()
  colnames(heatmap_mat) <- str_remove(colnames(heatmap_mat), "avg_")
  ann_row <- data.frame(Category=as.character(marker_table$MISEVCategory), row.names=marker_table$proteinAnnotation)
  gaps_row <- marker_table %>%
    count(MISEVCategory) %>%
    arrange(MISEVCategory) %>%
    pull(n) %>%
    cumsum() %>%
    head(-1)
  svglite(file.path(output_dir, sprintf("marker_heatmap_%s.svg", org)), width=12, height=max(6, nrow(heatmap_mat) * 0.35))
  pheatmap(heatmap_mat, annotation_row=ann_row, gaps_row=gaps_row, cluster_rows=FALSE, colour=colorRampPalette(c("#88CCEE", "white", "#CC6677"))(50), main=sprintf("MISEV2023 markers — log(dNSAF) — %s", org), fontsize_row=8, fontsize_col=10, border_colour=NA)
  dev.off()

  # Aggregated category heatmap (3 × fraction×treatment)
  agg_mat <- marker_table %>%
    select(MISEVCategory, all_of(org_cols)) %>%
    pivot_longer(-MISEVCategory, names_to="dnsaf_col", values_to="dNSAF") %>%
    left_join(select(org_meta, dnsaf_col, fraction, treatment), by="dnsaf_col") %>%
    mutate(log_dNSAF=logdNSAF(dNSAF)) %>%
    group_by(MISEVCategory, fraction, treatment) %>%
    summarise(mean_log_dNSAF=mean(log_dNSAF, na.rm=TRUE), .groups="drop") %>%
    mutate(col_label=paste(fraction, treatment, sep="_")) %>%
    select(MISEVCategory, col_label, mean_log_dNSAF) %>%
    pivot_wider(names_from=col_label, values_from=mean_log_dNSAF) %>%
    arrange(MISEVCategory) %>%
    column_to_rownames("MISEVCategory") %>%
    as.matrix()

  svglite(file.path(output_dir, sprintf("marker_category_heatmap_%s.svg", org)), width=8, height=4)
  pheatmap(agg_mat, cluster_rows=FALSE, cluster_cols=FALSE, colour=colorRampPalette(c("#88CCEE", "white", "#CC6677"))(50), main=sprintf("Mean log(dNSAF) by MISEV category — %s", org), fontsize=10, border_colour=NA)
  dev.off()

  all_marker_tables[[org]] <- marker_table
}
# Export .xlsx — one sheet per organism
wb <- wb_workbook()
for (org in names(all_marker_tables)) {
  wb$add_worksheet(org); wb$add_data(org, all_marker_tables[[org]])
}
wb_save(wb, file.path(output_dir, "ev_markers.xlsx"))
message("EV markers section complete")