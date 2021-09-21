from typing import Union, List, Any, Tuple

import pandas as pd
from tqdm import tqdm

from . import funcutil, logutil, pathutil, excel

from multiprocessing import Pool, cpu_count

_logger = logutil.get_logger(__name__)

_OUTPUT_EXCEL = "excel"
_OUTPUT_CONSOLE = "console"


def _log_mistakes_helper(df: pd.DataFrame, message: str, output: Union[str, Tuple[str, ...]] = _OUTPUT_EXCEL) -> None:
    output = funcutil.to_list(output)  # type: ignore

    if _OUTPUT_CONSOLE in output:
        _logger.warning(f"{message}: {len(df)}\n{df.to_string()}")
    else:
        _logger.warning(f"{message}: {len(df)}")


def merge(left: pd.DataFrame, right: pd.DataFrame, on: Union[List[str], str], **kwargs: Any) -> pd.DataFrame:
    if isinstance(on, str):
        on = [on]
    right = right[right.columns.difference(left.columns) | pd.Index(on)]
    return pd.merge(left, right, on=on, **kwargs)


def select_and_log(df: pd.DataFrame, condition: pd.Series, message: str,
                   output: Union[str, Tuple[str, ...]] = _OUTPUT_EXCEL) -> pd.DataFrame:
    condition_is_false = df[~condition]
    if len(condition_is_false) > 0:
        _log_mistakes_helper(condition_is_false, message, output=output)
        df = df[condition]
    return 
    
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

def groupby_apply_parallel(df: pd.DataFrame, group_cols: List[str], func, pool: Pool):
    r = []
    for g in tqdm(pool.imap_unordered(func, (group for name, group in df.groupby(group_cols))), total=len(df.drop_duplicates(group_cols))):
        r.append(g)
    return pd.concat(r)