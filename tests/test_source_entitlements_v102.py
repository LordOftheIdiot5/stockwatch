"""V102 entitlement inventory is deny-by-default and cannot claim a grant by implication."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import source_entitlements_v102 as ent


class SourceEntitlementsV102Tests(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(ent.load())

    def test_real_inventory_is_review_only(self):
        self.assertEqual(self.data["schemaVersion"], 1)
        self.assertEqual(len(self.data["sources"]), 6)
        for source in self.data["sources"]:
            self.assertFalse(any(source["permissions"].values()), source["id"])
            self.assertIsNone(source["authorization"])
            self.assertTrue(source["policyUrl"].startswith("https://"))

    def test_production_capabilities_deny_without_scoped_evidence(self):
        for source in self.data["sources"]:
            for capability in ent.CAPABILITIES:
                with self.assertRaises(PermissionError):
                    ent.require_permission(source["id"], capability, self.data)
        with self.assertRaises(PermissionError):
            ent.require_permission("not-in-inventory", "publicDisplay", self.data)

    def test_unknown_capability_and_bad_source_fail_closed(self):
        with self.assertRaises(ent.EntitlementError):
            ent.require_permission("cboe_europe_eod", "distributeAnyPrice", self.data)
        self.data["sources"][1]["id"] = self.data["sources"][0]["id"]
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)

    def test_incomplete_matrix_and_http_source_rejected(self):
        target = self.data["sources"][0]
        target["permissions"].pop("commercialExport")
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)
        target["permissions"]["commercialExport"] = False
        target["policyUrl"] = "http://untrusted.example"
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)

    def test_granted_flag_without_source_specific_evidence_rejected(self):
        target = self.data["sources"][0]
        target["permissions"]["publicDisplay"] = True
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)
        target["authorization"] = {
            "evidenceRef": "unit-test-only",
            "scope": "Synthetic local unit test",
            "reviewer": "test",
            "reviewedOn": "2026-11-21",
            "sourceId": target["id"],
            "product": target["product"],
            "capabilities": ["privateRetention"],
        }
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)

    def test_scoped_evidence_is_capability_specific(self):
        target = self.data["sources"][0]
        target["permissions"]["privateRetention"] = True
        target["authorization"] = {
            "evidenceRef": "SYNTHETIC-TEST-NOT-A-LICENCE",
            "scope": "Synthetic test fixture only",
            "reviewer": "test",
            "reviewedOn": "2026-11-21",
            "sourceId": target["id"],
            "product": target["product"],
            "capabilities": ["privateRetention"],
        }
        self.assertEqual(ent.require_permission(target["id"], "privateRetention", self.data)["id"], target["id"])
        with self.assertRaises(PermissionError):
            ent.require_permission(target["id"], "publicDisplay", self.data)
        target["authorization"]["sourceId"] = "unrelated"
        with self.assertRaises(ent.EntitlementError):
            ent.validate(self.data)


if __name__ == "__main__":
    unittest.main()
