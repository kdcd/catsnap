from typing import Any, List, Dict
from collections import defaultdict

import pandas as pd

from googleapiclient.discovery import build

from kd_common.google import common
from kd_common import logutil

_logger = logutil.get_logger(__name__)
_service = None
_RANGE = "A1:ZZ"


def _get_service() -> Any:
    global _service
    _service = build('sheets', 'v4', credentials=common.get_credentials())
    return _service


def _handle_columns(columns: List[str]) -> List[str]:
    count_name: Dict[str, int] = defaultdict(int)

    def get_name(col: str) -> str:
        cnt = count_name[col]
        count_name[col] = cnt + 1
        if cnt == 0:
            return col
        return col + str(cnt)

    return [get_name(col) for col in columns]


def read(table_path: str) -> pd.DataFrame:
    try:
        spreadsheet_id, sheet_name = table_path.split("/")

        _logger.info(f"Start reading '{sheet_name}' from gsheet")
        range_name = sheet_name + "!" + _RANGE
        result = _get_service().spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        rows = result.get('values', [])

        if rows:
            max_row_len = max(map(len, rows))
            rows = list(
                map(lambda row: row + [""] * (max_row_len - len(row)), rows))
            _logger.info(f"Finish reading '{sheet_name}' from gsheet")
            df = pd.DataFrame(rows[1:], columns=_handle_columns(rows[0]))
            return df
        _logger.info(f'No data found in table {spreadsheet_id} {sheet_name}')
        return pd.DataFrame()
    except Exception as e:
        raise Exception(f"Couldn't read from gsheet {table_path}") from e
