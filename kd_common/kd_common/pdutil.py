from __future__ import annotations

import multiprocessing
from typing import Callable, Iterable, Optional, Union, List, Any, Tuple, cast
import numpy as np
import sys

import pandas as pd

# import rolling_quantiles as rq
from tqdm import tqdm
from functools import partial

from . import funcutil, logutil

import multiprocessing.pool

_logger = logutil.get_logger(__name__)

_OUTPUT_EXCEL = "excel"
_OUTPUT_CONSOLE = "console"


from pandas.core.groupby.generic import SeriesGroupBy as pdSeriesGroupBy

class SeriesGroupBy(pdSeriesGroupBy):
    pass

class Series(pd.Series):
    pass

class DataFrame(pd.DataFrame):
    def __getitem__(self, key: Any) -> DataFrame: # type: ignore
        pass


def _log_mistakes_helper(df: pd.DataFrame, message: str, output: Union[str, Tuple[str, ...]] = _OUTPUT_EXCEL) -> None:
    output = funcutil.to_list(output)  # type: ignore

    if _OUTPUT_CONSOLE in output:
        _logger.warning(f"{message}: {len(df)}\n{df.to_string()}")
    else:
        _logger.warning(f"{message}: {len(df)}")


def merge(left: DataFrame, right: DataFrame, on: Union[List[str], str], **kwargs: Any) -> DataFrame:
    if isinstance(on, str):
        on = [on]
    right = right[right.columns.difference(left.columns) | pd.Index(on)]
    return cast(DataFrame, pd.merge(left, right, on=on, **kwargs))


def select_and_log(df: pd.DataFrame, condition: pd.Series, message: str,
                   output: Union[str, Tuple[str, ...]] = _OUTPUT_EXCEL) -> pd.DataFrame:
    condition_is_false = df[~condition]
    if len(condition_is_false) > 0:
        _log_mistakes_helper(condition_is_false, message, output=output)
        df = df[condition]
    return df
    
def apply(df: pd.DataFrame, f: Any, verbose: bool = False) -> List[Any]:
    result = []
    values_range = df.values
    if verbose:
        values_range = tqdm(values_range)
    for values in values_range:
        result.append(f(*values))
    return result

def get(df: pd.DataFrame, index: Any) -> pd.DataFrame:
    try:
        return df.loc[index]
    except KeyError:
        return pd.DataFrame(columns=df.columns)

def groupby_apply_parallel(df: pd.DataFrame, group_cols: List[str], func: Callable[[pd.DataFrame], pd.DataFrame], pool: multiprocessing.pool.Pool):
    r = []
    for g in tqdm(pool.imap_unordered(func, (group for _, group in df.groupby(group_cols))), total=len(df.drop_duplicates(group_cols))):
        r.append(g)
    return pd.concat(r)

def select(df: pd.DataFrame, mask: Union[pd.Series, np.ndarray]) -> pd.DataFrame:
    if isinstance(mask, pd.Series): 
        mask = mask.values
    return pd.DataFrame({col: df[col].values[mask] for col in df.columns}, index = df.index[mask])

def memory_usage():
    ipython_vars = ['In', 'Out', 'exit', 'quit', 'get_ipython', 'ipython_vars']

    mem = pd.DataFrame([
        {"name": x, "size": sys.getsizeof(globals().get(x)) / 2**30}
        for x in dir() if not x.startswith('_') and x not in sys.modules and x not in ipython_vars
    ]).sort_values("size", ascending = False)
    mem["sumsize"] = mem["size"].cumsum()
    return mem

def assign(df:pd.DataFrame, col: str, s: pd.Series) -> pd.DataFrame:
    if col in df.columns:
        df.drop(columns = [col], inplace = True)
    s = s.rename(col)
    return pd.merge(df, s.reset_index(), how = "left", on = s.index.names, copy = False)


def merge_update(left: DataFrame, right: DataFrame, on: Union[List[str], str], **kwargs: Any) -> DataFrame:
    if isinstance(on, str):
        on = [on]
    left.drop(columns = left.columns.intersection(right.columns).difference(on), inplace = True)
    return cast(DataFrame, pd.merge(left, right, on=on, **kwargs))

def _rolling_quantile_helper(s: pd.Series, window: int, quantile: float) -> pd.Series:
    return s.rolling(window).quantile(quantile) # type:ignore

def rolling_quantile(groups: Iterable[Tuple[str, pd.Series]], window: int, quantile: float, pool: Optional[multiprocessing.pool.Pool] = None) -> pd.Series:
    f = partial(_rolling_quantile_helper, window = window, quantile = quantile)

    if pool is not None:
        results_iterator = pool.imap_unordered(f, [s for _, s in groups])
    else:
        results_iterator = map(f, [s for _, s in groups])

    return pd.concat(list(results_iterator))
    
def _fast_rolling_quantile_helper(s: np.array, window: int, quantile: float) -> pd.Series:
    values = rq.Pipeline(rq.LowPass(window=window, quantile=quantile)).feed(s.values)
    return pd.Series(values, index = s.index)

def _fast_rolling_quantile_helper(s: np.array, window: int, quantile: float) -> pd.Series:
    return rq.Pipeline(rq.LowPass(window=window, quantile=quantile)).feed(s)
    # return pd.Series(values, index = s.index)


def fast_rolling_quantile(groups: Iterable[Tuple[str, pd.Series]], window: int, quantile: float, pool: Optional[multiprocessing.pool.Pool] = None) -> pd.Series:
    f = partial(_fast_rolling_quantile_helper, window = window, quantile = quantile)

    if pool is not None:
        results_iterator = pool.map(f, [s.values for _, s in groups])
    else:
        results_iterator = map(f, [s.values for _, s in groups])

    return np.hstack(list(results_iterator))
    # return pd.concat(list(results_iterator))
    