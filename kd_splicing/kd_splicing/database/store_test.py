import unittest
from pprint import PrettyPrinter, pprint
from kd_splicing.location.models import Location, LocationPart

from kd_splicing.database.store import _intersect


class UtilsTestCase(unittest.TestCase):
    def test_union(self) -> None:
        parts = [
            LocationPart(1, 2, 1, {"a": {1}}),
            LocationPart(3, 5, 1, {"a": {2}}),
            LocationPart(4, 5, 1, {"a": {3}}),
            LocationPart(4, 5, 1, {"b": {4}}),
            LocationPart(3, 4, 1, {"b": {5}}),
        ]
        result = _intersect(parts)
        c = Location([
            LocationPart(start=3, end=4, strand=None,
                         data={'a': {2}, 'b': {5}}),
            LocationPart(start=4, end=5, strand=None,
                         data={'a': {2, 3}, 'b': {4}}),
        ])
        self.assertEqual(c, result)
