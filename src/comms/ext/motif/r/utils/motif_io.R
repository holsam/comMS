#!/bin/R
# motif_io.R: minimal-MEME parsing and IO helpers for comMS motif extension

# read_meme_minimal: returns a list of motifs parsed from a minimal-MEME file
read_meme_minimal <- function(path) {
  lines <- readLines(path, warn = FALSE)
  alpha_line <- grep("^ALPHABET", lines, value = TRUE)[1]
  alphabet <- strsplit(gsub("ALPHABET=?\\s*", "", alpha_line), "")[[1]]
  alphabet <- alphabet[grepl("[A-Za-z]", alphabet)]
  motif_starts <- grep("^MOTIF", lines)
  motifs <- list()
  for (start in motif_starts) {
    header <- strsplit(trimws(lines[start]), "\\s+")[[1]]
    motif_id <- header[2]
    lp <- start + which(grepl("letter-probability matrix", lines[(start + 1):length(lines)]))[1]
    w <- as.integer(sub(".*w=\\s*(\\d+).*", "\\1", lines[lp]))
    evalue <- sub(".*E=\\s*(\\S+).*", "\\1", lines[lp])
    nsites <- suppressWarnings(as.integer(sub(".*nsites=\\s*(\\d+).*", "\\1", lines[lp])))
    rows <- lines[(lp + 1):(lp + w)]
    mat <- t(sapply(rows, function(l) as.numeric(strsplit(trimws(l), "\\s+")[[1]])))
    colnames(mat) <- alphabet
    rownames(mat) <- NULL
    motifs[[motif_id]] <- list(
      id = motif_id, width = w, evalue = evalue,
      nsites = ifelse(is.na(nsites), NA_integer_, nsites),
      ppm = mat
    )
  }
  return(motifs)
}

# read_sites_tsv: returns a data.frame from a TSV file (empty if file doesn't exist)
read_sites_tsv <- function(path) {
  if (!file.exists(path)) return(data.frame())
  return(read.delim(path, stringsAsFactors = FALSE))
}