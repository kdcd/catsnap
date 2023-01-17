from __future__ import annotations

import datetime
from functools import partial
import multiprocessing
import multiprocessing.pool
from typing import Iterable, List, Mapping, Optional, Union, Any
import pandas as pd
import polars as pl
from polars.internals.frame import DynamicGroupBy, GroupBy
from polars.internals.lazy_frame import LazyGroupBy
import numpy as np

from kd_common import logutil

_logger = logutil.get_logger(__name__)



try: 
    import rolling_quantiles as rq
except: pass

pl.Config.set_tbl_rows(40)

def _rolling_quantile_helper(s: np.array, window: int, quantile: float) -> np.array:
    return rq.Pipeline(rq.LowPass(window=window, quantile=quantile)).feed(s) #type: ignore
def rolling_quantile(s: pl.Series, window: int, quantile: float) -> np.array:
    return rq.Pipeline(rq.LowPass(window=window, quantile=quantile)).feed(s.to_numpy()) #type: ignore
def groups_rolling_quantile(groups: Iterable[pl.Series], window: int, quantile: float, pool: Optional[multiprocessing.pool.Pool] = None) -> np.array:
    f = partial(_rolling_quantile_helper, window = window, quantile = quantile)

    if pool is not None:
        results_iterator = pool.map(f, [s.to_numpy() for s in groups])
    else:
        results_iterator = map(f, [s.to_numpy() for s in groups])

    return pl.Series(np.hstack(list(results_iterator)))
def groupby_rolling_quantile(df: pl.DataFrame, group: str, c: Union[pl.Expr, str], window: int, quantile: float, pool: Optional[multiprocessing.pool.Pool] = None) -> np.array:
    return groups_rolling_quantile(
        df.groupby(group, maintain_order = True).agg(
            (col[c] if isinstance(c, str) else c).list().keep_name()
        )[:, 1]
    , window, quantile, pool = pool)


def dt(s: str) -> datetime.datetime:
    return pd.to_datetime(s)
def ifthen(condition: pl.Expr, then: pl.Expr, otherwise: pl.Expr) -> pl.Expr:
    return pl.when(condition).then(then).otherwise(otherwise)
def andifthen(*args: pl.Expr, then: pl.Expr, otherwise: pl.Expr) -> pl.Expr:
    condition = pl.lit(True)
    for arg in args: 
        condition = condition & arg # type: ignore
    return pl.when(condition).then(then).otherwise(otherwise)
def win(expr: pl.Expr) -> pl.Expr:
    return ifthen(expr != 0, (expr >= 0).cast(int), pl.lit(None)).cast(pl.Int32)

class LazyDataFrame(pl.LazyFrame): #type: ignore
    def mfilter(self, *args: pl.Expr) -> 'LazyDataFrame': # type: ignore
        pass

    def mwith(self, *args: pl.Expr, **kwargs:  pl.Expr) -> 'LazyDataFrame': # type: ignore
        pass
class DataFrame(pl.DataFrame):
    def mfilter(self, *args: pl.Expr) -> 'DataFrame': # type: ignore
        pass

    def lazy(self) -> LazyDataFrame: #type: ignore
        pass

def _collect_expressions(*args: List[pl.Expr], **kwargs: Mapping[str, pl.Expr]) -> List[pl.Expr]:
    expr_list = list(args)
    for key, expr in kwargs.items():
        if not isinstance(expr, pl.Expr):
            expr = pl.lit(expr)
        expr_list.append(expr.alias(key)) #type: ignore
    return expr_list #type: ignore
def mjoin(left: pl.DataFrame, right: pl.DataFrame, on: Union[str, List[str]], **kwargs: Any) -> pl.DataFrame:
    if isinstance(on, str):
        on = [on]
    r = left.drop(list(set(left.columns) & (set(right.columns) - set(on)))) \
        .join(right, on=on, **kwargs) #type: ignore
    return r
def mfilter(self: pl.DataFrame, *args: List[pl.Expr]) -> pl.DataFrame:
    result = pl.lit(True)
    for arg in args: 
        result = result & arg # type: ignore
    return self.filter(result)
def mwith(self: pl.DataFrame, *args: List[pl.Expr], **kwargs: Mapping[str, pl.Expr]):
    return self.with_columns(_collect_expressions(*args, **kwargs)) 
def mselect(self: pl.DataFrame, *args: List[pl.Expr], **kwargs: Mapping[str, pl.Expr]):
    return self.select(_collect_expressions(*args, **kwargs)) 
def magg(self: pl.DataFrame, *args: List[pl.Expr], **kwargs: Mapping[str, pl.Expr]):
    return self.agg(_collect_expressions(*args, **kwargs)) 
def mfilter_mutate(self: pl.Expr, *args: pl.Expr, then: pl.Expr):
    return andifthen(*args, then = then, otherwise=self)
def mconcat(self: pl.DataFrame, other: pl.DataFrame, how: str = "vertical") -> pl.DataFrame:
    return pl.concat([self, other], how = how)

pl.Config.set_global_string_cache()

pl.DataFrame.mfilter = mfilter #type: ignore
pl.DataFrame.mwith = mwith #type: ignore
pl.DataFrame.mselect = mselect #type: ignore
pl.DataFrame.mjoin = mjoin #type: ignore
pl.DataFrame.magg = magg #type: ignore
pl.DataFrame.mconcat = mconcat #type: ignore

pl.LazyFrame.mwith = mwith #type: ignore
pl.LazyFrame.mselect = mselect #type: ignore
pl.LazyFrame.mfilter = mfilter #type: ignore
pl.LazyFrame.mjoin = mjoin #type: ignore

pl.Expr.mfilter = mfilter #type: ignore
pl.Expr.mfilter_mutate = mfilter_mutate #type: ignore
pl.Expr.mwin = win #type: ignore

GroupBy.magg = magg #type: ignore
DynamicGroupBy.magg = magg #type: ignore
LazyGroupBy.magg = magg #type: ignore

class ColHelper:
    def __getattr__(self, key): # type: ignore
        return pl.col(key)

    def __getitem__(self, key): # type: ignore
        return pl.col(key)
col = ColHelper()
