from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from mobile_api import app


class MobileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_rna_tools_endpoint(self) -> None:
        response = self.client.post(
            "/rna_tools",
            json={
                "dna": "ATGCGTACGTACGTAGGCTAGGCTAGGCTAGGCTAGGCTAG",
                "start": 0,
                "end": 18,
                "max_codons": 4,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_codons"], 6)
        self.assertEqual(len(payload["rows"]), 4)

    def test_grnas_endpoint(self) -> None:
        response = self.client.post(
            "/grnas",
            json={
                "sequence": "ATGCGTACGTACGTAGGCTAGGCTAGGCTAGGCTAGGCTAG",
                "enzyme": "SpCas9",
                "scan_reverse": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["enzyme"], "SpCas9")
        self.assertIn("grnas", payload)


if __name__ == "__main__":
    unittest.main()
