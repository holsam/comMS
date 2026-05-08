#!/bin/R
# normalise.R: normalisation utilities

# logNSAF: applies log(x + epsilon) transform to a numeric matrix or tibble column; epsilon defaults to half the minimum non-zero value across the input
logNSAF <- function(x, epsilon=NULL) {
  if (is.null(epsilon)) {
    nonzero <- x[x > 0 & !is.na(x)]
    epsilon <- if (length(nonzero) > 0) min(nonzero) / 2 else 1e-10
  }
  log(x + epsilon)
}

# medianShiftNormalise: applies within-fraction median-shift normalisation to a wide NSAF tibble
medianShiftNormalise <- function(nsafWide, sampleMetadata) {
  fractions <- unique(sampleMetadata$fraction)
  for (frac in fractions) {
    frac_cols <- sampleMetadata %>%
      filter(fraction == frac) %>%
      pull(nsaf_col)
    frac_cols <- intersect(frac_cols, colnames(nsafWide))
    if (length(frac_cols) < 2) next
    global_median <- median(unlist(nsafWide[, frac_cols]), na.rm=TRUE)
    for (col in frac_cols) {
      col_median <- median(nsafWide[[col]], na.rm=TRUE)
      nsafWide[[col]] <- nsafWide[[col]] - col_median + global_median
    }
  }
  return(nsafWide)
}