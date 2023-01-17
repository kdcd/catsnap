import numpy as np
import pandas as pd
from typing import Any
import mplfinance as mpf

def addplot(a: np.ndarray, **kwargs: Any):
    if pd.isnull(a).all():
        a[0] = 0
        return mpf.make_addplot(a, **kwargs) # type:ignore
    return mpf.make_addplot(a, **kwargs) # type:ignore