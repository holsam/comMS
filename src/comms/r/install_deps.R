#!/bin/R
# install_deps.R: install all required R dependencies for comms report command

cran_packages <- c("tidyverse", "openxlsx2", "svglite", "ggrepel", "ggfortify", "cluster", "UpSetR", "pheatmap", "VennDiagram")
bioc_packages <- c("limma")

install.packages(cran_packages, repos = "https://cloud.r-project.org")
if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
BiocManager::install(bioc_packages)