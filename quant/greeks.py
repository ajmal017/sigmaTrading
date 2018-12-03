"""
Code for calculation of more and less esoteric greeks
"""

"""
#' Title
#'
#' @param S 
#' @param K 
#' @param r 
#' @param q 
#' @param sigma 
#' @param t 
#'
#' @return
#' @export
#'
#' @examples
d1 <- function(S, K, r, q, sigma, t) {
  v <- (log(S / K) + (r - q + sigma * sigma / 2) * t) / (sigma * sqrt(t))
  
  return(v)
}

#' Title
#'
#' @param S 
#' @param K 
#' @param r 
#' @param q 
#' @param sigma 
#' @param t 
#'
#' @return
#' @export
#'
#' @examples
d2 <- function(S, K, r, q, sigma, t) {
  v <- d1(S, K, r, q, sigma, t) - sigma * sqrt(t)
  return(v)
}

#' Title
#'
#' @param x 
#'
#' @return
#' @export
#'
#' @examples
phi <- function(x) {
  # \phi(x) = \frac{e^{- \frac{x^2}{2}}}{\sqrt{2 \pi}} 
  v <- exp(-(x*x)/2) / sqrt(2 * pi)
  return(v)
}

#' Title
#'
#' @param gamma 
#' @param s 
#' @param d1 
#' @param sigma 
#' @param t 
#'
#' @return
#' @export
#'
#' @examples
speed <- function(gamma, s, d1, sigma, t) {
  # -\frac{\Gamma}{S}\left(\frac{d_1}{\sigma\sqrt{\tau}}+1\right) 
  return(-(gamma / s) * ((d1 / (sigma * sqrt(t))) + 1))
  
}

# d value / d sigma
#' Title
#'
#' @param S 
#' @param K 
#' @param r 
#' @param q 
#' @param sigma 
#' @param t 
#'
#' @return
#' @export
#'
#' @examples
vega <- function(S, K, r, q, sigma, t) {
  #  S e^{-q \tau} \phi(d_1) \sqrt{\tau} = K e^{-r \tau} \phi(d_2) \sqrt{\tau} \, 
  v <- K * exp(-r * t) * phi(d2(S, K, r, q, sigma, t)) * sqrt(t)
  return(v)
}

# d delta / d sigma
#' Title
#'
#' @param vega 
#' @param s 
#' @param d1 
#' @param sigma 
#' @param t 
#'
#' @return
#' @export
#'
#' @examples
vanna <- function(vega, s, d1, sigma, t) {
  # {\frac {\mathcal {V}}{S}}\left[1-{\frac {d_{1}}{\sigma {\sqrt {\tau }}}}\right]\,}
  v <- vega / s * (1 - d1 / (sigma * sqrt(t)))
  return(v)
}

# d gamma / d sigma
#' Title
#'
#' @param gamma 
#' @param d2 
#' @param d1 
#' @param sigma 
#'
#' @return
#' @export
#'
#' @examples
zomma <- function(gamma, d2, d1, sigma) {
  # \Gamma\cdot\left(\frac{d_1 d_2 -1}{\sigma}\right) \,
  v <- gamma * (d2 * d1 - 1) / sigma 
  return(v)
}

#' Calculates charm (chane of delta over time)
#' that is: d delta / d time
#'
#' @param d1 
#' @param d2 
#' @param q 
#' @param sigma 
#' @param t 
#' @param side 
#' @param r 
#'
#' @return
#' @export
#'
#' @examples
charm <- function(side, d1, d2, r, q, sigma, t) {
  
  v1 <- exp(-q * t) * phi(d1) * (2 * (r - q) * t - d2 * sigma * sqrt(t)) / (2 * t * sigma * sqrt(t))
  
  v <- ifelse(side == "c", q * exp(-q * t) * pnorm(d1) -  v1,
    -q * exp(-q * t) * pnorm(-d1) - v1)
  return(v)
}"""

def speed():
    return 0


def vanna():
    return 0


def zomma():
    return 0
