
from typing import  List
import concurrent.futures
from kd_common import logutil
from typing import Optional

_logger = logutil.get_logger(__name__)

def cuncurrent_wait(futures: List[concurrent.futures.Future], timeout: Optional[float] = None): #type: ignore
    concurrent.futures.wait(futures, timeout=timeout)
    for f in futures:
        f.result()
        
        