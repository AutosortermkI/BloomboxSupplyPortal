# PDF Adapter Activation Guide

## Overview

Three new PDF scraper adapters have been built and registered:
- **Hoffman Nursery (SID 111)**
- **Mountain Spring Nursery (SID 121)**  
- **Go Native Trees (SID 130)**

They are currently in "dormant" mode with empty `pdf_urls` lists. Once you obtain the actual PDF download URLs from the suppliers, activation is simple.

## Step 1: Obtain PDF URLs

Contact each supplier or find publicly accessible price list PDFs:

### Hoffman Nursery (SID 111)
- **Company:** Hoffman Nursery, Rougemont, NC
- **Phone:** (from index.html: check if available)
- **Website:** hoffmannursery.com (Cloudflare protected)
- **Action:** Email sales team requesting wholesale price list PDF

### Mountain Spring Nursery (SID 121)
- **Company:** Mountain Spring Nursery, Reinholds, PA
- **Phone:** 717-354-7789
- **Website:** mountainspringnursery.com
- **Action:** Contact via phone or email about downloadable catalog

### Go Native Trees (SID 130)
- **Company:** Go Native Trees, Manheim, PA
- **Phone:** 717-399-0195
- **Website:** gonativetrees.com (WordPress site with Download Manager)
- **Action:** Request direct download link or check their downloads page

## Step 2: Add URLs to Adapters

Edit the file:
```
/sessions/friendly-sleepy-edison/mnt/BloomboxSupplyPortal/scrape/adapters/pdf_pricelists.py
```

### For Hoffman Nursery (Line ~425)

Find:
```python
@register
class HoffmannNurseryAdapter(PDFAdapter):
    supplier_id = 111
    supplier_name = "Hoffman Nursery"
    pdf_urls = [
        # Placeholder URLs for when supplier publishes price list
        # "https://hoffmannursery.com/price-list.pdf",
        # "https://hoffmannursery.com/catalog/ornamental-grasses.pdf",
    ]
```

Replace with (example):
```python
@register
class HoffmannNurseryAdapter(PDFAdapter):
    supplier_id = 111
    supplier_name = "Hoffman Nursery"
    pdf_urls = [
        "https://hoffmannursery.com/wholesale/price-list-2026.pdf",
    ]
```

### For Mountain Spring Nursery (Line ~495)

Replace the empty list:
```python
    pdf_urls = [
        "https://mountainspringnursery.com/wp-content/uploads/2026/catalog-price-list.xlsx",
    ]
```

### For Go Native Trees (Line ~577)

Replace the empty list:
```python
    pdf_urls = [
        "https://www.gonativetrees.com/wp-content/uploads/2026/native-species-price-list.pdf",
    ]
```

## Step 3: Verify Syntax

Test that your changes are valid:
```bash
cd /sessions/friendly-sleepy-edison/mnt/BloomboxSupplyPortal
python3 -m py_compile scrape/adapters/pdf_pricelists.py
```

Output should be silent (no errors).

## Step 4: Test with Specific Adapter

Run just your three suppliers to test:
```bash
python -m scrape.run --id 111 121 130 --verbose
```

This will:
1. Download each PDF
2. Extract tables with pdfplumber
3. Parse each row using `parse_table_row()`
4. Output products to `scrape/output/prices.json`

## Step 5: Validate Results

Check that products were extracted:
```bash
python3 << 'PYEOF'
import json
with open('scrape/output/prices.json') as f:
    data = json.load(f)
    for supplier in data.get('suppliers', []):
        if supplier['id'] in [111, 121, 130]:
            print(f"SID {supplier['id']:3d} ({supplier['name']:30s}): "
                  f"{len(supplier['products']):4d} products")
PYEOF
```

Expected output:
```
SID 111 (Hoffman Nursery                   ): XXXX products
SID 121 (Mountain Spring Nursery           ): XXXX products
SID 130 (Go Native Trees                   ): XXXX products
```

## Troubleshooting

### "Failed to download PDF"
- Verify URL is accessible in a browser
- Check that URL returns a valid PDF (not HTML error page)
- Look for 403/404/500 errors in logs

### "No tables found in PDF"
- PDF may be image-based or scanned (requires OCR)
- Verify pdfplumber can extract tables: 
  ```python
  import pdfplumber
  with pdfplumber.open('path/to/pdf') as pdf:
      for page in pdf.pages:
          print(f"Tables: {len(page.extract_tables())}")
  ```

### "Products with incorrect category"
- Edit the category detection logic in `parse_table_row()`
- Look for keyword patterns that map to wrong categories
- Add new keyword patterns as needed

### "Price not being extracted"
- Check format: `_parse_price_cell()` expects formats like:
  - `$4.50` (with dollar sign)
  - `4.50` (bare number)
  - `4,50` (European format, if modified)
- If format differs, update regex in adapter or `_parse_price_cell()`

## Monitoring

After activation, monitor these metrics:
- **Products/supplier:** Should be > 100 for meaningful data
- **Parse success rate:** Aim for > 95% (most rows parseable)
- **Price quality:** Check that prices are in expected range
- **Category accuracy:** Spot-check a few products match expected categories

## Deactivation / Pause

To pause scraping without deleting the adapter:

```python
    pdf_urls = [
        # "https://...",  # Temporarily disabled
    ]
    # Or set requires_login = True if credentials not available
    requires_login = True
```

Then run without the `--id 111 121 130` flags.

## Advanced: Custom Table Formats

If the actual PDF table format differs from expected:

1. Download a sample PDF
2. Inspect with pdfplumber:
   ```python
   import pdfplumber
   with pdfplumber.open('sample.pdf') as pdf:
       for table in pdf.pages[0].extract_tables():
           for row in table[:5]:  # First 5 rows
               print(row)
   ```

3. Modify `parse_table_row()` to match actual structure:
   ```python
   def parse_table_row(self, row: list[str], page_num: int) -> Optional[dict]:
       # Adjust indices based on actual table structure
       name = row[2]  # If name is column 2, not 1
       price = row[5]  # If price is column 5, not 4
       # etc.
   ```

4. Test locally before deploying

## Support

If issues persist:
1. Check logs: `python -m scrape.run --id 111 --verbose`
2. Review pdf_pricelists.py docstrings
3. Compare against working adapters (ErnstSeedsAdapter, BlueSkyAvailAdapter)
4. Examine actual PDF structure vs expected format in docstring

---

**Build Date:** April 13, 2026  
**Status:** Ready for deployment (awaiting PDF URLs)
