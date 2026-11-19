# Product introductions, public brand and current image captions

Start with a fresh complete export. The audit compares one visible description per product, groups identical text, and finds substantial near matches of at least 20 words using four-word sequences with 85% overlap. It also compares the body below a first paragraph to catch newly added copies of an already optimized product. A partial export only compares products in that file. Read each flagged pair and check the opening against the actual product. Shared care instructions can coexist with a distinct introduction. If the existing opening already describes this product well, skip it. When a copied opening describes a different product, flag that factual conflict for correction before applying an introduction. For each remaining candidate with enough evidence, write a natural German introduction using verified details about its design, customer, occasion or personalization options. Compare siblings side by side. A repeated template with the title inserted rarely tells a shopper what makes this product different. Keep existing specifications, safety information, personalization instructions, links and formatted copy after the introduction. Leave distinctive descriptions alone unless the brief also covers them.

Use the dedicated `product.metafields.custom.produktmarke` export column for the public brand when that assignment is accurate and approved. Keep the fulfillment vendor in its existing field. The theme and each sales channel consume their own brand mapping.

For media, run the audit with JSON output and review its `image_alt_review` rows, including extensionless filenames, numeric IDs and single-word colors. Check descriptive-looking captions against the photos in their product gallery when needed. The flags are review candidates. Reconcile the current URL, product association and alt text. Inspect the image when a visual detail is uncertain. Historical alt text can help identify a design after a re-upload, but recycled filenames and image positions can belong to different photos. Record the current media ID for a live update. If a personalization app recreates photos, also check its source mockup and verify the next sync preserves the caption.

For products published through Teeinblue, also prepare the source caption plan using `scripts/teeinblue_caption_plan.py original.csv validated.csv --output source-captions.json`. The command accounts for unchanged photos sharing the old caption and lists ambiguous images for identification. A file-only run can deliver this plan without writing to any service.

For an authorized live rollout, apply the plan using the merchant's existing signed-in Teeinblue editor. The skill can perform this step. Open the campaign from the merchant's own listing and confirm the Shopify product link. Load `scripts/teeinblue_mockups.mjs` in the browser-controlling runtime. Pass its `syncOpenCampaign` function the open tab and an options object with the verified `handle`, `campaignPath`, authorized `shopHosts` and the corresponding product entry from `source-captions.json`. Start with `write: false`; then use `write: true` for the authorized changes. The helper checks each selected product base, source URL and mockup ID, edits the alt text and reads it back after reloading. It never presses the campaign’s Update button. A matched source edit can be retried from a freshly opened campaign.

When an old caption is missing or ambiguous, identify the exact native mockup and matching Shopify media. Supply `matches[basePath][mockupID] = {shopifyUrl, sourceUrl}` only after verifying that association. Keep an unresolved image for follow-up when the two images cannot be matched. Teeinblue’s thumbnail captions can also come from the product base name. The FamilySurprise theme uses the approved Shopify caption for thumbnails whose upload ID matches the current product’s original photo. Verify a photo of the product and a size chart separately when a gallery has both.

If the campaign name, the printed design and the proposed caption disagree, open the original mockup and the published Shopify photo side by side. A mockup can be an undecorated background with the artwork applied later. For a caption shared between the two, describe what both images actually show. Use the product view or setting to distinguish photos. For example, a white money box can be shown on a wooden surface in one image and against a white background in another. After an interrupted save, reload the campaign and compare the current caption before trying again.

The skill authors the wording and builds the plan. The Python audit itself reports candidates. A run updates a separate CSV, and publishing changes to Shopify is a separate action.

Create a JSON plan keyed by the exact current handle. Each product can contain any combination of the three kinds of edit shown below. Obtain the lowercase SHA-256 digest from the UTF-8 bytes of the original description cell.

```json
{
  "version": 3,
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

Use version 3 for FamilySurprise. A fresh CSV includes the product metafield ending in `(product.metafields.custom.produkteinleitung)`. The tool saves the approved wording there and at the start of the normal description. If the current export omits the column, export the products with this metafield included. When the audit reports “restore saved product introduction”, check the text still describes this product, use that saved wording as the introduction, and take the body hash from the fresh export. This restores the opening for services that read the normal Shopify description. An unexpected difference between a saved field and a marked opening needs editorial review.

The opening paragraph carries the `fs-product-intro` class so the FamilySurprise personalization form can show it above the selected product base’s specifications. The tool can mark a previously applied plain paragraph if its exact text and the original remainder match the plan. Older plans still reproduce their original files. Version 2 uses the marked paragraph alone for exports that predate the dedicated field.

When a newly duplicated listing has inherited another design’s marked introduction, check the two products and identify which opening needs rewriting. On that listing’s plan entry, include the exact old text in `previous_introduction`, the replacement in `introduction` and the hash of the full current body in `body_sha256`. The tool replaces that opening once. It preserves every character after it and rejects an unexpected edit. The same plan can be reapplied safely. A shared heading such as “Hochwertiger Baumwollbeutel” can remain below a suitable individual opening when it describes the correct product.

For a live check, compare the expected paragraph from the plan with the visible first paragraph in the launched storefront. On a personalized item, wait for the Teeinblue form and verify the opening occurs once in its visible description. Open a partner product, an ordinary product and a product with switchable bases. Check a direct variant link and the mobile layout. When a campaign update includes the Shopify description or recreates photos, repeat the check against the saved plan after the update; a CSV export alone cannot show what the app presents to the shopper.

The command prepends an escaped paragraph and checks the original body, caption and brand. A second run of the same plan accepts already-applied values. Verification recomputes every cell, including protected fields and untouched products.

For a file intended for re-import, choose Shopify’s **Plain CSV file** export. The spreadsheet export can add an apostrophe before a numeric option value. FamilySurprise’s sandals, for example, have a size called `47`. Check the Shopify import preview for the actual options, variants and prices. If a product with priced size variants previews as a free default variant, cancel the import and use the field-specific admin workflow. Keep the fresh export’s original options and variants.

For a live rollout, use current product and media IDs and write only the fields named in the plan. A bulk grid can send an edit to a different column when focus moves. Use a field-specific action for catalog-wide changes. After saving, compare every original product title by ID, then verify variant IDs, options, prices, SKUs, supplier values and image associations against the export. Look up the saved brand metafield on each product as well. A storefront fallback can display the expected brand even when the stored field is empty.

Check the rendered Product or ProductGroup structured data and each channel’s brand mapping. Check Shopify channel publication and the receiving catalog’s acceptance separately.
