import unittest

from kd_splicing.location.models import Location, LocationPart, ConvertSegment
from kd_splicing import as_type

class FeaturesTestCase(unittest.TestCase):

    def test_relative_to_location(self) -> None:
        query_iso_b = Location(parts=[LocationPart(start=12755136, end=12755239, strand=-1), LocationPart(start=12755309, end=12755375, strand=-1), LocationPart(start=12755453, end=12755605, strand=-1), LocationPart(start=12755689, end=12755782, strand=-1), LocationPart(start=12755930, end=12756046,
                                                                                                                                                                                                                                                                               strand=-1), LocationPart(start=12756143, end=12756193, strand=-1), LocationPart(start=12756301, end=12756456, strand=-1), LocationPart(start=12756538, end=12756566, strand=-1), LocationPart(start=12756743, end=12756934, strand=-1), LocationPart(start=12757550, end=12757653, strand=-1)])
        query_splicing = Location(parts=[
            LocationPart(start=12754727, end=12754866, strand=-1),
            LocationPart(start=12754944, end=12755048, strand=-1),
            LocationPart(start=12755136, end=12755140, strand=-1)])
        print(features.convert_splicing(query_splicing, query_iso_b, 348))
