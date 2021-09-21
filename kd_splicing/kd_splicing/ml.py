from __future__ import annotations

import pickle
from operator import itemgetter
from typing import List, Mapping, Tuple, Union

import pandas as pd
from sklearn import preprocessing, svm
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn import svm
from tqdm import tqdm

from kd_common import logutil
from kd_splicing import database, performance
from kd_splicing.models import Match

_logger = logutil.get_logger(__name__)


def _extract_features(matches: List[Match]) -> Tuple[Tuple[float, ...], ...]:
    return tuple(
        (
            m.isoform_blast_score,
            m.splicing_difference,
            m.splicing_similarity,
            m.splicing_dissimilarity,
        )
        for m in matches
    )


class Detector:
    def fit(self, model_name: str, matches: List[Match]) -> None:
        self.model_name = model_name
        if model_name == "logistic_regression":
            self.model = LogisticRegression(solver='lbfgs')
        elif model_name == "svm":
            self.model = svm.SVC(probability=True)
        elif model_name == "boosting":
            self.model = GradientBoostingClassifier(n_estimators=30, subsample=0.1, min_samples_leaf=10)
        elif model_name == "nn":
            self.model = MLPClassifier(solver='lbfgs', alpha=1e-4, hidden_layer_sizes=(5, 2), random_state=1, max_iter = 1000)
        else: assert(False)

        y = tuple(m.positive for m in matches)
        x_train = _extract_features(matches)
        self.scaler = preprocessing.StandardScaler().fit(x_train)
        x_train = self.scaler.transform(x_train)
        self.model.fit(x_train, y)

    def transform(self, matches: List[Match]) -> None:
        if not matches:
            return
        features = _extract_features(matches)
        x = self.scaler.transform(features)
        classes = self.model.predict(x)
        probs = self.model.predict_proba(x)[:, 1]
        for m, c, prob in zip(matches, classes, probs):
            m.predicted_positive_probability = float(prob)
            m.predicted_positive = c

    def cross_validate(self, model_name: str, matches: List[Match], db: database.models.DB, cross_validation_results: bool = True) -> None:
        queries = list({m.query_isoforms for m in matches})

        _logger.info(f"Start cross validation for {len(queries)} locus tags")
        results: List[Mapping[str, Union[float, str]]] = []
        aggregated_test_correct = []
        aggregated_test_predicted = []
        aggregated_test_probs = []
        for i in tqdm(range(0, len(queries))):
            test_query = queries[i]
            test_queries = {test_query}
            train_queries = set(queries) - test_queries
            train = [m for m in matches if m.query_isoforms in train_queries]
            test = [m for m in matches if m.query_isoforms in test_queries]
            self.fit(model_name, train)
            self.transform(test)
            test_predicted = [t.predicted_positive for t in test]
            test_probs = [t.predicted_positive_probability for t in test]
            test_correct = [t.positive for t in test]
            aggregated_test_correct.extend(test_correct)
            aggregated_test_probs.extend(test_probs)
            aggregated_test_predicted.extend(test_predicted)
            test_iso_a = db.isoforms[test_query.a]
            test_iso_b = db.isoforms[test_query.b]
            results.append({
                **performance.binary_y_performance(test_correct, test_predicted),
                "test_size": len(test),
                "test_positive_count": sum(test_correct),
                "test_positive_predicted_count": sum(test_predicted),
                "test_isoforms": (test_iso_a.protein_id or "") + "," + (test_iso_b.protein_id or "")
            })

        df = pd.DataFrame(results)
        df = df.sort_values("f1")
        _logger.info(f"Model: {self.model_name}")
        results = pd.Series(performance.binary_y_performance(aggregated_test_correct, aggregated_test_predicted))
        _logger.info(f"Aggregated result:\n{results.to_string()}")
        for value in results.values:
            print(value)
        if cross_validation_results: 
            _logger.info(f"Cross validation results:\n{df.to_string()}")
        return {"y": aggregated_test_correct, "probs": aggregated_test_probs}

    def save(self, file_path: str) -> None:
        with open(file_path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(file_path: str) -> Detector:
        with open(file_path, "rb") as f:
            return pickle.load(f)
