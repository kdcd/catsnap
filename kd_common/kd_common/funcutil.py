import collections
from typing import List, Union, Any, Generator, Set, Sequence, TypeVar, Optional, Tuple, Iterable
from types import ModuleType, FunctionType
from gc import get_referents
import sys


T = TypeVar('T')


def to_list(seq: Optional[Union[List[T], Tuple[T, ...], Set[T], str]], unique_flag: bool = False) -> List[Union[T, str]]:
    if seq is None:
        return []

    if isinstance(seq, (set, list, tuple)):
        return list(seq)

    return [seq]


def unique(sequence: Iterable[T]) -> List[T]:
    seen: Set[Any] = set()
    result = []
    for x in sequence:
        if not x in seen:
            seen.add(x)
            result.append(x)
    return result


_BLACKLIST = type, ModuleType, FunctionType

def getsize(obj: Any) -> int:
    if isinstance(obj, _BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids: Set[Any] = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, _BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size

def flatten(l):
    if isinstance(l, float) or l is None:
        return []
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el
