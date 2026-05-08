#!/bin/R
# limma_da.R — differential abundance using limma empirical Bayes

library(limma)
library(tidyverse)

# runLimmaDA: fits a limma model to a log-dNSAF matrix for a single fraction and returns a tidy tibble of results for the treatment contrast
runLimmaDA <- function(logMat, treatment) {
  design <- model.matrix(~0 + factor(treatment))
  treat_levels <- make.names(levels(factor(treatment)))
  colnames(design) <- treat_levels
  contrast_matrix <- makeContrasts(
    contrasts = paste(treat_levels[2], "-", treat_levels[1]),
    levels = design
  )
  fit <- lmFit(logMat, design)
  fit2 <- contrasts.fit(fit, contrast_matrix)
  fit2 <- eBayes(fit2)
  topTable(fit2, n=Inf, adjust.method="BH") %>%
    as_tibble(rownames="proteinId") %>%
    rename(log2FC=logFC, pval=P.Value, adj_pval=adj.P.Val)
}

# classifyDA: adds an Abundance column using lfc and fdr thresholds
classifyDA <- function(daResults, lfcThreshold, fdrThreshold) {
  daResults %>%
    mutate(Abundance = case_when(
      adj_pval < fdrThreshold & log2FC > lfcThreshold ~ "Increased",
      adj_pval < fdrThreshold & log2FC < -lfcThreshold ~ "Decreased",
      TRUE ~ "Unchanged"
    ))
}