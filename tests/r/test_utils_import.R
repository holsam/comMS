# Import libraries
library(testthat)
library(tidyverse)

# Import utility functions
source(file.path(REPO_ROOT, "src", "comms", "r", "utils", "import.R"))

# Define shared fixtures
make_ref_info <- function(tmp_dir) {
  path <- file.path(tmp_dir, "ref_info.tsv")
  write_tsv(tibble(
    protein.id = c("Mtrun001", "Mtrun002"),
    protein.annotation = c("Test protein 1", "Test protein 2"),
    protein.length = c(200L, 150L),
    go.cellular.component = c("membrane [GO:0016020]", "nucleus [GO:0005634]"),
    go.molecular.function = c("", ""),
    go.biological.process = c("", ""),
    transmembrane.domains = c(1L, 0L),
    signal.peptide = c(0L, 0L),
    transit.peptide = c(0L, 0L)
  ), path)
  path
}
make_cont_csv <- function(tmp_dir) {
  path <- file.path(tmp_dir, "cont.csv")
  write_csv(tibble(protein.id="CONT001", protein.annotation="Keratin", protein.reason="skin"), path); path
}
make_sc_file <- function(tmp_dir, filename="s1.spectral-counts.target.txt") {
  path <- file.path(tmp_dir, filename)
  write_tsv(tibble(
    proteinId = c("Mtrun001", "Mtrun002", "CONT001"),
    dNSAF = c(0.6, 0.4, 0.1)
  ), path)
  path
}

# Initialise temporary directory
tmp <- tempdir()

# Define unit tests
test_that("loadRefInfo returns tibble with expected columns", {
  result <- loadRefInfo(make_ref_info(tmp))
  expect_s3_class(result, "tbl_df")
  expect_true(all(c("proteinId","proteinAnnotation","proteinLength") %in% colnames(result)))
})

test_that("loadRefInfo raises an error for a non-existent path", {
  expect_error(loadRefInfo(file.path(tmp, "does_not_exist.tsv")))
})

test_that("loadContInfo returns tibble with ProteinId column", {
  result <- loadContInfo(make_cont_csv(tmp))
  expect_true("proteinId" %in% colnames(result))
})

test_that("loadSpectralCounts removes contaminant proteins", {
  result <- loadSpectralCounts(
    make_sc_file(tmp),
    loadRefInfo(make_ref_info(tmp)),
    loadContInfo(make_cont_csv(tmp))
  )
  expect_false("CONT001" %in% result$proteinId)
})

test_that("loadSpectralCounts retains non-contaminant proteins", {
  result <- loadSpectralCounts(
    make_sc_file(tmp),
    loadRefInfo(make_ref_info(tmp)),
    loadContInfo(make_cont_csv(tmp))
  )
  expect_true("Mtrun001" %in% result$proteinId)
})

test_that("loadSpectralCounts attaches annotation columns from ref info", {
  result <- loadSpectralCounts(
    make_sc_file(tmp),
    loadRefInfo(make_ref_info(tmp)),
    loadContInfo(make_cont_csv(tmp))
  )
  expect_true("proteinAnnotation" %in% colnames(result))
})

test_that("loadSpectralCounts retains dNSAF column", {
  result <- loadSpectralCounts(
    make_sc_file(tmp),
    loadRefInfo(make_ref_info(tmp)),
    loadContInfo(make_cont_csv(tmp))
  )
  expect_true("dNSAF" %in% colnames(result))
})

test_that("mergeResults produces a wide tibble with one dNSAF column per sample", {
  ref  <- loadRefInfo(make_ref_info(tmp))
  cont <- loadContInfo(make_cont_csv(tmp))
  s1 <- make_sc_file(tmp, "s1.spectral-counts.target.txt")
  s2 <- make_sc_file(tmp, "s2.spectral-counts.target.txt")
  result <- mergeResults(list(
    s1=loadSpectralCounts(s1, ref, cont),
    s2=loadSpectralCounts(s2, ref, cont)
  ))
  expect_true("dNSAF_s1" %in% colnames(result))
  expect_true("dNSAF_s2" %in% colnames(result))
})

test_that("mergeResults preserves proteinId and proteinAnnotation columns", {
  ref  <- loadRefInfo(make_ref_info(tmp))
  cont <- loadContInfo(make_cont_csv(tmp))
  result <- mergeResults(list(
    s1=loadSpectralCounts(make_sc_file(tmp, "s1.spectral-counts.target.txt"), ref, cont)
  ))
  expect_true(all(c("proteinId", "proteinAnnotation") %in% colnames(result)))
})

test_that("mergeResults fills absent proteins with 0 rather than NA", {
  ref <- loadRefInfo(make_ref_info(tmp))
  cont <- loadContInfo(make_cont_csv(tmp))
  s2_path <- file.path(tmp, "s2_partial.spectral-counts.target.txt")
  write_tsv(tibble(
    proteinId = "Mtrun001",
    dNSAF = 1.0
  ), s2_path)
  result <- mergeResults(list(
    s1=loadSpectralCounts(make_sc_file(tmp, "s1.spectral-counts.target.txt"), ref, cont),
    s2=loadSpectralCounts(s2_path, ref, cont)
  ))
  mtrun002_s2 <- result[result$proteinId == "Mtrun002", "dNSAF_s2"][[1]]
  expect_equal(mtrun002_s2, 0)
})