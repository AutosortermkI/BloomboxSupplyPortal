# Supplier Master Audit

This report is generated from the raw `index.html` supplier import and registered adapter source code. It is not evidence that any supplier is real or verified.

## Raw Import Summary

- Raw supplier records: 127
- Unique legacy IDs: 114
- Duplicate legacy ID rows: 13
- Registered adapters: 17

## Issue Counts

| Issue code | Count |
| --- | --- |
| adapter_without_supplier | 0 |
| duplicate_domain | 1 |
| duplicate_legacy_id | 13 |
| missing_location | 0 |
| missing_website | 0 |
| name_domain_mismatch | 1 |
| registered_placeholder_adapter | 3 |
| supplier_without_adapter | 97 |

## Duplicate Legacy IDs

| Legacy ID | Rows | Raw names | Raw websites |
| --- | --- | --- | --- |
| 200 | 2 | Griffin Greenhouse Supplies; Floral King Wholesale Nursery | griffins.com; floralkingnursery.com |
| 201 | 2 | Nolt's Greenhouse Supplies; Musser Forests Inc | noltsgreenhousesupplies.com; musserforests.com |
| 202 | 2 | HC Companies; Colebrook Nursery | hc-companies.com; colebrooknursery.com |
| 203 | 2 | Kirby Agri; Meadowview Wholesale Nursery | kirbyagri.com; meadowviewnursery.com |
| 204 | 2 | Plant Food Company; Sunnyslope Nurseries | plantfoodco.com; sunnyslope-nurseries.com |
| 205 | 2 | MasterTag; York Nursery & Garden Center Supply | mastertag.com; yorknursery.com |
| 206 | 2 | BWI Companies; Lebanon Ornamental Nursery | bwicompanies.com; lebanonnursery.com |
| 207 | 2 | SiteOne Landscape Supply; Eppley Nursery | siteone.com; eppley-nursery.com |
| 208 | 2 | Aquarius Supply; Herr's Nursery & Garden Center | aquariussupply.com; herrsnursery.com |
| 209 | 2 | Beneficial Insectary; Meadow Fresh Perennials | insectary.com; meadowfreshperennials.com |
| 210 | 2 | ARBICO Organics; Adams County Greenhouse & Nursery | arbico-organics.com; adamscountygreenhouse.com |
| 211 | 2 | Organic Mechanics Soil; Sunrise Nursery Supply | organicmechanicsoil.com; sunrisenurserysupply.com |
| 244 | 2 | Blue Sky Nursery; Blue Sky Nursery | blueskynursery.ca; blueskynursery.ca |

## Adapter/Dashboard Mismatches

| Code | Legacy ID | Adapter class | Adapter name | Dashboard name(s) |
| --- | --- | --- | --- | --- |
| name_domain_mismatch | 201 | NoltsSuppliesAdapter | Nolts Greenhouse Supplies | Musser Forests Inc; Nolt's Greenhouse Supplies |
| registered_placeholder_adapter | 111 | HoffmannNurseryAdapter | Hoffman Nursery |  |
| registered_placeholder_adapter | 121 | MountainSpringNurseryAdapter | Mountain Spring Nursery |  |
| registered_placeholder_adapter | 130 | GoNativeTreesAdapter | Go Native Trees |  |
| supplier_without_adapter | 1 |  |  | North Creek Nurseries |
| supplier_without_adapter | 2 |  |  | Octoraro Native Plant Nursery |
| supplier_without_adapter | 3 |  |  | Brandywine Trees |
| supplier_without_adapter | 4 |  |  | Wm. F. Hammell Nurseries |
| supplier_without_adapter | 5 |  |  | Feeney's Wholesale Nursery |
| supplier_without_adapter | 6 |  |  | Coles Nurseries |
| supplier_without_adapter | 7 |  |  | Peace Tree Farm |
| supplier_without_adapter | 8 |  |  | Highland Hill Farm |
| supplier_without_adapter | 9 |  |  | Clearview Nursery |
| supplier_without_adapter | 10 |  |  | Gino's Nursery |
| supplier_without_adapter | 11 |  |  | Gro 'n Sell |
| supplier_without_adapter | 12 |  |  | Groth Nurseries |
| supplier_without_adapter | 13 |  |  | ArcheWild |
| supplier_without_adapter | 14 |  |  | Heartwood Nursery |
| supplier_without_adapter | 15 |  |  | Edge of the Woods Native Plant Nursery |
| supplier_without_adapter | 17 |  |  | Musselman Greenhouses |
| supplier_without_adapter | 18 |  |  | Huber Nurseries |
| supplier_without_adapter | 23 |  |  | Creek Hill Nursery |
| supplier_without_adapter | 27 |  |  | Miller Plant Farm |
| supplier_without_adapter | 29 |  |  | Babikow Greenhouses |
| supplier_without_adapter | 30 |  |  | Waverly Farm |
| supplier_without_adapter | 31 |  |  | Wicklein's Water Gardens & Nursery |
| supplier_without_adapter | 32 |  |  | Catoctin Mountain Growers |
| supplier_without_adapter | 33 |  |  | Tidal Creek Growers |
| supplier_without_adapter | 34 |  |  | Ruppert Nurseries |
| supplier_without_adapter | 36 |  |  | Clear Ridge Nursery |
| supplier_without_adapter | 38 |  |  | Delmarva Native Plants |
| supplier_without_adapter | 39 |  |  | Tideland Gardens |
| supplier_without_adapter | 48 |  |  | Overdevest Nurseries |
| supplier_without_adapter | 49 |  |  | New Moon Nursery |
| supplier_without_adapter | 50 |  |  | County Line Nurseries |
| supplier_without_adapter | 52 |  |  | Riggins Nursery |
| supplier_without_adapter | 53 |  |  | Pinelands Nursery & Supply |
| supplier_without_adapter | 59 |  |  | Lucas Greenhouse |
| supplier_without_adapter | 60 |  |  | Lennon Farm Greenhouses |
| supplier_without_adapter | 61 |  |  | DVFlora |
| supplier_without_adapter | 65 |  |  | Riverbend Nursery |
| supplier_without_adapter | 69 |  |  | Colesville Nursery |
| supplier_without_adapter | 70 |  |  | Eastern Shore Nursery of Virginia |
| supplier_without_adapter | 80 |  |  | Costa Farms |
| supplier_without_adapter | 81 |  |  | Dewar Nurseries |
| supplier_without_adapter | 82 |  |  | Emerald Forest Tropicals |
| supplier_without_adapter | 83 |  |  | Holt Nurseries |
| supplier_without_adapter | 93 |  |  | Knox Horticulture |
| supplier_without_adapter | 98 |  |  | Morning Dew Tropical Plants |
| supplier_without_adapter | 103 |  |  | Aldershot Greenhouses |
| supplier_without_adapter | 105 |  |  | NVK Nurseries |
| supplier_without_adapter | 109 |  |  | Spring Meadow Nursery |
| supplier_without_adapter | 114 |  |  | Sun Gro Horticulture (Fafard) |
| supplier_without_adapter | 120 |  |  | Minders Nursery |
| supplier_without_adapter | 122 |  |  | Rosedale Growers |
| supplier_without_adapter | 123 |  |  | Musser Forests |
| supplier_without_adapter | 124 |  |  | Kline's Tree Farm |
| supplier_without_adapter | 125 |  |  | Brown's Tree Farm |
| supplier_without_adapter | 126 |  |  | Adams County Nursery |
| supplier_without_adapter | 127 |  |  | Boyer Nurseries & Orchards |
| supplier_without_adapter | 128 |  |  | Frysville Farms |
| supplier_without_adapter | 131 |  |  | Esbenshade's Greenhouses |
| supplier_without_adapter | 132 |  |  | Moyers Mum Farm |
| supplier_without_adapter | 133 |  |  | Holly Hill Farms |
| supplier_without_adapter | 134 |  |  | New Blooms Greenhouse |
| supplier_without_adapter | 135 |  |  | Holly Days Nursery |
| supplier_without_adapter | 136 |  |  | Splash Plants |
| supplier_without_adapter | 140 |  |  | Raemelton Farm |
| supplier_without_adapter | 141 |  |  | Cavano's Perennials |
| supplier_without_adapter | 142 |  |  | Ecotone Native Nursery |
| supplier_without_adapter | 143 |  |  | Sun Nurseries |
| supplier_without_adapter | 144 |  |  | Kollar Nursery |
| supplier_without_adapter | 145 |  |  | Bell Nursery |
| supplier_without_adapter | 146 |  |  | Maryland Aquatic Nurseries |
| supplier_without_adapter | 147 |  |  | Patuxent Nursery |
| supplier_without_adapter | 160 |  |  | Bruce Jensen Nurseries |
| supplier_without_adapter | 161 |  |  | Wekiwa Gardens |
| supplier_without_adapter | 162 |  |  | Biostok Foliage |
| supplier_without_adapter | 163 |  |  | Redland Nursery |
| supplier_without_adapter | 164 |  |  | Sunshine Tropical Foliage |
| supplier_without_adapter | 165 |  |  | TreeWorld Wholesale |
| supplier_without_adapter | 166 |  |  | Plant Life Farms |
| supplier_without_adapter | 167 |  |  | Bernecker's Nursery |
| supplier_without_adapter | 168 |  |  | Native Tree Nursery |
| supplier_without_adapter | 169 |  |  | Mid Florida Nurseries |
| supplier_without_adapter | 175 |  |  | Rockwell Farms |
| supplier_without_adapter | 176 |  |  | Acorn Farms |
| supplier_without_adapter | 177 |  |  | Dickman Farms |
| supplier_without_adapter | 178 |  |  | Van Engelen Inc |
| supplier_without_adapter | 179 |  |  | Colorblends Wholesale Flower Bulbs |
| supplier_without_adapter | 180 |  |  | KGS Plants |
| supplier_without_adapter | 200 |  |  | Floral King Wholesale Nursery; Griffin Greenhouse Supplies |
| supplier_without_adapter | 202 |  |  | Colebrook Nursery; HC Companies |
| supplier_without_adapter | 203 |  |  | Kirby Agri; Meadowview Wholesale Nursery |
| supplier_without_adapter | 204 |  |  | Plant Food Company; Sunnyslope Nurseries |
| supplier_without_adapter | 205 |  |  | MasterTag; York Nursery & Garden Center Supply |
| supplier_without_adapter | 206 |  |  | BWI Companies; Lebanon Ornamental Nursery |
| supplier_without_adapter | 208 |  |  | Aquarius Supply; Herr's Nursery & Garden Center |
| supplier_without_adapter | 209 |  |  | Beneficial Insectary; Meadow Fresh Perennials |
| supplier_without_adapter | 211 |  |  | Organic Mechanics Soil; Sunrise Nursery Supply |
| supplier_without_adapter | 306 |  |  | HeadStart Nursery |

## All Machine-Readable Issues

- `duplicate_domain` `{"code": "duplicate_domain", "legacy_ids": [123, 201], "normalized_domain": "musserforests.com", "record_count": 2, "supplier_names": ["Musser Forests", "Musser Forests Inc"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["floralkingnursery.com", "griffins.com"], "legacy_id": 200, "record_count": 2, "supplier_names": ["Floral King Wholesale Nursery", "Griffin Greenhouse Supplies"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["musserforests.com", "noltsgreenhousesupplies.com"], "legacy_id": 201, "record_count": 2, "supplier_names": ["Musser Forests Inc", "Nolt's Greenhouse Supplies"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["colebrooknursery.com", "hc-companies.com"], "legacy_id": 202, "record_count": 2, "supplier_names": ["Colebrook Nursery", "HC Companies"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["kirbyagri.com", "meadowviewnursery.com"], "legacy_id": 203, "record_count": 2, "supplier_names": ["Kirby Agri", "Meadowview Wholesale Nursery"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["plantfoodco.com", "sunnyslope-nurseries.com"], "legacy_id": 204, "record_count": 2, "supplier_names": ["Plant Food Company", "Sunnyslope Nurseries"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["mastertag.com", "yorknursery.com"], "legacy_id": 205, "record_count": 2, "supplier_names": ["MasterTag", "York Nursery & Garden Center Supply"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["bwicompanies.com", "lebanonnursery.com"], "legacy_id": 206, "record_count": 2, "supplier_names": ["BWI Companies", "Lebanon Ornamental Nursery"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["eppley-nursery.com", "siteone.com"], "legacy_id": 207, "record_count": 2, "supplier_names": ["Eppley Nursery", "SiteOne Landscape Supply"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["aquariussupply.com", "herrsnursery.com"], "legacy_id": 208, "record_count": 2, "supplier_names": ["Aquarius Supply", "Herr's Nursery & Garden Center"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["insectary.com", "meadowfreshperennials.com"], "legacy_id": 209, "record_count": 2, "supplier_names": ["Beneficial Insectary", "Meadow Fresh Perennials"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["adamscountygreenhouse.com", "arbico-organics.com"], "legacy_id": 210, "record_count": 2, "supplier_names": ["ARBICO Organics", "Adams County Greenhouse & Nursery"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["organicmechanicsoil.com", "sunrisenurserysupply.com"], "legacy_id": 211, "record_count": 2, "supplier_names": ["Organic Mechanics Soil", "Sunrise Nursery Supply"]}`
- `duplicate_legacy_id` `{"code": "duplicate_legacy_id", "domains": ["blueskynursery.ca"], "legacy_id": 244, "record_count": 2, "supplier_names": ["Blue Sky Nursery"]}`
- `name_domain_mismatch` `{"adapter_class": "NoltsSuppliesAdapter", "adapter_supplier_name": "Nolts Greenhouse Supplies", "code": "name_domain_mismatch", "legacy_id": 201, "supplier_names": ["Musser Forests Inc", "Nolt's Greenhouse Supplies"]}`
- `registered_placeholder_adapter` `{"adapter_class": "HoffmannNurseryAdapter", "adapter_supplier_name": "Hoffman Nursery", "code": "registered_placeholder_adapter", "legacy_id": 111}`
- `registered_placeholder_adapter` `{"adapter_class": "MountainSpringNurseryAdapter", "adapter_supplier_name": "Mountain Spring Nursery", "code": "registered_placeholder_adapter", "legacy_id": 121}`
- `registered_placeholder_adapter` `{"adapter_class": "GoNativeTreesAdapter", "adapter_supplier_name": "Go Native Trees", "code": "registered_placeholder_adapter", "legacy_id": 130}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 1, "supplier_names": ["North Creek Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 2, "supplier_names": ["Octoraro Native Plant Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 3, "supplier_names": ["Brandywine Trees"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 4, "supplier_names": ["Wm. F. Hammell Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 5, "supplier_names": ["Feeney's Wholesale Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 6, "supplier_names": ["Coles Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 7, "supplier_names": ["Peace Tree Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 8, "supplier_names": ["Highland Hill Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 9, "supplier_names": ["Clearview Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 10, "supplier_names": ["Gino's Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 11, "supplier_names": ["Gro 'n Sell"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 12, "supplier_names": ["Groth Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 13, "supplier_names": ["ArcheWild"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 14, "supplier_names": ["Heartwood Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 15, "supplier_names": ["Edge of the Woods Native Plant Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 17, "supplier_names": ["Musselman Greenhouses"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 18, "supplier_names": ["Huber Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 23, "supplier_names": ["Creek Hill Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 27, "supplier_names": ["Miller Plant Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 29, "supplier_names": ["Babikow Greenhouses"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 30, "supplier_names": ["Waverly Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 31, "supplier_names": ["Wicklein's Water Gardens & Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 32, "supplier_names": ["Catoctin Mountain Growers"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 33, "supplier_names": ["Tidal Creek Growers"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 34, "supplier_names": ["Ruppert Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 36, "supplier_names": ["Clear Ridge Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 38, "supplier_names": ["Delmarva Native Plants"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 39, "supplier_names": ["Tideland Gardens"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 48, "supplier_names": ["Overdevest Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 49, "supplier_names": ["New Moon Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 50, "supplier_names": ["County Line Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 52, "supplier_names": ["Riggins Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 53, "supplier_names": ["Pinelands Nursery & Supply"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 59, "supplier_names": ["Lucas Greenhouse"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 60, "supplier_names": ["Lennon Farm Greenhouses"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 61, "supplier_names": ["DVFlora"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 65, "supplier_names": ["Riverbend Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 69, "supplier_names": ["Colesville Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 70, "supplier_names": ["Eastern Shore Nursery of Virginia"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 80, "supplier_names": ["Costa Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 81, "supplier_names": ["Dewar Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 82, "supplier_names": ["Emerald Forest Tropicals"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 83, "supplier_names": ["Holt Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 93, "supplier_names": ["Knox Horticulture"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 98, "supplier_names": ["Morning Dew Tropical Plants"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 103, "supplier_names": ["Aldershot Greenhouses"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 105, "supplier_names": ["NVK Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 109, "supplier_names": ["Spring Meadow Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 114, "supplier_names": ["Sun Gro Horticulture (Fafard)"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 120, "supplier_names": ["Minders Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 122, "supplier_names": ["Rosedale Growers"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 123, "supplier_names": ["Musser Forests"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 124, "supplier_names": ["Kline's Tree Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 125, "supplier_names": ["Brown's Tree Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 126, "supplier_names": ["Adams County Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 127, "supplier_names": ["Boyer Nurseries & Orchards"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 128, "supplier_names": ["Frysville Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 131, "supplier_names": ["Esbenshade's Greenhouses"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 132, "supplier_names": ["Moyers Mum Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 133, "supplier_names": ["Holly Hill Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 134, "supplier_names": ["New Blooms Greenhouse"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 135, "supplier_names": ["Holly Days Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 136, "supplier_names": ["Splash Plants"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 140, "supplier_names": ["Raemelton Farm"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 141, "supplier_names": ["Cavano's Perennials"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 142, "supplier_names": ["Ecotone Native Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 143, "supplier_names": ["Sun Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 144, "supplier_names": ["Kollar Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 145, "supplier_names": ["Bell Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 146, "supplier_names": ["Maryland Aquatic Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 147, "supplier_names": ["Patuxent Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 160, "supplier_names": ["Bruce Jensen Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 161, "supplier_names": ["Wekiwa Gardens"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 162, "supplier_names": ["Biostok Foliage"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 163, "supplier_names": ["Redland Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 164, "supplier_names": ["Sunshine Tropical Foliage"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 165, "supplier_names": ["TreeWorld Wholesale"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 166, "supplier_names": ["Plant Life Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 167, "supplier_names": ["Bernecker's Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 168, "supplier_names": ["Native Tree Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 169, "supplier_names": ["Mid Florida Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 175, "supplier_names": ["Rockwell Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 176, "supplier_names": ["Acorn Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 177, "supplier_names": ["Dickman Farms"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 178, "supplier_names": ["Van Engelen Inc"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 179, "supplier_names": ["Colorblends Wholesale Flower Bulbs"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 180, "supplier_names": ["KGS Plants"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 200, "supplier_names": ["Floral King Wholesale Nursery", "Griffin Greenhouse Supplies"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 202, "supplier_names": ["Colebrook Nursery", "HC Companies"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 203, "supplier_names": ["Kirby Agri", "Meadowview Wholesale Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 204, "supplier_names": ["Plant Food Company", "Sunnyslope Nurseries"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 205, "supplier_names": ["MasterTag", "York Nursery & Garden Center Supply"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 206, "supplier_names": ["BWI Companies", "Lebanon Ornamental Nursery"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 208, "supplier_names": ["Aquarius Supply", "Herr's Nursery & Garden Center"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 209, "supplier_names": ["Beneficial Insectary", "Meadow Fresh Perennials"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 211, "supplier_names": ["Organic Mechanics Soil", "Sunrise Nursery Supply"]}`
- `supplier_without_adapter` `{"code": "supplier_without_adapter", "legacy_id": 306, "supplier_names": ["HeadStart Nursery"]}`
