from collections import defaultdict, Sequence
from typing import List, Optional, Any, Dict

import numpy as np
import pandas as pd
from pandas.core.indexes.multi import MultiIndex


def row_to_str_list(row: Any) -> List[Any]:
    def transform(value: Any) -> Optional[str]:
        if isinstance(value, Sequence):
            return str(value)
        if pd.isnull(value):
            return None
        if isinstance(value, str) and len(value) == 0:
            return None
        return str(value)

    return list(map(transform, row))


def from_nested(tables: List[pd.DataFrame], index_names: List[Any]) -> List[Any]:
    index_names = index_names
    index_names = list(map(lambda s: s if isinstance(s, (list, tuple)) else [s], index_names))
    ancestors: Dict[Any, List[Any]] = defaultdict(list)

    def get_key(table_id: int, names: List[str], row: Dict[str, Any]) -> int:
        try:
            key = tuple(row[name] for name in names)
            return hash((table_id, key))
        except KeyError as e:
            raise Exception(f"Couldn't find key in row {row.keys()}") from e

    def get_ancestors(table_id: int, row: Dict[str, Any]) -> List[Any]:
        return ancestors[get_key(table_id, index_names[table_id], row)]

    def add_ancestor(table_id: int, row: Dict[str, Any]) -> None:
        ancestors[get_key(table_id, index_names[table_id], row)].append(row)

    result = []

    for i, index_name in zip(range(1, len(tables)), index_names):
        for row in tables[i].to_dict(orient="records"):
            add_ancestor(i - 1, row)

    def nested_row(table_id: Any, row: Dict[str, Any]) -> Any:
        line = (row_to_str_list(row.values()), table_id + 1)
        if table_id + 1 >= len(tables):
            return [line]

        ancestors = get_ancestors(table_id, row)
        if len(ancestors) == 0:
            return [line]

        result = [(list(tables[table_id + 1].columns), table_id + 2)]
        for ancestor in ancestors:
            result.extend(nested_row(table_id + 1, ancestor))
        return result + [line]

    result.append((list(tables[0].columns), 1))
    for row in tables[0].to_dict(orient="records"):
        result.extend(nested_row(0, row))
    return list(zip(*result))


def df_from_nested(tables: List[pd.DataFrame], index_names: List[Any]) -> Any:
    rows, levels = from_nested(tables, index_names)
    max_row_len = max(map(len, rows))
    rows = list(map(lambda row: row + [""] * (max_row_len - len(row)), rows))
    return pd.DataFrame(rows), levels


def from_df(df: pd.DataFrame) -> Any:
    values, columns = [], []
    index_width = 0
    height, width = df.shape
    if isinstance(df.index, MultiIndex):
        index = []
        index_width = len(df.index.levels)
        for i in range(index_width):
            index.append(df.index.levels[i][df.index.labels[i]])
        rows = df.values.tolist()
        for index_row, row in zip(np.array(index).transpose(), rows):
            values.append(row_to_str_list(list(index_row) + row))
    elif df.index.names and any(name is not None for name in df.index.names):
        index_width = 1
        for index_row, row in zip(df.index, df.values.tolist()):
            values.append(row_to_str_list([index_row] + row))
    else:
        values = [row_to_str_list(lst) for lst in df.values.tolist()]

    columns_height = 1
    if isinstance(df.columns, MultiIndex):
        columns_height = len(df.columns.levels)
        for i in range(columns_height):
            columns.append(row_to_str_list([' '] * index_width + list(df.columns.levels[i][df.columns.labels[i]])))
    else:
        columns = [[' '] * index_width + list(df.columns)]

    height += columns_height
    width += index_width

    return columns + values, (height, width)
