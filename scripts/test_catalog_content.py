import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from catalog_content import apply_plan, digest, main


class CatalogContentTest(unittest.TestCase):
    def setUp(self):
        self.cols = ["Handle", "Title", "Body (HTML)", "Vendor", "Variant SKU", "Image Src", "Image Alt Text", "Produktmarke (product.metafields.custom.produktmarke)"]
        self.html = '<p>Pflege: 30 °C. <a href="/details">Maße</a></p>'
        self.rows = [["a", "Shirt", self.html, "Supplier", "sku1", "one", "old", ""],
                     ["a", "", "", "", "sku2", "two", "old", ""],
                     ["b", "Another product", self.html, "Supplier", "sku3", "", "", ""]]
        self.plan = {"products": {"a": {"body_sha256": digest(self.html), "introduction": "Motiv A & B",
                                 "brand": "FamilySurprise", "expected_brand": "",
                                 "images": {"two": {"expected_alt": "old", "alt": "Rückseite"}}}}}

    def test_apply_replay_and_protected_values(self):
        before = copy.deepcopy(self.rows)
        self.assertEqual(apply_plan(self.cols, self.rows, self.plan),
                         {"introductions": 1, "brands": 1, "image_captions": 1})
        self.assertEqual(self.rows[0][2], "<p>Motiv A &amp; B</p>\n" + self.html)
        self.assertEqual(self.rows[0][3:7], before[0][3:7])
        self.assertEqual(self.rows[1][:6], before[1][:6])
        self.assertEqual(self.rows[2], before[2])
        self.assertEqual(apply_plan(self.cols, self.rows, self.plan), {})
        self.plan["products"]["a"]["body_sha256"] = digest(self.rows[0][2])
        self.assertEqual(apply_plan(self.cols, self.rows, self.plan), {})

    def test_changed_input_or_ambiguous_image_refused(self):
        for field, value in [(2, self.html + " Neu"), (5, "two"), (7, "Different")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                rows = copy.deepcopy(self.rows)
                rows[0][field] = value
                apply_plan(self.cols, rows, self.plan)

    def test_verify_rejects_brand_in_title_column(self):
        candidate = copy.deepcopy(self.rows)
        apply_plan(self.cols, candidate, self.plan)
        candidate[0][self.cols.index("Title")] = "FamilySurprise"
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source, changed, plan = (directory / name for name in ("source.csv", "changed.csv", "plan.json"))
            for path, rows in ((source, self.rows), (changed, candidate)):
                with path.open("w", encoding="utf-8", newline="") as stream:
                    csv.writer(stream).writerows([self.cols, *rows])
            plan.write_text(json.dumps(self.plan), encoding="utf-8")
            with patch("sys.argv", ["catalog_content", str(source), str(plan), "--verify", str(changed)]):
                with self.assertRaisesRegex(ValueError, "unrelated edits"):
                    main()

    def test_current_format_marks_new_and_migrated_introductions_without_changing_original(self):
        legacy_rows = copy.deepcopy(self.rows)
        apply_plan(self.cols, legacy_rows, self.plan)
        self.plan["version"] = 2
        apply_plan(self.cols, self.rows, self.plan)
        expected = '<p class="fs-product-intro">Motiv A &amp; B</p>\n' + self.html
        self.assertEqual(self.rows[0][2], expected)
        self.assertEqual(apply_plan(self.cols, legacy_rows, self.plan), {"marked_existing_introductions": 1})
        self.assertEqual(legacy_rows, self.rows)
        self.assertEqual(apply_plan(self.cols, self.rows, self.plan), {})

    def test_unknown_fields_and_missing_product_refused(self):
        for plan in ({"products": {"a": {"Vendor": "Other"}}}, {"products": {"gone": {"brand": "x"}}}):
            with self.assertRaises(ValueError):
                apply_plan(self.cols, self.rows, plan)


if __name__ == "__main__":
    unittest.main()
