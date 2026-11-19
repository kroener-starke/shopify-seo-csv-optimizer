import csv
import tempfile
import unittest
from pathlib import Path

from catalog_content import apply_plan, digest
from description_review import review_descriptions
from shopify_csv_guard import audit_data, render_audit_markdown


class DescriptionReviewTest(unittest.TestCase):
    def setUp(self):
        self.body = '<h3>Unisex T-Shirt</h3><p>Details zum Schnitt &amp; zur Pflege.</p>'
        self.cols = ["Handle", "Title", "Body (HTML)", "Variant SKU", "Status"]
        self.rows = [["rost", "Shirt mit Rost-Motiv", self.body, "S1", "active"],
                     ["rost", "", "", "S2", ""],
                     ["strom", "Shirt mit Steckdosen-Motiv", self.body, "S3", "active"]]

    def audit(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "export.csv"
            with source.open("w", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerows([self.cols, *self.rows])
            result = audit_data(source)
            self.assertIn("Product descriptions to compare", render_audit_markdown(result))
            return result["description_review"]

    def test_fresh_export_repeat_and_new_product(self):
        before = self.audit()
        self.assertEqual(before["exact_groups"], [["rost", "strom"]])
        self.assertEqual(len(before["review"]), 2)
        intros = {"rost": "Der Oldtimer trägt seine Rostspuren mit Stolz.",
                  "strom": "Auf diesem Shirt wird die Steckdose zum Schrauberwitz."}
        plan = {"products": {h: {"introduction": text, "body_sha256": digest(self.body)}
                             for h, text in intros.items()}}
        self.assertEqual(apply_plan(self.cols, self.rows, plan), {"introductions": 2})
        self.assertEqual(self.audit()["review"], [])
        self.rows.append(["neu", "Neues Schraubermotiv", self.body, "S4", "active"])
        fresh = self.audit()
        self.assertEqual([row["handle"] for row in fresh["review"]], ["neu"])
        self.assertEqual(fresh["distinct_openings_on_shared_copy"], ["rost", "strom"])
        self.assertTrue(self.rows[0][2].endswith(self.body))
        self.assertEqual(self.rows[1][2], "")

    def test_visible_text_only_and_status_preserved_for_scope_selection(self):
        self.rows[0][2] = '<div>Té&eacute; &amp; Tee</div><style>green</style>'
        self.rows[2][2] = '<p>Téé   &amp; <b>T</b>ee</p><script>javascript</script>'
        self.rows[2][-1] = "draft"
        self.rows.append(["empty", "Leeres Produkt", "<p>&nbsp;</p>", "", "active"])
        result = self.audit()
        self.assertEqual(result["exact_groups"], [["rost", "strom"]])
        self.assertEqual(result["empty"], ["empty"])

    def test_near_copies_and_unrelated_shared_small_print(self):
        prose = " ".join("wort" + str(i) for i in range(100))
        groups = [("one", prose), ("two", prose.replace("wort50 ", "anders ")),
                  ("other", "Dieses Modell zeigt eine Wiese voller Blumen. " * 15 + prose[:35])]
        rows = [{"URL handle": h, "Description": body} for h, body in groups]
        review = review_descriptions(rows)["review"]
        self.assertEqual([r["handle"] for r in review], ["one", "two"])
        self.assertTrue(all(r["four_word_jaccard"] >= .85 for r in review))
        self.assertEqual(review_descriptions(rows[:1])["review"], [])

    def test_familysurprise_field_survives_republication_and_recovers_the_body(self):
        field = "Produkteinleitung (product.metafields.custom.produkteinleitung)"
        self.cols.append(field)
        for row in self.rows:
            row.append("")
        text = "Das Rostmotiv passt zu Fans alter Fahrzeuge."
        plan = {"version": 3, "products": {"rost": {"introduction": text, "body_sha256": digest(self.body)}}}
        self.assertEqual(apply_plan(self.cols, self.rows, plan), {"introductions": 1, "saved_introduction_fields": 1})
        complete = self.rows[0][2]
        self.assertEqual(self.rows[0][-1], text)
        self.assertEqual(apply_plan(self.cols, self.rows, plan), {})
        self.rows[0][2] = self.body
        finding = next(r for r in self.audit()["review"] if r["handle"] == "rost")
        self.assertEqual(finding["reason"], "restore saved product introduction")
        self.assertEqual(apply_plan(self.cols, self.rows, plan), {"introductions": 1})
        self.assertEqual(self.rows[0][2], complete)
        self.rows[0][-1] = "Ein unabhängig bearbeiteter Text."
        with self.assertRaisesRegex(ValueError, "saved product introduction has changed"):
            apply_plan(self.cols, self.rows, plan)
