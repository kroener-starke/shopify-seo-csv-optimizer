import copy
import unittest

from catalog_content import apply_plan, digest


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

    def test_changed_input_or_ambiguous_image_refused(self):
        for field, value in [(2, self.html + " Neu"), (5, "two"), (7, "Different")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                rows = copy.deepcopy(self.rows)
                rows[0][field] = value
                apply_plan(self.cols, rows, self.plan)

    def test_unknown_fields_and_missing_product_refused(self):
        for plan in ({"products": {"a": {"Vendor": "Other"}}}, {"products": {"gone": {"brand": "x"}}}):
            with self.assertRaises(ValueError):
                apply_plan(self.cols, self.rows, plan)


if __name__ == "__main__":
    unittest.main()
