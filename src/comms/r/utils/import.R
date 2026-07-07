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
  file_scs <- read_tsv(spectralCountsFilePath, show_col_types=FALSE) %>%
    rename(proteinId="protein id")
  if (nrow(file_scs) == 0) return(NULL)
  raw_path <- str_replace(spectralCountsFilePath, "_[^./!_]+\\.spectral-counts", "_RAW.spectral-counts")
  if (file.exists(raw_path)) {
    raw <- read_tsv(raw_path, show_col_types=FALSE) %>%
      rename(proteinId="protein id")
    file_scs <- left_join(file_scs, raw, by="proteinId")
  } else {
    file_scs <- file_scs %>% mutate(`RAW`=NA_integer_)
  }
  file_scs %>%
    filter(!proteinId %in% contInfo$proteinId) %>%
    left_join(refInfo, by = "proteinId")
}

# importSpectralCountFiles: loads all spectral-counts files in a directory and
# returns a named list of tibbles, one per sample. Names are derived from the
# file stem (i.e. the original sample name used as --fileroot in comms quantify).
importSpectralCountFiles <- function(quantifyDir, refInfo, contInfo) {
  files <- list.files(path=quantifyDir, pattern="spectral-counts\\.target\\.txt$", full.names=TRUE) %>%
    keep(\(x) !str_detect(x, pattern="_RAW\\.spectral-counts"))
  if (length(files) == 0) stop("No spectral-counts files found in: ", quantifyDir)
  results <- lapply(files, loadSpectralCounts, refInfo, contInfo)
  names(results) <- word(
    str_remove_all(files, "_[^./!_]+\\.spectral-counts\\.target\\.txt"),
    start=-1, sep=fixed("/")
  )
  return(compact(results))
}

# mergedNSAF: reduces a named list of per-sample tibbles to a single wide tibblewith one dNSAF column per sample (missing proteins are filled with 0)
mergeResults <- function(resultsList) {
  merged <- resultsList %>%
    map(select, proteinId, proteinAnnotation, dNSAF, `RAW`) %>%
    imap(function(x, y) x %>%
           rename_with(~paste(., y, sep='_'), -c(proteinId, proteinAnnotation))) %>%
    reduce(full_join, by=join_by(proteinId, proteinAnnotation))
  value_cols <- setdiff(colnames(merged), c("proteinId", "proteinAnnotation"))
  merged <- merged %>% mutate(across(all_of(value_cols), ~replace_na(., 0)))
  return(merged)
}

# buildSampleMetadata: joins sample sheet to dNSAF column stems
buildSampleMetadata <- function(dnsafColStems, sampleSheet) {
  tibble(full_stem=dnsafColStems) %>%
    mutate(
      sample_id = str_extract(full_stem, "^[^.]+"),
      organism = str_extract(full_stem, "(?<=\\.)[^_]+"),
      dnsaf_col = paste0("dNSAF_", full_stem)
    ) %>%
    inner_join(sampleSheet, by="sample_id")
}

# loadLfqFiles: reads all crux-lfq-mod-pep.txt files, applies MaxLFQ protein-level
# quantification via iq::preprocess + iq::create_protein_table, and returns a single
# tibble with a Fraction column.
# Implements Cox et al. 2014 (doi:10.1074/mcp.M113.031591) via Pham et al. 2020
# (doi:10.1093/bioinformatics/btz961).
loadLfqFiles <- function(lfqDir) {
  lfq_files <- list.files(lfqDir, pattern="\\.crux-lfq-mod-pep\\.txt$", full.names=TRUE, recursive=TRUE)
  if (length(lfq_files) == 0) stop("No crux-lfq-mod-pep.txt files found under: ", lfqDir)
  bind_rows(lapply(lfq_files, function(f) {
    dat <- read_tsv(f, show_col_types=FALSE) %>%
      rename(proteinId=`Protein ID`, peptideSeq=`Unmodified Sequence`)
    intensity_cols <- colnames(dat)[str_starts(colnames(dat), "Intensity_")]
    long <- dat %>%
      select(proteinId, peptideSeq, all_of(intensity_cols)) %>%
      pivot_longer(
        cols = all_of(intensity_cols),
        names_to = "sample_id",
        values_to = "intensity"
      ) %>%
      mutate(
        sample_id = str_extract(sample_id, "[^/]+(?=\\.mzML)"),
        intensity = na_if(intensity, 0)
      ) %>%
      filter(!is.na(intensity))
    if (nrow(long) == 0) {
      message(sprintf("loadLfqFiles: no non-zero intensities in %s — skipping", basename(f)))
      return(NULL)
    }
    tmp_in  <- tempfile(fileext=".txt")
    tmp_out <- tempfile(fileext=".txt")
    on.exit(unlink(c(tmp_in, tmp_out)), add=TRUE)
    write_tsv(long, tmp_in)
    result <- iq::process_long_format(
      tmp_in,
      output_filename = tmp_out,
      primary_id = "proteinId",
      sample_id = "sample_id",
      secondary_id = "peptideSeq",
      intensity_col = "intensity",
      filter_double_less = NULL
    )
    # process_long_format behaviour varies by iq version: may return the result directly or write to output_filename and return NULL
    if (is.null(result)) {
      if (!file.exists(tmp_out)) {
        stop(sprintf("iq::process_long_format produced no output for %s", basename(f)))
      }
      result <- read_tsv(tmp_out, show_col_types = FALSE)
    }
    result %>%
      rename(proteinId = 1) %>%
      mutate(Fraction = basename(dirname(f)))
}))}