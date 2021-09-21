import unittest

from pprint import PrettyPrinter, pprint
from kd_splicing.location.models import Location, LocationPart, ConvertSegment
from kd_splicing import as_type


class AsTypeTestCase(unittest.TestCase):

    def test_ir(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1),
                LocationPart(2, 3),
            ]),
            Location([
                LocationPart(0, 3),
            ]),
        )
        self.assertEqual(as_types, (("IR", ),))

    def test_altd(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1),
                LocationPart(3, 4),
            ]),
            Location([
                LocationPart(0, 2),
                LocationPart(3, 4),
            ]),
        )
        self.assertEqual(as_types, (("AltD", ),))

    def test_alta(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1),
                LocationPart(3, 4),
            ]),
            Location([
                LocationPart(0, 1),
                LocationPart(2, 4),
            ]),
        )
        self.assertEqual(as_types, (("AltA", ),))

    def test_exs(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1),
                LocationPart(4, 5),
            ]),
            Location([
                LocationPart(0, 1),
                LocationPart(2, 3),
                LocationPart(4, 5),
            ]),
        )
        self.assertEqual(as_types, (("ExS", ),))

    def test_altd_exs_alta(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1),
                LocationPart(10, 11),
            ]),
            Location([
                LocationPart(0, 2),
                LocationPart(4, 5),
                LocationPart(9, 11),
            ]),
        )
        self.assertEqual(as_types, (("AltD", "ExS", "AltA"),))


    def test_reverse_ir(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1, -1),
                LocationPart(2, 3, -1),
            ]),
            Location([
                LocationPart(0, 3, -1),
            ]),
        )
        self.assertEqual(as_types, (("IR", ),))

    def test_reverse_alta(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1, -1),
                LocationPart(3, 4, -1),
            ]),
            Location([
                LocationPart(0, 2, -1),
                LocationPart(3, 4, -1),
            ]),
        )
        self.assertEqual(as_types, (("AltA", ),))

    def test_reverse_altd(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1, -1),
                LocationPart(3, 4, -1),
            ]),
            Location([
                LocationPart(0, 1, -1),
                LocationPart(2, 4, -1),
            ]),
        )
        self.assertEqual(as_types, (("AltD", ),))

    def test_reverse_exs(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1, -1),
                LocationPart(4, 5, -1),
            ]),
            Location([
                LocationPart(0, 1, -1),
                LocationPart(2, 3, -1),
                LocationPart(4, 5, -1),
            ]),
        )
        self.assertEqual(as_types, (("ExS", ),))

    def test_reverse_ir_source_parts(self) -> None:
        as_types = as_type.get_as_types(
            Location([
                LocationPart(0, 1, -1),
                LocationPart(2, 3, -1),
            ]),
            Location([
                LocationPart(0, 3, -1),
            ]),
            source_parts=True,
        )
        self.assertEqual(as_types, ((('IR', 'b_0'),),))

if __name__ == "__main__":
    AsTypeTestCase().test_reverse_ir_source_parts()