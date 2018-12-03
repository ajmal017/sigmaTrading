"""
# Scales values to -1 .. 1 scale
scale11 <- function(x) {
  (2 * ((x - min(x))/(max(x) - min(x)))) - 1
}

# Scales back to the original scale
revscale11 <- function(y, min.x, max.x) {
  min.x + ((y + 1) * (max.x - min.x)) / 2
}
"""