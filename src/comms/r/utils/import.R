#!/bin/R
# import.R: data import and NSAF calculation utilities

library(tidyverse)
library(openxlsx2)

# loadRefInfo: returns tibble from a reference protein info TSV
loadRefInfo <- function(refInfoPath) {
  if (is.null(refInfoPath) || refInfoPath == '') return(NULL)
  read_tsv(refInfoPath, show_col_types=FALSE) %>%
    rename(
      ProteinId = protein.id,
      ProteinAnnotation = protein.annotation,
      ProteinLength = protein.length
    )
}

# loadContInfo: returns tibble from a contaminant annotations CSV
loadContInfo <- function(contCsvPath) {
  if (is.null(contCsvPath) || contsCsvPath == '') return(tibble(ProteinId=character()))
  read_csv(contCsvPath, show_col_types=FALSE) %>%
    rename(ProteinId=protein.id)
}

# loadSampleSheet: returns tibble from a sample sheet TSV/CSV
loadSampleSheet <- function(sampleSheetPath) {
  sep <- if (str_ends(sampleSheetPath, fixed(".tsv")) || str_ends(sampleSheetPath, fixed(".txt"))) "\t" else ","
  read_delim(sampleSheetPath, delim=sep, show_col_types=FALSE) %>%
    rename_with(str_to_lower)
}

# calculateNSAF: returns tububle of NSAF values from a single spectral-counts file
calculateNSAF <- function(spectralCountsFilePath, refInfo, contInfo) {
  result <- read_tsv(file=spectralCountsFilePath, show_col_types=FALSE) %>%
    filter(! `q-value` > 0.01) %>%
    filter(! ProteinId %in% contInfo$ProteinId) %>%
    rowwise() %>%
    filter(length(str_split_1(peptideIds, pattern=fixed(" "))) > 1) %>%
    ungroup()
  if (!is.null(refInfo)) {
    result <- left_join(result, refInfo, by=join_by(ProteinId))
  }
  result %>%
    add_count(ProteinGroupId) %>%
    group_by(ProteinGroupId) %>%
    mutate(GroupedProteins=case_when(
      n == 1 ~ NA,
      n > 1  ~ paste(paste0(ProteinId, " (", ProteinAnnotation, ")"), collapse=", ")
    ), .after=ProteinGroupId) %>%
    filter(row_number() == 1) %>%
    ungroup() %>%
    select(!n) %>%
    mutate(normalised_spec = spec_count_all / ProteinLength) %>%
    mutate(NSAF = normalised_spec / sum(normalised_spec, na.rm=TRUE)) %>%
    select(!normalised_spec)
}

# importSpectralCountFiles: loads all spectral count files in a directory and returns a named list of NSAF tibbles
importSpectralCountFiles <- function(quantifyDir, refInfo, contInfo) {
  files <- list.files(path=quantifyDir, pattern='spectral-counts.target', full.names=TRUE)
  if (length(files) == 0) stop("No spectral-counts files found in: ", quantifyDir)
  nsaf_results <- lapply(files, calculateNSAF, refInfo, contInfo)
  names(nsaf_results) <- word(
    str_remove_all(files, "\\.spectral-counts\\.target\\.txt"),
    start=-1, sep=fixed("/")
  )
  return(nsaf_results)
}

# mergeNSAFResults: reduces a named list of per-sample NSAF tibbles to a single wide tibble with one NSAF column per sample (missing proteins = 0)
mergeNSAFResults <- function(nsafList) {
  merged <- nsafList %>%
    map(select, ProteinId, ProteinAnnotation, NSAF) %>%
    imap(function(x, y) x %>%
      rename_with(~paste(., y, sep='_'), -c(ProteinId, ProteinAnnotation))) %>%
    reduce(full_join, by=join_by(ProteinId, ProteinAnnotation))
  merged[is.na(merged)] <- 0
  return(merged)
}

# buildSampleMetadata: joins sample sheet to NSAF column stems and returns tibble linking nsaf_col to fraction, treatment, replicate
buildSampleMetadata <- function(nsafColStems, sampleSheet) {
  sampleSheet %>%
    mutate(stem = tools::file_path_sans_ext(basename(raw_file))) %>%
    filter(stem %in% nsafColStems) %>%
    mutate(nsaf_col = paste0("NSAF_", stem))
}