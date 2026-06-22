#!/bin/R
# import.R: data import and NSAF calculation utilities

library(tidyverse)
library(openxlsx2)

# loadRefInfo: returns tibble from a reference protein info TSV
loadRefInfo <- function(refInfoPath) {
  read_tsv(refInfoPath, show_col_types=FALSE) %>%
    rename(
      proteinId = protein.id,
      proteinAnnotation = protein.annotation,
      proteinLength = protein.length
    )
}

# loadContInfo: returns tibble from a contaminant annotations CSV
loadContInfo <- function(contCsvPath) {
  read_csv(contCsvPath, show_col_types=FALSE) %>%
    rename(proteinId=protein.id)
}

# loadSampleSheet: returns tibble from a sample sheet TSV/CSV
loadSampleSheet <- function(sampleSheetPath) {
  sep <- if (str_ends(sampleSheetPath, fixed(".tsv")) || str_ends(sampleSheetPath, fixed(".txt"))) "\t" else ","
  read_delim(sampleSheetPath, delim=sep, show_col_types=FALSE) %>%
    rename_with(str_to_lower)
}

# loadSpectralCounts: reads a single spectral-counts file, removes contaminant proteins, and joins reference annotations
loadSpectralCounts <- function(spectralCountsFilePath, refInfo, contInfo) {
  read_tsv(file=spectralCountsFilePath, show_col_types=FALSE) %>%
    rename(proteinId="protein id") %>%
    filter(!proteinId %in% contInfo$proteinId) %>%
    left_join(refInfo, by="proteinId")
}

# importSpectralCountFiles: loads all spectral-counts files in a directory and
# returns a named list of tibbles, one per sample. Names are derived from the
# file stem (i.e. the original sample name used as --fileroot in comms quantify).
importSpectralCountFiles <- function(quantifyDir, refInfo, contInfo) {
  files <- list.files(path=quantifyDir, pattern='spectral-counts\\.target', full.names=TRUE)
  if (length(files) == 0) stop("No spectral-counts files found in: ", quantifyDir)
  results <- lapply(files, loadSpectralCounts, refInfo, contInfo)
  names(results) <- word(
    str_remove_all(files, "\\.spectral-counts\\.target\\.txt"),
    start=-1, sep=fixed("/")
  )
  return(results)
}

# mergedNSAF: reduces a named list of per-sample tibbles to a single wide tibblewith one dNSAF column per sample (missing proteins are filled with 0)
mergeResults <- function(resultsList) {
  merged <- resultsList %>%
    map(select, proteinId, proteinAnnotation, dNSAF) %>%
    imap(function(x, y) x %>%
      rename_with(~paste(., y, sep='_'), -c(proteinId, proteinAnnotation))) %>%
     reduce(full_join, by=join_by(proteinId, proteinAnnotation))
  dnsaf_cols <- setdiff(colnames(merged), c("proteinId", "proteinAnnotation"))
  merged <- merged %>% mutate(across(all_of(dnsaf_cols), ~replace_na(., 0)))
  return(merged)
}

# buildSampleMetadata: joins sample sheet to dNSAF column stems
buildSampleMetadata <- function(dnsafColStems, sampleSheet) {
  sampleSheet %>%
    mutate(stem=sample_id) %>%
    filter(stem %in% dnsafColStems) %>%
    mutate(dnsaf_col=paste0("dNSAF_", stem))
}