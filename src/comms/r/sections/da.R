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
top_n <- as.integer(args[10])

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
source(file.path(script_dir, "..", "utils", "status.R"))
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

organisms <- unique(sample_meta$organism)
treatments <- sort(unique(sample_meta$treatment))
if (length(treatments) != 2) stop("DA section requires exactly two treatment levels.")

# Initialise list for differentially abundant results
da_results_all <- list()

status <- new_status_tracker("da")

for (org in organisms) {
  org_meta <- filter(sample_meta, organism == org)
  fractions <- unique(org_meta$fraction)

  for (frac in fractions) {
    tryCatch({
      frac_meta <- filter(org_meta, fraction == frac)
      frac_cols <- frac_meta$dnsaf_col

      frac_data <- results_wide %>%
        select(proteinId, proteinAnnotation, all_of(frac_cols)) %>%
        filter(rowSums(select(., all_of(frac_cols)) > 0) > 0)

      for (trt in treatments) {
        trt_cols <- filter(frac_meta, treatment == trt)$dnsaf_col
        frac_data[[paste0("n_", trt)]] <- rowSums(select(frac_data, all_of(trt_cols)) > 0)
      }
      frac_data <- filter(frac_data, if_any(starts_with("n_"), ~. >= min_reps))

      if (nrow(frac_data) < 5) {
        reason <- sprintf("too few proteins after replicate filter (%d) in fraction %s", nrow(frac_data), frac)
        message(sprintf("DA %s %s: %s — skipping", org, frac, reason))
        status <<- record_skip(status, org, reason)
        next
      }

      log_mat <- frac_data %>%
        select(proteinId, all_of(frac_cols)) %>%
        column_to_rownames("proteinId") %>%
        as.matrix() %>%
        logdNSAF()
      treatment_vec <- frac_meta %>%
        arrange(match(dnsaf_col, frac_cols)) %>%
        pull(treatment)

      if (length(unique(treatment_vec)) < 2) {
        reason <- sprintf("fewer than 2 treatment levels in fraction %s", frac)
        message(sprintf("DA %s %s: %s — skipping", org, frac, reason))
        status <<- record_skip(status, org, reason)
        next
      }

      da_res <- runLimmaDA(log_mat, treatment_vec) %>%
        classifyDA(lfc_threshold, fdr_threshold) %>%
        left_join(select(frac_data, proteinId, proteinAnnotation), by = "proteinId")

      key <- paste(org, frac, sep = "_")
      da_results_all[[key]] <- da_res

      top_labels <- filter(da_res, Abundance != "Unchanged") %>% 
        slice_min(adj_pval, n=top_n)
      volcano <- ggplot(da_res, aes(x=log2FC, y=-log10(adj_pval), colour=Abundance)) +
        geom_point(alpha=0.7, size=1.5) +
        geom_hline(yintercept=-log10(fdr_threshold), linetype="dashed", colour="grey50") +
        geom_vline(xintercept=c(-lfc_threshold, lfc_threshold), linetype="dashed", colour="grey50") +
        geom_text_repel(data=top_labels, aes(label=proteinAnnotation), size=3, max.overlaps=15) +
        scale_colour_manual(values=c("Increased"="#CC6677", "Decreased"="#88CCEE", "Unchanged"="grey70")) +
        theme_comms() +
        labs(title=sprintf("DA — %s %s (%s vs %s)", org, frac, treatments[2], treatments[1]), x=expression(log[2](FC)), y=expression(-log[10](adj.p)))
      svglite(file.path(output_dir, sprintf("volcano_%s_%s.svg", frac, org)), width=10, height=7)
      print(volcano); dev.off()

      status <<- record_ok(status, org)
    }, error = function(e) {
      while (dev.cur() != 1) dev.off()
      message(sprintf("DA %s %s: error — %s", org, frac, conditionMessage(e)))
      status <<- record_fail(status, org, conditionMessage(e))
    })
  }
}

write_status(status, output_dir)

# Venn diagrams per organism
for (org in organisms) {
  org_results <- da_results_all[str_starts(names(da_results_all), org)]
  da_up_sets <- lapply(org_results, function(x) filter(x, Abundance == "Increased")$proteinId)
  da_down_sets <- lapply(org_results, function(x) filter(x, Abundance == "Decreased")$proteinId)
  names(da_up_sets) <- names(da_down_sets) <- str_remove(names(org_results), paste0(org, "_"))
  if (length(da_up_sets) >= 2) {
    venn_up <- venn.diagram(da_up_sets, filename=NULL, disable.logging=TRUE, category.names=names(da_up_sets))
    ggsave(file.path(output_dir, sprintf("venn_da_up_%s.svg", org)), venn_up)
    venn_down <- venn.diagram(da_down_sets, filename=NULL, disable.logging=TRUE, category.names=names(da_down_sets))
    ggsave(file.path(output_dir, sprintf("venn_da_down_%s.svg", org)), venn_down)
  }
}

# Export .xlsx spreadsheet
wb <- wb_workbook()
for (key in names(da_results_all)) {
  sn <- substr(key, 1, 31)
  wb$add_worksheet(sn); wb$add_data(sn, da_results_all[[key]])
}
wb_save(wb, file.path(output_dir, "da_results.xlsx"))
message("DA section complete")