# Product introductions, public brand and current image captions

Start with a fresh Shopify export. Group similar descriptions after removing HTML formatting. For each product, write a natural German introduction using verified details about its design, customer, occasion or personalization options. Compare siblings side by side. A repeated template with the title inserted rarely tells a shopper what makes this product different. Keep existing specifications, safety information, personalization instructions, links and formatted copy after the introduction. Leave distinctive descriptions alone unless the brief also covers them.

Use the dedicated `product.metafields.custom.produktmarke` export column for the public brand when that assignment is accurate and approved. Keep the fulfillment vendor in its existing field. The theme and each sales channel consume their own brand mapping.

For media, run the audit with JSON output and review its `image_alt_review` rows, including extensionless filenames, numeric IDs and single-word colors. Check descriptive-looking captions against the photos in their product gallery when needed. The flags are review candidates. Reconcile the current URL, product association and alt text. Inspect the image when a visual detail is uncertain. Historical alt text can help identify a design after a re-upload, but recycled filenames and image positions can belong to different photos. Record the current media ID for a live update. If a personalization app recreates photos, also check its source mockup and verify the next sync preserves the caption.

Create a JSON plan keyed by the exact current handle. Each product can contain any combination of the three kinds of edit shown below. Obtain the lowercase SHA-256 digest from the UTF-8 bytes of the original description cell.

```json
{
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

The command prepends an escaped paragraph and checks the original body, caption and brand. A second run of the same plan accepts already-applied values. Verification recomputes every cell, including protected fields and untouched products.

Check the Shopify import preview for the actual options, variants and prices. If a product with priced size variants previews as a free default variant, cancel the import and edit those existing records through the admin.

For a live rollout, use current product and media IDs and write only the fields named in the plan. A bulk grid can send an edit to a different column when focus moves. Use a field-specific action for catalog-wide changes. After saving, compare every original product title by ID, then verify variant IDs, options, prices, SKUs, supplier values and image associations against the export. Look up the saved brand metafield on each product as well. A storefront fallback can display the expected brand even when the stored field is empty.

Check the rendered Product or ProductGroup structured data and each channel’s brand mapping. Check Shopify channel publication and the receiving catalog’s acceptance separately.
