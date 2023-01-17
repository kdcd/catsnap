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
        "muscle", "-in", input_file, "-out", output_file,
    ]
    _logger.info("Start Muscle")
    r = subprocess.call(blast_args)
    try: 
        r = subprocess.check_output(blast_args, stderr=subprocess.STDOUT, timeout=200)
    except subprocess.CalledProcessError as e:
        raise CustomException("Muscle alignment error")
    except subprocess.TimeoutExpired as e:
        raise CustomException('One of the entered sequences is too long, check out&nbsp;<a href="/help#custom_sequence_troubleshooting">troubleshooting</a>')
    _logger.info(r)
    _logger.info("Finish Muscle")
    return output_file

newlines = ['\n', '\r\n', '\r']
def unbuffered(proc, stream='stdout'):
    stream = getattr(proc, stream)
    with contextlib.closing(stream):
        while True:
            out = []
            last = stream.read(1)
            if last == '' and proc.poll() is not None:
                break
            while last not in newlines:
                if last == '' and proc.poll() is not None:
                    break
                out.append(last)
                last = stream.read(1)
            out = ''.join(out)
            yield out

def run_single_with_progress(input_file: str, output_file: Optional[str] = None, ) -> Generator[str, None, None]:
    if not output_file:
        output_file = input_file + ".aligned"

    args = [
        "muscle", "-in", input_file, "-out", output_file
    ]
    _logger.info("Start Muscle and get")
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    for line in unbuffered(p):
        m = re.search(r'Iter\s+(\d+)\s*(\d+\.\d+)', line)
        if m:
            yield f"Iteration {m.group(1)} {m.group(2)}%"
    _logger.info("Finish Muscle")
    return output_file