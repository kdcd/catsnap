from typing import Generator, List, Optional
from kd_common import logutil
import subprocess
import contextlib
import re

from kd_splicing.models import AlignStatus
from kd_splicing.exception import CustomException

_logger = logutil.get_logger(__name__)

def run_multiple(input_files: List[str]) -> List[str]:
    return [run_single(f) for f in input_files]

def run_single(input_file: str, output_file: Optional[str] = None) -> str:
    if not output_file:
        output_file = input_file + ".aligned"

    blast_args = [
        "kalign", "-i", input_file, "-o", output_file,
    ]
    _logger.info("Start Kaline")
    r = subprocess.call(blast_args)
    try: 
        r = subprocess.check_output(blast_args, stderr=subprocess.STDOUT, timeout=10)
    except subprocess.CalledProcessError as e:
        raise CustomException("Muscle alignment error")
    except subprocess.TimeoutExpired as e:
        raise CustomException('One of the entered sequences is too long, check out&nbsp;<a href="/help#custom_sequence_troubleshooting">troubleshooting</a>')
    _logger.info(r)
    _logger.info("Finish Muscle")
    return output_file
