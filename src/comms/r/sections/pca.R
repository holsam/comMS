#!/bin/R
# pca.R: principal component analysis and clustering section

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
source(file.path(script_dir, "..", "utils", "theme.R"))

# Load libraries
library(cluster)
library(ggfortify)
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

# Matrix for PCA
pca_mat <- results_wide %>%
  select(proteinId, all_of(dnsaf_cols)) %>%
  column_to_rownames("proteinId") %>%
  rename_with(~str_remove(., "dNSAF_")) %>%
  t()

# Calculate number of clusters
k <- max(2, min(length(unique(sample_meta$fraction)), nrow(pca_mat) - 1))
pca_data <- clara(pca_mat, k=k, metric="euclidean", stand=FALSE, samples=500, sampsize=nrow(pca_mat), pamLike=TRUE, correct.d=TRUE)

# Generate PCA plot
pca_plot <- autoplot(pca_data, frame=TRUE, frame.type='t', size=5) +
  theme_comms() +
  geom_text_repel(label=rownames(pca_mat), size=4, box.padding=0.5, point.padding=0.75, direction="both", force=15, max.overlaps=Inf) +
  scale_color_manual(values=COMMS_COLOURS) +
  scale_fill_manual(values=COMMS_COLOURS) +
  labs(colour="Cluster", fill="Cluster")
svglite(file.path(output_dir, "pca.svg"), width=10, height=8)
print(pca_plot); dev.off()

# Generate distance matrix and plot dendrogram
dist_mat <- dist(scale(pca_mat), method="euclidean")
hc <- hclust(dist_mat, method="average")
svglite(file.path(output_dir, "dendrogram.svg"), width=10, height=6)
plot(hc, main="Sample clustering (Euclidean, average linkage)",
     xlab="", sub="", ylab="Distance", cex=0.9)
dev.off()
message("PCA section complete")