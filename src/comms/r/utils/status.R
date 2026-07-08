#!/bin/R
# status.R: per-organism status tracking utilities

library(jsonlite)

# new_status_tracker: initialise an empty tracker for a section
new_status_tracker <- function(section) {
  list(section = section, organisms = list(), reasons = list())
}

# record_ok: mark organism as having produced at least one successful output
record_ok <- function(tracker, organism) {
  current <- tracker$organisms[[organism]]
  if (is.null(current) || current == "skipped") {
    tracker$organisms[[organism]] <- "ok"
  }
  tracker
}

# record_skip: mark organism as skipped for this attempt (insufficient data)
record_skip <- function(tracker, organism, reason) {
  if (is.null(tracker$organisms[[organism]])) {
    tracker$organisms[[organism]] <- "skipped"
  }
  tracker$reasons[[organism]] <- c(tracker$reasons[[organism]], reason)
  tracker
}

# record_fail: mark organism as failed (unhandled error)
record_fail <- function(tracker, organism, reason) {
  tracker$organisms[[organism]] <- "failed"
  tracker$reasons[[organism]] <- c(tracker$reasons[[organism]], reason)
  tracker
}

# write_status: serialise a tracker to <output_dir>/_status.json
write_status <- function(tracker, output_dir) {
  reasons_flat <- lapply(tracker$reasons, function(r) paste(r, collapse = "; "))
  payload <- list(
    section = tracker$section,
    organisms = tracker$organisms,
    reasons = if (length(reasons_flat)) reasons_flat else setNames(list(), character(0))
  )
  writeLines(
    toJSON(payload, auto_unbox = TRUE, pretty = TRUE),
    file.path(output_dir, "_status.json")
  )
}