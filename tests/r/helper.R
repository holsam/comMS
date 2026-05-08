# Locate the repo root by walking up from the working directory until pyproject.toml is found. This is robust to being invoked from any directory.
.find_repo_root <- function() {
  path <- normalizePath(getwd())
  while (TRUE) {
    if (file.exists(file.path(path, "pyproject.toml"))) return(path)
    parent <- dirname(path)
    if (parent == path) stop("Could not locate repo root (pyproject.toml not found)")
    path <- parent
  }
}

REPO_ROOT <- .find_repo_root()