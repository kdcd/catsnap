from dataclasses import dataclass, field
import datetime
from typing import Iterable, List, Optional, Union, Any
import time

import pandas as pd

from kd_common import logutil

_logger = logutil.get_logger(__name__)

class _TimeManager:
    def sleep(self, seconds: float):
        time.sleep(seconds)
    
    def now(self, timezone: Any = None) -> datetime.datetime:
        return datetime.datetime.now(timezone)
        
@dataclass
class _FakeTimeManager(_TimeManager):
    _now: datetime.datetime = field(default_factory = lambda : datetime.datetime.now(datetime.timezone.utc))

    def sleep(self, seconds: float):
        self._now += datetime.timedelta(seconds=seconds + 0.001)
    
    def now(self, timezone: Any = None) -> datetime.datetime:
        return self._now

_time = _TimeManager()

def debug():
    global _time
    _time = _FakeTimeManager()

# Dataclasses
@dataclass
class PauseInfo:
    datetime: datetime.datetime
    index: int
    indices_till_end: int

# Pause
def pause_until(end: datetime.datetime):
    now = _time.now(timezone=end.tzinfo)
    delta = end - now
    _logger.info(f"Pause until {end} delta {delta} now {now}")
    while delta.total_seconds() >= 0:
        _time.sleep(delta.total_seconds() / 2)
        delta = end - _time.now(timezone=end.tzinfo)
def pause_every_day_at(stop: datetime.time) -> Iterable[PauseInfo]:
    index = 0
    while True:
        now = _time.now(datetime.timezone.utc)
        current_date = now.date()
        stop_datetime = datetime.datetime.combine(current_date, stop, tzinfo=stop.tzinfo)
        if stop_datetime < now:
            stop_datetime += datetime.timedelta(days=1)
        pause_until(stop_datetime)
        yield PauseInfo(_time.now(datetime.timezone.utc), index = index, indices_till_end=-1)
        index += 1
def pause_every(
    begin: Union[str, datetime.datetime],
    end: Optional[Union[str, datetime.datetime]] = None,
    count:int = 0,
    minutes: int = 0,
    seconds: int = 0
) -> Iterable[PauseInfo]:
    assert (end is not None or count > 0)

    if isinstance(begin, str):
        begin = datetime.datetime.strptime(begin, '%H:%M:%S %z')
    if end is not None and isinstance(end, str):
        end = datetime.datetime.strptime(end, '%H:%M:%S %z')

    now = _time.now(datetime.timezone.utc)
    today = _time.now(datetime.timezone.utc).date()
    today_begin = datetime.datetime.combine(today, begin.time(), tzinfo=begin.tzinfo)
    index = 0
    delta = datetime.timedelta(minutes=minutes, seconds = seconds)

    if end is not None:
        today_end = datetime.datetime.combine(today, end.time(), tzinfo=end.tzinfo)
        indices_till_end = int(((today_end - today_begin) / delta))
    else:
        indices_till_end = count - 1
        today_end = delta * indices_till_end + today_begin

    _logger.info(f"Pause every {minutes} minutes {seconds} seconds, now {now} begin {today_begin} end {today_end}  pause count {indices_till_end + 1}")

    pause_until(today_begin)
    next_stop = today_begin
    while indices_till_end >= 0:
        yield PauseInfo(datetime = next_stop, index = index, indices_till_end  = indices_till_end)

        index += 1
        indices_till_end -= 1

        if indices_till_end < 0: break

        next_stop = (next_stop + delta).replace(microsecond=0)
        if seconds == 0:
            next_stop = next_stop.replace(second=0)
        pause_until(next_stop)
def pause_on(s: pd.DatetimeIndex) -> Iterable[pd.Timestamp]: #type: ignore
    s = s[s > pd.Timestamp.now("utc")] #type: ignore
    for timestamp in s:
        pause_until(timestamp.to_pydatetime())
        yield timestamp
# Helpers
def dates_between(begin: datetime.date, end: datetime.date) -> List[datetime.date]:        
    result = []
    while begin <= end:
        result.append(begin)
        begin += datetime.timedelta(days = 1)
    return result
def add_time(t: datetime.time,  hours: int = 0, minutes: int = 0, seconds: int = 0) -> datetime.time:
    return (datetime.datetime.combine(datetime.date.today(), t) + datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)).timetz()
def next_delta(dt: datetime.datetime, minutes: int = 0, seconds: int = 0) -> datetime.datetime:
    next = (dt + datetime.timedelta(minutes = minutes, seconds = seconds)).replace(microsecond=0)
    if seconds == 0:
        next.replace(second = 0)
    return next
def next_minute(dt: datetime.datetime) -> datetime.datetime:
    return next_delta(dt, minutes=1)
def to_pauses(datetime_list: List[Union[datetime.datetime, datetime.date]]) -> List[PauseInfo]:
    return [
        PauseInfo(
            datetime=dt if isinstance(dt, datetime.datetime) else datetime.datetime.combine(dt, datetime.time()), 
            index=i, 
            indices_till_end=len(datetime_list) - i - 1
        )
        for i, dt in enumerate(datetime_list)
    ]
def now() -> datetime.datetime:
    return _time.now(datetime.timezone.utc)


if __name__ == "__main__":
    _time = _FakeTimeManager()

    begin_datetime = next_minute(datetime.datetime.now(datetime.timezone.utc))
    end_time = begin_datetime + datetime.timedelta(minutes = 10)
    print(datetime.datetime.now(datetime.timezone.utc), begin_datetime, end_time)
    for p in pause_every(minutes=1, begin=next_minute(begin_datetime), end=next_minute(begin_datetime)): 
        print(p)
