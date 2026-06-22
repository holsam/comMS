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

# Calculate sample fractions and treatments
fractions    <- unique(sample_meta$fraction)

# Compute per-fraction mean dNSAF
for (frac in fractions) {
  cols <- intersect(filter(sample_meta, fraction==frac)$dnsaf_col, colnames(results_wide))
  results_wide[[paste0("avg_", frac)]] <-
    if (length(cols) > 0) rowMeans(select(results_wide, all_of(cols))) else NA_real_
}


# MISEV2023 category keyword matching against protein annotations:
# - Category 1: transmembrane EV markers (should be enriched in EVs)
# - Category 2: cytosolic EV-associated (variably enriched)
# - Category 3: negative/contamination markers (should be depleted in EVs vs WCL)
MISEV_CATEGORY_1 <- c("tetraspanin", "SNARE", "synaptotagmin")
MISEV_CATEGORY_2 <- c("ESCRT", "Rab", "exocyst", "flotillin")
MISEV_CATEGORY_3 <- c("GAPDH", "BiP", "histone", "Rubisco")

categorise_marker <- function(annotation) {
  a <- tolower(annotation)
  if (any(str_detect(a, tolower(MISEV_CATEGORY_1)))) return("Category 1 — transmembrane EV")
  if (any(str_detect(a, tolower(MISEV_CATEGORY_2)))) return("Category 2 — cytosolic EV-associated")
  if (any(str_detect(a, tolower(MISEV_CATEGORY_3)))) return("Category 3 — negative marker")
  return(NA_character_)
}

marker_table <- results_wide %>%
  filter(startsWith(proteinId, organism_prefix)) %>%
  rowwise() %>%
  mutate(MISEVCategory=categorise_marker(proteinAnnotation)) %>%
  ungroup() %>%
  filter(!is.na(MISEVCategory))

# log2 enrichment ratios; fraction names matched by substring
ev_frac  <- fractions[str_detect(tolower(fractions), "ev")][1]
wcl_frac <- fractions[str_detect(tolower(fractions), "wcl")][1]
awf_frac <- fractions[str_detect(tolower(fractions), "awf|cr")][1]
if (!is.na(ev_frac) && !is.na(wcl_frac))
  marker_table <- mutate(marker_table, log2_EV_vs_WCL=log2((.data[[paste0("avg_", ev_frac)]]+1e-10) / (.data[[paste0("avg_", wcl_frac)]]+1e-10)))
if (!is.na(ev_frac) && !is.na(awf_frac))
  marker_table <- mutate(marker_table, log2_EV_vs_WCL=log2((.data[[paste0("avg_", ev_frac)]]+1e-10) / (.data[[paste0("avg_", awf_frac)]]+1e-10)))

# Generate heatmap of log-dNSAF across fractions for marker proteins
avg_cols <- intersect(paste0("avg_", fractions), colnames(marker_table))
heatmap_mat <- marker_table %>%
  select(proteinAnnotation, all_of(avg_cols)) %>%
  column_to_rownames("proteinAnnotation") %>%
  as.matrix() %>%
  logdNSAF()
colnames(heatmap_mat) <- str_remove(colnames(heatmap_mat), "avg_")
ann_row <- data.frame(Category=marker_table$MISEVCategory, row.names=marker_table$proteinAnnotation)
svglite(file.path(output_dir, "marker_heatmap.svg"),
        width=12, height=max(6, nrow(heatmap_mat) * 0.35))
pheatmap(heatmap_mat, annotation_row=ann_row,
         color=colorRampPalette(c("#88CCEE","white","#CC6677"))(50),
         main="MISEV2023 markers — log(dNSAF) across fractions",
         fontsize_row=8, fontsize_col=10, border_color=NA)
dev.off()

# Export .xlsx spreadsheet
wb <- wb_workbook()
wb$add_worksheet("EV_Markers"); wb$add_data("EV_Markers", marker_table)
wb_save(wb, file.path(output_dir, "ev_markers.xlsx"))
message("EV markers section complete")