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

# Define COMMS_COLOURS constant: colour palette based on Tol, P. (2021). Colour Schemes. SRON Technical Note SRON/EPS/TN/09-002, issue 3.2. https://sronpersonalpages.nl/~pault/
COMMS_COLOURS <- c(
  "#CC6677", # rose
  "#88CCEE", # cyan
  "#DDCC77", # sand
  "#117733", # green
  "#332288", # indigo
  "#AA4499", # purple
  "#44AA99", # teal
  "#999933", # olive
  "#882255", # wine
  "#DDDDDD"  # pale grey
)