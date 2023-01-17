import numpy as np

def angle(a: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a, axis = 1).reshape((len(a), 1))
    return np.arctan2(np.clip(a[:, 1], -1, 1), np.clip(a[:, 0], -1, 1)) # type:ignore

def angle_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a, axis = 1).reshape((len(a), 1))
    b = b / np.linalg.norm(b, axis = 1).reshape((len(b), 1))
    x = np.clip((a * b).sum(axis = 1), -1, 1)
    y = np.clip(np.cross(a, b), -1, 1)
    return np.arctan2(y, x) # type:ignore