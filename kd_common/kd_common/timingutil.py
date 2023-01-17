from dataclasses import dataclass
import time
from typing import Any
from kd_common import logutil, pathutil
import inspect
from functools import wraps


_logger = logutil.get_logger(__name__)

@dataclass
class Timing:
    begin: float

    def end(self, description: str) -> None:
        end = time.time()
        _logger.info(f"Timing {description} {end - self.begin}")


def begin() -> Timing:
    return Timing(
        begin=time.time(),
    )


def _fully_qualified_name(func: Any):
    name = func.__qualname__
    workdir = str(pathutil.FOLDER_PROJECTS_ROOT)
    return ".".join((func.__code__.co_filename[len(workdir) + 1:-3], name))


class TimingArg:
    def __init__(self, arg_name: str, pos: int):
        self.arg_name = arg_name
        self.arg_position = pos

    def extract(self, func: Any, *func_args: Any, **func_kwargs: Any) -> Any:
        if self.arg_name in func_kwargs:
            return self.arg_name, func_kwargs[self.arg_name]
        elif list(inspect.signature(func).parameters.keys())[self.arg_position] == self.arg_name:
            if len(func_args) <= self.arg_position:
                return self.arg_name, list(inspect.signature(func).parameters.values())[self.arg_position]
            return self.arg_name, func_args[self.arg_position]
        raise AttributeError(f"No such argument in '{func.__name__}' function:"
                             f" {self.arg_name} (position {self.arg_position})")


class timing:
    def __init__(self, *func_args: TimingArg):
        self._func_args = func_args

    def __call__(self, func: Any):
        name = _fully_qualified_name(func)

        @wraps(func)
        def _wrapped(*args: Any, **kwargs: Any):
            begin = time.monotonic()
            result = func(*args, **kwargs)
            end = time.monotonic()
            duration = (end - begin) 
            func_args = [arg.extract(func, *args, **kwargs) for arg in self._func_args]
            _logger.info(f"Duration of {name} with {func_args} is {duration:.4f}s")
            return result

        return _wrapped

