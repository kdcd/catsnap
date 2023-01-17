import datetime
import json
import logging
import os
import sys
import time
import traceback
from distutils.util import strtobool
from threading import local
from copy import copy
from inspect import istraceback
from typing import Mapping, Any, List, Optional, Tuple, Type, Dict
from types import TracebackType

_locals = local()


def refresh(data: Mapping[str, str]) -> None:
    delete_trace_id()
    delete_datadog_trace_id()
    delete_datadog_span_id()
    delete_user_data()
    set_trace_id(data['trace_id'])
    set_datadog_trace_id(data['datadog_trace_id'])
    set_datadog_span_id(data['datadog_span_id'])
    if 'user_id' in data and 'user_name' in data:
        set_user_data(data['user_id'], data['user_name'])


def set_trace_id(trace_id: str) -> None:
    _locals.trace_id = trace_id


def set_datadog_trace_id(datadog_trace_id: str) -> None:
    _locals.datadog_trace_id = datadog_trace_id


def set_datadog_span_id(datadog_span_id: str) -> None:
    _locals.datadog_span_id = datadog_span_id


def set_user_data(user_id: str, user_name: str) -> None:
    _locals.user_id = user_id
    _locals.user_name = user_name


def get_trace_id() -> Optional[str]:
    return getattr(_locals, 'trace_id', None)


def get_datadog_trace_id() -> Optional[str]:
    return getattr(_locals, 'datadog_trace_id', None)


def get_datadog_span_id() -> Optional[str]:
    return getattr(_locals, 'datadog_span_id', None)


def get_user_data() -> Tuple[Optional[str], Optional[str]]:
    user_id = getattr(_locals, 'user_id', None)
    user_name = getattr(_locals, 'user_name', None)
    return user_id, user_name

def get_data():
    return getattr(_locals, 'data', None)


def delete_trace_id() -> None:
    keys = set(_locals.__dict__.keys())
    if "trace_id" in keys:
        delattr(_locals, "trace_id")


def delete_datadog_trace_id() -> None:
    keys = set(_locals.__dict__.keys())
    if "datadog_trace_id" in keys:
        delattr(_locals, "datadog_trace_id")


def delete_datadog_span_id() -> None:
    keys = set(_locals.__dict__.keys())
    if "datadog_span_id" in keys:
        delattr(_locals, "datadog_span_id")


def delete_user_data() -> None:
    keys = set(_locals.__dict__.keys())
    if "user_id" in keys:
        delattr(_locals, "user_id")
    if "user_name" in keys:
        delattr(_locals, "user_name")


MAIN_MODULE_NAME = "main_module_name"

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

SIMPLE_FORMAT = "[%(asctime)s][%(threadName)s][%(name)-20s][%(levelname)-10s]  %(message)s (%(filename)s:%(lineno)d:%(funcName)s)"
FORMAT = "[%(asctime)s][$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d:%(funcName)s)"
custom_format = {
    'host': '%(hostname)s',
    'level': '%(levelname)s',
    'logger_name': '%(module)s',
    'where': '%(module)s.%(funcName)s',
    'type': '%(levelname)s',
    'stack_trace': '%(exc_text)s'
}

DEFAULT_LOG_RECORD_FIELDS = {'name', 'msg', 'args', 'levelname', 'levelno',
                             'pathname', 'filename', 'module', 'exc_info',
                             'exc_class', 'exc_msg', 'exc_traceback',
                             'exc_text', 'stack_info', 'lineno', 'funcName',
                             'created', 'msecs', 'relativeCreated', 'thread',
                             'threadName', 'processName', 'process'}

# TRACING_FIELDS = {'trace_id', 'datadog_trace_id', 'datadog_span_id', 'user_id', 'user_name'}

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

_levelToName = {
    CRITICAL: 'CRITICAL',
    ERROR: 'ERROR',
    WARNING: 'WARNING',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
    NOTSET: 'NOTSET',
}


_logger_list: List[Any] = []
_logger_map: Dict[str, Any] = {}


def formatter_message(message: str, use_color: bool = True) -> str:
    if use_color:
        message = message.replace(
            "$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


COLOR_FORMAT = formatter_message(FORMAT, True)


def set_level(level: int) -> None:
    for logger in _logger_list:
        logger.setLevel(level)


class SimpleSTDErrorFormatter(object):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def handle_exception(self, type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
        if issubclass(type_, KeyboardInterrupt):
            sys.__excepthook__(type_, value, traceback)
            return

        self.logger.error("Uncaught exception", exc_info=(
            type_, value, traceback))


def set_global_lebel(level: str) -> None:
    assert level in logging._nameToLevel, f"level = {level} not found" # type: ignore
    for logger in _logger_list:
        logger.setLevel(logging._nameToLevel[level]) # type: ignore


# def wrap_log_method(original_info):
#     def wrapped(message, *args, **kwargs):
#         stack = inspect.stack()

#         # stack[1] gives previous function ('info' in our case)
#         # stack[2] gives before previous function and so on
#         print(stack)

#         fn = stack[2][1]
#         ln = stack[2][2]
#         func = stack[2][3]

#         return original_info(f"{fn}, {ln}, {func} {message}", *args, **kwargs)
#     return wrapped

def get_logger(module_name: str, redirect_stderr: bool = True, add_datadog_handler: bool = False) -> logging.Logger:
    logger = _logger_map.get(module_name)
    if logger:
        return logger 
    logger = logging.getLogger(module_name)
    # logger.info = wrap_log_method(logger.info)
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    if strtobool(os.environ.get('JSON_LOGGING', 'false')):
        console.setFormatter(SimpleJsonFormatter())
    else:
        console.setFormatter(ColoredFormatter(COLOR_FORMAT))
    logger.addHandler(console)

    if redirect_stderr:
        err_formatter = SimpleSTDErrorFormatter(logger)
        sys.excepthook = err_formatter.handle_exception

    _logger_list.append(logger)
    _logger_map[module_name] = logger
    return logger

def remove_handlers():
    for logger in _logger_list:
        for hdlr in logger.handlers[:]: 
            logger.removeHandler(hdlr)

def get_loggers_list():
    return _logger_list


def add_file_handler(file_path: str) -> None:
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.DEBUG)

    file_handler.setFormatter(ColoredFormatter(SIMPLE_FORMAT, use_color=False))
    for logger in _logger_list:
        logger.addHandler(file_handler)


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg: str, use_color: bool = True) -> None:
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record: Any) -> str:
        record = copy(record)
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (
                30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class SimpleJsonFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__()
        self.level_to_name_mapping = _levelToName

    @staticmethod
    def _default_json_handler(obj: Any) -> str:
        if isinstance(obj, (datetime.date, datetime.time)):
            return str(obj.isoformat())
        elif istraceback(obj):
            tb = u''.join(traceback.format_tb(obj))
            return tb.strip()
        elif isinstance(obj, Exception):
            return u"Exception: {}".format(str(obj))
        return str(obj)

    def format(self, record: Any) -> str:
        msg = {
            'logger_name': str(record.name),
            'line_number': record.lineno,
            'module': str(record.module),
            'level': str(self.level_to_name_mapping[record.levelno]),
            'path': str(record.pathname),
            # 'trace_id': get_trace_id(),
            # 'datadog_trace_id': get_datadog_trace_id(),
            # 'datadog_span_id': get_datadog_span_id(),
        }
        # data = get_data()
        # if data is not None:
        #     msg = {"data": data}
        user_id, user_name = get_user_data()
        if user_id and user_name:
            msg.update({
                'user_id': user_id,
                'user_name': user_name,
            })

        for field, value in record.__dict__.items():
            if field not in DEFAULT_LOG_RECORD_FIELDS:
                msg[field] = value  # if type(value) in [int, float]

        if isinstance(record.msg, dict):
            msg.update(record.msg)
        else:
            if len(record.args) > 0 and '%s' in record.msg:
                record.msg = record.msg % record.args
                record.args = ()
            msg['message'] = record.msg

        if record.exc_info:
            msg['exception'] = logging.Formatter.formatException(
                self, record.exc_info)

        return str(json.dumps(msg, default=self._default_json_handler))


class ThreadLogFilter(logging.Filter):
    def __init__(self, thread_name: str):
        logging.Filter.__init__(self)
        self.thread_name = thread_name

    def filter(self, record: logging.LogRecord):
        return record.threadName == self.thread_name