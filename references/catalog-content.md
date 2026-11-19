# Product introductions, public brand and current image captions

Start with a fresh complete export. The audit compares one visible description per product, groups identical text, and finds substantial near matches of at least 20 words using four-word sequences with 85% overlap. It also compares the body below a first paragraph to catch newly added copies of an already optimized product. A partial export only compares products in that file. Read each flagged pair and check the opening against the actual product. Shared care instructions can coexist with a distinct introduction. If the existing opening already describes this product well, skip it. When a copied opening describes a different product, flag that factual conflict for correction before applying an introduction. For each remaining candidate with enough evidence, write a natural German introduction using verified details about its design, customer, occasion or personalization options. Compare siblings side by side. A repeated template with the title inserted rarely tells a shopper what makes this product different. Keep existing specifications, safety information, personalization instructions, links and formatted copy after the introduction. Leave distinctive descriptions alone unless the brief also covers them.

Use the dedicated `product.metafields.custom.produktmarke` export column for the public brand when that assignment is accurate and approved. Keep the fulfillment vendor in its existing field. The theme and each sales channel consume their own brand mapping.

For media, run the audit with JSON output and review its `image_alt_review` rows, including extensionless filenames, numeric IDs and single-word colors. Check descriptive-looking captions against the photos in their product gallery when needed. The flags are review candidates. Reconcile the current URL, product association and alt text. Inspect the image when a visual detail is uncertain. Historical alt text can help identify a design after a re-upload, but recycled filenames and image positions can belong to different photos. Record the current media ID for a live update. If a personalization app recreates photos, also check its source mockup and verify the next sync preserves the caption.

The skill authors the wording and builds the plan. The Python audit itself reports candidates. A run updates a separate CSV, and publishing changes to Shopify is a separate action.

Create a JSON plan keyed by the exact current handle. Each product can contain any combination of the three kinds of edit shown below. Obtain the lowercase SHA-256 digest from the UTF-8 bytes of the original description cell.

```json
{
  "version": 2,
  "products": {
    "example-handle": {
      "body_sha256": "<sha256 of the exact original cell>",
      "introduction": "Das Poster verbindet euer Foto mit der Definition von Papa.",
      "expected_brand": "",
      "brand": "FamilySurprise",
      "images": {
        "<current image URL from this export>": {
          "expected_alt": "<current alt, or an empty string>",
          "alt": "Schwarzes T-Shirt mit Borrachos-Motiv"
        }
      }
    }
  }
}
```

```sh
python3 scripts/catalog_content.py current.csv plan.json --output improved.csv
python3 scripts/catalog_content.py current.csv plan.json --verify improved.csv
```

For a run that also edits SEO titles or meta descriptions, create that intermediate CSV first and validate it against the export with `shopify_csv_guard.py validate original.csv seo.csv --allowed "SEO Title,SEO Description"`. Use the validated intermediate as the source for both content commands above. Re-audit the final file and review any remaining matches inside the requested scope.

Use version 2 for new plans. The opening paragraph carries the `fs-product-intro` class so the FamilySurprise personalization form can show it above the selected product base’s specifications. The tool can mark a previously applied plain paragraph if its exact text and the original remainder match the plan. Older plans still reproduce their original file. Verify the visible text in an actual browser after the personalizer loads, including a switch between product bases with different specifications.

The command prepends an escaped paragraph and checks the original body, caption and brand. A second run of the same plan accepts already-applied values. Verification recomputes every cell, including protected fields and untouched products.

Check the Shopify import preview for the actual options, variants and prices. If a product with priced size variants previews as a free default variant, cancel the import and edit those existing records through the admin.

For a live rollout, use current product and media IDs and write only the fields named in the plan. A bulk grid can send an edit to a different column when focus moves. Use a field-specific action for catalog-wide changes. After saving, compare every original product title by ID, then verify variant IDs, options, prices, SKUs, supplier values and image associations against the export. Look up the saved brand metafield on each product as well. A storefront fallback can display the expected brand even when the stored field is empty.

Check the rendered Product or ProductGroup structured data and each channel’s brand mapping. Check Shopify channel publication and the receiving catalog’s acceptance separately.
