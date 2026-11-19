import csv
import tempfile
import unittest
from pathlib import Path

from shopify_csv_guard import audit_data, weak_alt_text_reason


class AltReviewTest(unittest.TestCase):
    def test_review_queue_covers_existing_files_only_and_preserves_source_identity(self):
        original = [
            ("shirt", "Shirt", "hero.webp", "06-salbeigruen-mann-32-hinten"),
            ("shirt", "", "back.webp", "6854"),
            ("shirt", "", "size.webp", "Größentabelle für das Unisex-T-Shirt"),
            ("shirt", "", "", "6854"),
            ("cap", "Kappe", "cap.webp", ""),
            ("cap", "", "front.webp", "FamilySurprise_Cap_2"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "products.csv"
            with file.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Handle", "Title", "Image Src", "Image Alt Text"])
                writer.writerows(original)
            before = file.read_bytes()
            result = audit_data(file)
            self.assertEqual(file.read_bytes(), before)
        rows = result["image_alt_review"]
        self.assertEqual([r["row"] for r in rows], [2, 3, 6, 7])
        self.assertEqual(rows[0]["current_alt"], original[0][3])
        self.assertEqual(rows[0]["url"], original[0][2])
        self.assertEqual(rows[-1]["handle"], "cap")

    def test_screenshot_names_and_one_word_colors_are_reviewed(self):
        for text in ("ChatGPT Image 4. Juni 2026, 21_03_45", "schwarz", "DDA8D96B-C73D-4385-9E83-BE0FA726BD5D", "entwurf.AVIF"):
            with self.subTest(text=text):
                self.assertTrue(weak_alt_text_reason(text))
        self.assertEqual(weak_alt_text_reason("Schwarzes T-Shirt mit Borrachos-Motiv"), "")


if __name__ == "__main__":
    unittest.main()
