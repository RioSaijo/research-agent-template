import unittest

from code.integration.semantic_ieq_features import assemble_room_features, mapping_coverage


class SemanticFeatureAssemblyTests(unittest.TestCase):
    def test_graph_context_is_joined_without_target_use(self):
        triples = [
            ("sensor-co2-1", "isPointOf", "room-101"),
            ("room-101", "isPartOf", "ahu-zone-a"),
        ]
        rows = [{"sensor_id": "sensor-co2-1", "co2_ppm": 780.0}]
        result = assemble_room_features(rows, triples)
        self.assertEqual(result[0]["semantic_room"], "room-101")
        self.assertEqual(result[0]["semantic_hvac_zone"], "ahu-zone-a")
        self.assertEqual(mapping_coverage(result), 1.0)

    def test_missing_semantics_remain_visible(self):
        result = assemble_room_features([{"sensor_id": "unknown", "co2_ppm": 900.0}], [])
        self.assertEqual(result[0]["semantic_room"], "UNKNOWN")
        self.assertEqual(result[0]["semantic_mapping_complete"], 0)
        self.assertEqual(mapping_coverage(result), 0.0)


if __name__ == "__main__":
    unittest.main()

