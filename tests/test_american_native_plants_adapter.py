import io
import unittest

import openpyxl

from scrape.adapters.pdf_pricelists import AmericanNativePlantsAdapter


class AmericanNativePlantsAdapterTests(unittest.TestCase):
    def test_parse_workbook_extracts_real_availability_rows(self):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Availability Report + Pricing"
        worksheet.append(["Availability - April 30th, 2026", "Locations: ", None, None])
        worksheet.append(["www.AmericanNativePlants.com", "7500 Marshy Point Rd, Middle River MD, 21220", None, None])
        worksheet.append(["***$1,000.00 Minimum purchase required to receive wholesale pricing***", None, None, None])
        worksheet.append(["NS species are \"Non-sellable\" Rooting Plants", None, None, None])
        worksheet.append(["Species", "Common Name", "Quantity", "Category"])
        worksheet.append(["2' Rainbow Defender Shelter", "2' Rainbow Defender Shelter", 376, "Hardgoods"])
        worksheet.append(["Acer pensylvanicum #3 NS", "Striped Maple #3 NS", 27, "Tree"])

        buffer = io.BytesIO()
        workbook.save(buffer)
        workbook.close()

        adapter = AmericanNativePlantsAdapter()
        rows = adapter.parse_workbook(buffer.getvalue(), "https://www.americannativeplants.com/wp-content/uploads/2026/05/Availability-05-06-2026.xlsx")

        self.assertEqual(2, len(rows))
        self.assertEqual("2' Rainbow Defender Shelter", rows[0]["name"])
        self.assertEqual(376, rows[0]["extras"]["available_qty"])
        self.assertEqual("Hardgoods", rows[0]["category"])
        self.assertEqual("Striped Maple #3 NS (Acer pensylvanicum #3 NS)", rows[1]["name"])
        self.assertEqual(27, rows[1]["extras"]["available_qty"])
        self.assertEqual("Tree", rows[1]["category"])
        self.assertEqual(0.0, rows[1]["price"])


if __name__ == "__main__":
    unittest.main()
