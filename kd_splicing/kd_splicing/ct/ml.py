from kd_splicing.ct.common import concat

Y = "y"

SUFFIX_PREDICTED = "_predicted"
SUFFIX_PREDICTED_PROBA = "_predicted_proba"
SUFFIX_ACCURACY = "_accuracy"
SUFFIX_PRECISION = "_precision"
SUFFIX_RECALL = "_recall"
SUFFIX_F1 = "_f1"


def accuracy(y: str) -> str:
    return concat(y, SUFFIX_ACCURACY)


def recall(y: str) -> str:
    return concat(y, SUFFIX_RECALL)


def precision(y: str) -> str:
    return concat(y, SUFFIX_PRECISION)


def f1(y: str) -> str:
    return concat(y, SUFFIX_F1)


def predicted(y: str) -> str:
    return concat(y, SUFFIX_PREDICTED)


def predicted_proba(y: str) -> str:
    return concat(y, SUFFIX_PREDICTED_PROBA)
