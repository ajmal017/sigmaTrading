"""
#' Transforms a scalar into GDX importable list.
#'
#' @param l Scalar value
#' @param l.n Scalar name for GDX
#' @param l.d Scalar description for GDX
#'
#' @return List in wgdx format
#' @export none
#'
#' @examples
createScalar <- function(l, l.n, l.d) {
  return(list(name = l.n, ts = l.d, type = "parameter", dim = 0, form = "full", val = l))
}
"""