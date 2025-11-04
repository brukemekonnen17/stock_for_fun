import numpy as np
from dataclasses import dataclass

@dataclass
class Arm:
    name: str  # "EARNINGS_PRE" | "POST_EVENT_MOMO" | "NEWS_SPIKE" | "REACTIVE" | "SKIP"

class ContextualTS:
    """
    Simple linear contextual Thompson Sampling.
    Model: r = x^T theta + noise
    """
    def __init__(self, d: int, arms: list[Arm], alpha: float = 1.0):
        self.d = d
        self.arms = arms
        self.alpha = alpha
        self.A = {a.name: np.eye(d) for a in arms}      # precision matrices
        self.b = {a.name: np.zeros((d, 1)) for a in arms}

    def select(self, x: np.ndarray) -> str:
        x = x.reshape(-1, 1)
        samples = {}
        for a in self.arms:
            A_inv = np.linalg.inv(self.A[a.name])
            theta = A_inv @ self.b[a.name]
            cov = self.alpha**2 * A_inv
            w = np.random.multivariate_normal(theta.flatten(), cov)
            samples[a.name] = float(w @ x.flatten())
        return max(samples, key=samples.get)

    def update(self, arm_name: str, x: np.ndarray, r: float):
        x = x.reshape(-1, 1)
        self.A[arm_name] += x @ x.T
        self.b[arm_name] += r * x

