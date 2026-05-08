# Import libraries
library(testthat)

# Import utility functions
source(file.path(REPO_ROOT, "src", "comms", "r", "utils", "normalise.R"))

# Define unit tests
test_that("logdNSAF returns no -Inf values when epsilon is applied", {
  mat <- matrix(c(0, 0.1, 0, 0.2), nrow=2)
  expect_false(any(is.infinite(logdNSAF(mat))))
})

test_that("logNSAF transforms non-zero values correctly", {
  mat <- matrix(c(0.5, 0.5), nrow=2)
  result <- logdNSAF(mat, epsilon=0)
  expect_equal(result[1,1], log(0.5), tolerance=1e-10)
})

test_that("logNSAF accepts custom epsilon", {
  mat <- matrix(c(0, 1), nrow=2)
  result <- logdNSAF(mat, epsilon=0.01)
  expect_equal(result[1,1], log(0.01), tolerance=1e-10)
})

test_that("medianShiftNormalise leaves single-sample fractions unchanged", {
  mat <- tibble(ProteinId="P1", dNSAF_s1=0.5)
  meta <- tibble(fraction="EV", dnsaf_col="NSAF_s1")
  result <- medianShiftNormalise(mat, meta)
  expect_equal(result$dNSAF_s1, 0.5)
})

test_that("medianShiftNormalise aligns within-fraction medians", {
  mat <- tibble(ProteinId=c("P1","P2"), dNSAF_s1=c(2.0,4.0), dNSAF_s2=c(3.0,5.0))
  meta <- tibble(fraction=c("PUR","PUR"), dnsaf_col=c("dNSAF_s1","dNSAF_s2"))
  result <- medianShiftNormalise(mat, meta)
  expect_equal(median(result$dNSAF_s1), median(result$dNSAF_s2), tolerance=1e-10)
})

test_that("medianShiftNormalise does not modify cross-fraction values", {
  mat <- tibble(ProteinId="P1", dNSAF_pur=1.0, dNSAF_wcl=2.0)
  meta <- tibble(fraction=c("PUR","WCL"), dnsaf_col=c("dNSAF_pur","dNSAF_wcl"))
  result <- medianShiftNormalise(mat, meta)
  # Single-sample fractions are not adjusted; values should be unchanged
  expect_equal(result$dNSAF_pur, 1.0)
  expect_equal(result$dNSAF_wcl, 2.0)
})