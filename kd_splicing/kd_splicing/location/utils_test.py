import unittest
from pprint import PrettyPrinter, pprint

from kd_splicing.location.models import ConvertSegment, Location, LocationPart
from kd_splicing.location.utils import (convert_location, union,
                                        get_alignment_segments, intersection,
                                        merge, relative_to_alignment,
                                        relative_to_location,
                                        symmetric_difference)


class UtilsTestCase(unittest.TestCase):
    def test_union(self) -> None:
        a = Location(parts=[
            LocationPart(start=0, end=3, strand=None),
            LocationPart(start=5, end=6, strand=None),
            LocationPart(start=9, end=11, strand=None),
            LocationPart(start=12, end=14, strand=None),
        ])
        b = Location(parts=[
            LocationPart(start=1, end=2, strand=None),
            LocationPart(start=4, end=7, strand=None),
            LocationPart(start=8, end=10, strand=None),
            LocationPart(start=13, end=15, strand=None),
        ])
        r = union(a, b)
        c = Location(parts=[
            LocationPart(start=0, end=1, strand=None, data={'source': {'a'}}),
            LocationPart(start=1, end=2, strand=None, data={'source': {'a', 'b'}}),
            LocationPart(start=2, end=3, strand=None, data={'source': {'a'}}),
            LocationPart(start=4, end=5, strand=None, data={'source': {'b'}}),
            LocationPart(start=5, end=6, strand=None, data={'source': {'a', 'b'}}),
            LocationPart(start=6, end=7, strand=None, data={'source': {'b'}}),
            LocationPart(start=8, end=9, strand=None, data={'source': {'b'}}),
            LocationPart(start=9, end=10, strand=None, data={'source': {'a', 'b'}}),
            LocationPart(start=10, end=11, strand=None, data={'source': {'a'}}),
            LocationPart(start=12, end=13, strand=None, data={'source': {'a'}}),
            LocationPart(start=13, end=14, strand=None, data={'source': {'a', 'b'}}),
            LocationPart(start=14, end=15, strand=None, data={'source': {'b'}})
         ])
        self.assertEqual(r, c)

    def test_symmetric_difference(self) -> None:
        a = Location(parts=[
            LocationPart(start=0, end=3, strand=None, data={"a_id": 0}),
            LocationPart(start=5, end=6, strand=None, data={"a_id": 1}),
            LocationPart(start=9, end=11, strand=None, data={"a_id": 2}),
            LocationPart(start=12, end=14, strand=None, data={"a_id": 3}),
        ])
        b = Location(parts=[
            LocationPart(start=1, end=2, strand=None, data={"b_id": 0}),
            LocationPart(start=4, end=7, strand=None, data={"b_id": 1}),
            LocationPart(start=8, end=10, strand=None, data={"b_id": 2}),
            LocationPart(start=13, end=15, strand=None, data={"b_id": 3}),
        ])
        r = symmetric_difference(a, b)
        c = Location(parts=[
            LocationPart(start=0, end=1, strand=None, data={"a_id": 0}),
            LocationPart(start=2, end=3, strand=None, data={"a_id": 0}),
            LocationPart(start=4, end=5, strand=None, data={"b_id": 1}),
            LocationPart(start=6, end=7, strand=None, data={"b_id": 1}),
            LocationPart(start=8, end=9, strand=None, data={"b_id": 2}),
            LocationPart(start=10, end=11, strand=None, data={"a_id": 2}),
            LocationPart(start=12, end=13, strand=None, data={"a_id": 3}),
            LocationPart(start=14, end=15, strand=None, data={"b_id": 3})
        ])
        self.assertEqual(r, c)

    def test_intersection(self) -> None:
        a = Location(parts=[
            LocationPart(start=0, end=3, strand=None, data={"a_id": 1}),
            LocationPart(start=5, end=6, strand=None, data={"a_id": 2}),
            LocationPart(start=9, end=11, strand=None, data={"a_id": 3}),
            LocationPart(start=12, end=14, strand=None, data={"a_id": 4}),
        ])
        b = Location(parts=[
            LocationPart(start=1, end=2, strand=None, data={"b_id": 1}),
            LocationPart(start=4, end=7, strand=None, data={"b_id": 2}),
            LocationPart(start=8, end=10, strand=None, data={"b_id": 3}),
            LocationPart(start=13, end=15, strand=None, data={"b_id": 4}),
        ])
        r = intersection(a, b)

        c = Location(parts=[
            LocationPart(start=1, end=2, strand=None,
                         data={'a_id': 1, 'b_id': 1}),
            LocationPart(start=5, end=6, strand=None,
                         data={'a_id': 2, 'b_id': 2}),
            LocationPart(start=9, end=10, strand=None,
                         data={'a_id': 3, 'b_id': 3}),
            LocationPart(start=13, end=14, strand=None,
                         data={'a_id': 4, 'b_id': 4})
        ])
        self.assertEqual(r, c)

    def test_get_alignment_segments_simple(self) -> None:
        segments = get_alignment_segments("SD", 1, 4)
        correct = [ConvertSegment(src_start=0, src_end=1, dst_start=-1),
                   ConvertSegment(src_start=1, src_end=4, dst_start=0)]
        self.assertEqual(correct, segments)

    def test_get_alignment_segments_simple2(self) -> None:
        segments = get_alignment_segments("SD-", 1, 5)
        correct = [ConvertSegment(src_start=0, src_end=1, dst_start=-1), ConvertSegment(
            src_start=1, src_end=3, dst_start=0), ConvertSegment(src_start=3, src_end=5, dst_start=3)]
        self.assertEqual(correct, segments)

    def test_get_alignment_segments(self) -> None:
        segments = get_alignment_segments("S-SD---KSD-", 3, 30)
        correct = [
            ConvertSegment(src_start=0, src_end=3, dst_start=-3),
            ConvertSegment(src_start=3, src_end=4, dst_start=0),
            ConvertSegment(src_start=4, src_end=6, dst_start=2),
            ConvertSegment(src_start=6, src_end=9, dst_start=7),
            ConvertSegment(src_start=9, src_end=30, dst_start=11)
        ]
        self.assertEqual(correct, segments)

    def test_convert_location_merge(self) -> None:
        segments = get_alignment_segments("S-SD---KSD-", 3, 30)
        loc = Location(parts=[
            LocationPart(start=0, end=1, strand=None),
            LocationPart(start=2, end=4, strand=None),
            LocationPart(start=5, end=7, strand=None),
            LocationPart(start=8, end=9, strand=None),
            LocationPart(start=11, end=13, strand=None),
        ])
        converted = convert_location(loc, segments)
        correct = Location(parts=[
            LocationPart(start=-3, end=-2, strand=None),
            LocationPart(start=-1, end=1, strand=None),
            LocationPart(start=3, end=4, strand=None),
            LocationPart(start=7, end=8, strand=None),
            LocationPart(start=9, end=10, strand=None),
            LocationPart(start=13, end=15, strand=None)
        ])
        self.assertEqual(converted, correct)

    def test_convert_location(self) -> None:
        segments = get_alignment_segments("S-SD---KSD-", 3, 30)
        loc = Location(parts=[
            LocationPart(start=0, end=1, strand=None, data={"id": 1}),
            LocationPart(start=2, end=4, strand=None, data={"id": 2}),
            LocationPart(start=5, end=7, strand=None, data={"id": 3}),
            LocationPart(start=8, end=9, strand=None, data={"id": 4}),
            LocationPart(start=11, end=13, strand=None, data={"id": 5}),
        ])
        converted = convert_location(loc, segments, merge=False)
        correct = Location(parts=[
            LocationPart(start=-3, end=-2, strand=None, data={'id': 1}),
            LocationPart(start=-1, end=0, strand=None, data={'id': 2}),
            LocationPart(start=0, end=1, strand=None, data={'id': 2}),
            LocationPart(start=3, end=4, strand=None, data={'id': 3}),
            LocationPart(start=7, end=8, strand=None, data={'id': 3}),
            LocationPart(start=9, end=10, strand=None, data={'id': 4}),
            LocationPart(start=13, end=15, strand=None, data={'id': 5})
        ])
        self.assertEqual(converted, correct)

    def test_convert_merge(self) -> None:
        loc = Location(parts=[
            LocationPart(start=0, end=1, strand=None, data={"id": 1}),
            LocationPart(start=1, end=2, strand=None, data={"id": 2}),
        ])
        merged = merge(loc)
        print(merged)
