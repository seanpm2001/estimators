from scipy.stats import beta  # type: ignore
from typing import List, Tuple


class IncrementalFsum:
    """Incremental version of https://en.wikipedia.org/wiki/Kahan_summation_algorithm"""

    def __init__(self) -> None:
        self.partials: List[float] = []

    def __iadd__(self, x: float) -> "IncrementalFsum":
        i = 0
        for y in self.partials:
            if abs(x) < abs(y):
                x, y = y, x
            hi = x + y
            lo = y - (hi - x)
            if lo:
                self.partials[i] = lo
                i += 1
            x = hi
        self.partials[i:] = [x]
        return self

    @staticmethod
    def merge(*args: "IncrementalFsum") -> "IncrementalFsum":
        result = IncrementalFsum()
        for x in args:
            for y in x.partials:
                result += y
        return result

    def __float__(self) -> float:
        return sum(self.partials, 0.0)


def clopper_pearson(
    successes: float, n: float, alpha: float = 0.05
) -> Tuple[float, float]:
    lower_bound = (
        beta.ppf(alpha / 2, successes, n - successes + 1) if successes > 0 else 0
    )
    upper_bound = (
        beta.ppf(1 - alpha / 2, successes + 1, n - successes) if successes < n else 1
    )
    return (lower_bound, upper_bound)
