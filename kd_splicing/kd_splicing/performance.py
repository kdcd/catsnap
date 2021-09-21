
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from typing import Sequence, Union, Mapping

def binary_y_performance(correct: Sequence[Union[int, bool, None]], predicted: Sequence[Union[int, bool, None]]) -> Mapping[str, float]:
    correct = [c if c else False for c in correct]
    predicted = [p if p else False for p in predicted]
    return {
        "accuracy": accuracy_score(correct, predicted),
        "precision": precision_score(correct, predicted, zero_division=0) if sum(predicted) > 0 else 0 ,
        "recall": recall_score(correct, predicted, zero_division=0) if sum(correct) > 0 else 0,
        "f1": f1_score(correct, predicted, zero_division=0)
    }
