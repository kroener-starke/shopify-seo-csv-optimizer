import unittest

from teeinblue_caption_plan import prepare


class SourceCaptionTest(unittest.TestCase):
    def test_shared_and_missing_old_values_need_an_exact_image_match(self):
        columns = ["Handle", "Title", "Image Src", "Image Alt Text", "product.metafields.teeinblue.campaign_version"]
        before = [["a", "Shirt", "one", "generic", "1"], ["a", "", "two", "generic", ""],
                  ["a", "", "three", "", ""], ["a", "", "four", "back.webp", ""],
                  ["b", "Ordinary product", "five", "unrelated", ""]]
        after = [row[:] for row in before]
        for index, caption in [(0, "Vorne"), (2, "Details"), (3, "Rückseite"), (4, "Neues Foto")]:
            after[index][3] = caption
        output = prepare((columns, before), (columns, after))["products"]
        self.assertEqual(set(output), {"a"})
        self.assertEqual(output["a"]["by_previous_caption"], {"back.webp": "Rückseite"})
        self.assertEqual(output["a"]["needs_media_match"], ["one", "three"])
        after[0][2] = "other"
        with self.assertRaisesRegex(ValueError, "association changed"):
            prepare((columns, before), (columns, after))
