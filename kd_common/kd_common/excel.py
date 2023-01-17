from typing import List, Any, Optional, cast

import pandas as pd
import numpy as np

from . import logutil
from kd_common import table


_logger = logutil.get_logger(__name__)


def max_length(lines: str) -> int:
    return max((len(line) for line in lines.splitlines()), default=0)


def _write(
    writer: pd.ExcelWriter,
    df: pd.DataFrame,
    sheet_name: str,
    levels: Optional[List[Any]] = None,
) -> None:
    if df.empty:
        return
    col_len = [
        cast(float, df[col].astype(str).apply(max_length).quantile(0.95))
        for col in df.columns
    ]
    col_len = np.clip(col_len, 20, 120)

    df.to_excel(writer, sheet_name=sheet_name, index=False)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    fmt = workbook.add_format()
    fmt.set_text_wrap()
    for i in range(len(df.columns)):
        worksheet.set_column(i, i + 1, int(col_len[i]), fmt)
    if levels is not None:
        for idx, level in enumerate(levels):
            worksheet.set_row(
                idx + 1, None, None, {"level": level, "hidden": True, "collapsed": True}
            )


def write(df: pd.DataFrame, path: str, levels: Optional[List[Any]] = None) -> None:
    _logger.info("Start writing to excel " + path)
    with pd.ExcelWriter(path, engine="xlsxwriter") as w: # type: ignore
        _write(w, df, "sheet", levels)
    _logger.info("Finish writing to excel " + path)


def write_nested_df(
    data_frames: List[pd.DataFrame], index_names: List[Any], table_path: str
) -> None:
    df, levels = table.df_from_nested(data_frames, index_names)
    df["level"] = levels
    write(df, table_path, levels)
