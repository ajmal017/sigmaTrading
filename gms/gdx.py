"""
#' Turns a list of variable values returned from GDX into a data framel
#'
#' @param x List in rgdx format
#'
#' @return R data frame
#' @export
#'
#' @examples
gdxAsDf <- function(x) {
  # Reshape
  # Rename lines and columns
  # return data frame

  x$data <- data.frame(x$val)
  for (i in seq(1, length(x$uels))) {
    x$data[,i] <- x$uels[[i]][x$data[,i]]
  }

  names(x$data) <- c(x$domains, "val")

  return(x$data)
}
"""