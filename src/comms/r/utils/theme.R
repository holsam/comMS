#!/bin/R
# theme.R: shared ggplot2 theme

library(ggplot2)

# theme_comms: define basic ggplot2 function
theme_comms <- function() {
  theme_bw() +
    theme(
      axis.title = element_text(size=14),
      axis.text = element_text(size=12),
      legend.title = element_text(size=14),
      legend.text = element_text(size=12),
      plot.title = element_text(size=16)
    )
}

# Define COMMS_COLOURS constant: colour palette
COMMS_COLOURS <- c("#CC6677", "#88CCEE", "#DDCC77", "#117733", "#332288", "#AA4499")