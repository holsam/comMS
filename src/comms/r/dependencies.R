#!/bin/R
# dependencies.R: list of all R packages required by comms report command

R_DEPENDENCIES <- list(
    cran = c("tidyverse", "openxlsx2", "svglite", "ggrepel", "ggfortify", "cluster", "UpSetR", "pheatmap", "VennDiagram", "iq"),
    bioc = c("limma")
)