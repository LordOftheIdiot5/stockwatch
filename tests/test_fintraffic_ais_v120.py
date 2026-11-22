"""Regression tests for the V120 Fintraffic AIS private integration pilot."""
import copy
import unittest

from scripts import fintraffic_ais_v120 as ais

NOW = 1795389400000
MMSI = 230949000

POSITION = {
    "type": "Feature", "mmsi": MMSI,
    "geometry": {"type": "Point", "coordinates": [28.927335, 61.856277]},
    "properties": {
        "mmsi": MMSI, "sog": 0.0, "cog": 187.6,
        "navStat": 5, "heading": 302, "timestamp": 35,
        "timestampExternal": 1795389336737
    }
}
META = {
    "mmsi": MMSI, "name": "HELGA", "destination": "SAVONLINNA",
    "shipType": 70, "timestamp": 1795389368174
}


class FintrafficAisTests(unittest.TestCase):
    def test_real_response_shape_has_explicit_provenance_and_is_not_live_track(self):
        result = ais.snapshot(
            {"type": "FeatureCollection", "features": [POSITION]}, META, MMSI, NOW
        )
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["provider"], "Fintraffic Digitraffic")
        self.assertEqual(result["license"], "CC BY 4.0")
        self.assertIn("digitraffic.fi", result["attribution"])
        self.assertIn("NOT continuous live tracking", result["kind"])
        self.assertEqual(result["redistributionState"], "private_integration_pilot_not_published")
        self.assertEqual(len(result["positions"]), 1)
        row = result["positions"][0]
        self.assertEqual(row["mmsi"], MMSI)
        self.assertEqual(row["name"], "HELGA")
        self.assertEqual(row["destinationAisReported"], "SAVONLINNA")
        self.assertEqual(row["latitude"], 61.856277)
        self.assertEqual(row["longitude"], 28.927335)
        self.assertEqual(row["speedKnots"], 0)
        self.assertEqual(row["positionReportedAt"], "2026-11-22T23:15:36Z")
        self.assertEqual(row["metadataReportedAt"], "2026-11-22T23:16:08Z")
        self.assertNotIn("etaPredicted", row)
        self.assertNotIn("company", row)

    def test_stale_position_is_omitted_not_labelled_current(self):
        f = copy.deepcopy(POSITION)
        f["properties"]["timestampExternal"] = NOW - ais.MAX_POSITION_AGE_MS - 1
        self.assertIsNone(ais.normalize(f, META, NOW))
        result = ais.snapshot({"type": "FeatureCollection", "features": [f]}, META, MMSI, NOW)
        self.assertEqual(result["positions"], [])
        self.assertEqual(result["reason"], "no_fresh_verified_position")

    def test_future_time_and_ais_second_of_minute_cannot_be_accepted(self):
        f = copy.deepcopy(POSITION)
        f["properties"]["timestampExternal"] = NOW + ais.FUTURE_TOLERANCE_MS + 1
        self.assertIsNone(ais.normalize(f, META, NOW))
        f["properties"]["timestampExternal"] = f["properties"]["timestamp"]
        self.assertIsNone(ais.normalize(f, META, NOW))

    def test_invalid_geo_and_mismatched_mmsi_rejected(self):
        for coords in ([181, 0], [20, -92], ["nan", 5], [False, 5], [], None):
            f = copy.deepcopy(POSITION)
            f["geometry"]["coordinates"] = coords
            self.assertIsNone(ais.normalize(f, META, NOW), coords)
        f = copy.deepcopy(POSITION)
        f["mmsi"] = 230949001
        self.assertIsNone(ais.normalize(f, META, NOW))
        f = copy.deepcopy(POSITION)
        f["properties"]["mmsi"] = 0
        self.assertIsNone(ais.normalize(f, META, NOW))

    def test_unavailable_ais_speed_course_and_heading_not_faked(self):
        f = copy.deepcopy(POSITION)
        f["properties"].update(sog=102.3, cog=360, heading=511)
        result = ais.normalize(f, META, NOW)
        self.assertIsNone(result["speedKnots"])
        self.assertIsNone(result["courseDegrees"])
        self.assertIsNone(result["headingDegrees"])

    def test_missing_or_mismatched_vessel_metadata_never_invents_name_destination(self):
        for meta in (None, {"mmsi": 230949001, "name": "WRONG"}, {}):
            result = ais.normalize(POSITION, meta, NOW)
            self.assertIsNone(result["name"])
            self.assertIsNone(result["destinationAisReported"])
            self.assertIsNone(result["metadataReportedAt"])

    def test_duplicate_positions_select_latest_genuine_report(self):
        older = copy.deepcopy(POSITION)
        older["properties"]["timestampExternal"] -= 10000
        newer = copy.deepcopy(POSITION)
        newer["properties"]["timestampExternal"] += 10000
        r = ais.snapshot(
            {"type": "FeatureCollection", "features": [older, newer, POSITION]},
            META, MMSI, NOW
        )
        self.assertEqual(len(r["positions"]), 1)
        self.assertEqual(r["positions"][0]["positionReportedAt"], "2026-11-22T23:15:46Z")

    def test_malformed_oversized_and_other_vessel_inputs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid_mmsi"):
            ais.snapshot({"type": "FeatureCollection", "features": []}, META, 123, NOW)
        with self.assertRaisesRegex(ValueError, "invalid_fintraffic_payload"):
            ais.snapshot({"type": "Collection", "features": []}, META, MMSI, NOW)
        with self.assertRaisesRegex(ValueError, "invalid_fintraffic_features"):
            ais.snapshot({"type": "FeatureCollection", "features": "not a list"}, META, MMSI, NOW)
        different = copy.deepcopy(POSITION)
        different["mmsi"] = 230949001
        different["properties"]["mmsi"] = 230949001
        result = ais.snapshot({"type": "FeatureCollection", "features": [different]}, META, MMSI, NOW)
        self.assertEqual(result["positions"], [])

    def test_fetch_only_allowlisted_provider(self):
        with self.assertRaisesRegex(ValueError, "non_allowlisted_api"):
            ais.fetch_json("https://example.org/api/ais/v1/locations")
        self.assertEqual(ais.mmsi_number("230949000"), MMSI)
        self.assertIsNone(ais.mmsi_number("000000000"))
        self.assertIsNone(ais.mmsi_number("230949000.0"))


if __name__ == "__main__":
    unittest.main()
