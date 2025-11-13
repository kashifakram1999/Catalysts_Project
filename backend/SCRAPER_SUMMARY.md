# CARB PDF Scraper - Field Extraction Summary

## PDF Structure (columns in Data.pdf)
1. Company (with phone number)
2. EO/Date (Executive Order number and date)
3. Series/Model (product series/model codes)
4. Model Year (year range or single year)
5. Make/Class (vehicle make and classification)

## Fields Successfully Extracted

### Always Present (339/339 records):
- `manufacturer` - Company name (13 unique manufacturers)
- `executive_order` - EO number (e.g., D-182-37)
- `series_model` - Product series/model codes (e.g., 80600/80700)
- `model_year_start` - Start year of applicability
- `model_year_end` - End year of applicability
- `vehicle_class` - Vehicle classification (PC, LDT1, MDV, etc.)
- `eo_date` - Executive order issue date

### Sometimes Present:
- `make` - Vehicle make (63/339 records: BMW, Chrysler, Ford, GM, Honda, Hyundai, Mazda, Nissan, Toyota, VW, Volvo)
- `model` - Vehicle model (2/339 records: Civics)
- `engine_size` - Engine displacement (0/339 in current PDF - rare/not present in this format)

## Fields NOT in PDF (Currently NULL)
These fields are in the database model but not populated by the scraper because they're not present in the PDF format:

- `product_name` - Not in PDF
- `test_group` - Not in PDF
- `cert_level` - Not in PDF
- `application_type` - Not explicitly in PDF
- `converter_location` - Not in PDF
- `converter_type` - Not in PDF
- `quantity` - Not in PDF

## Frontend Search Fields
The search form has 6 fields:
1. Year ✓ (from model_year_start/end)
2. Make ✓ (from make field - 63 records have this)
3. Model ✓ (from model field - 2 records have this)
4. Engine Size ✗ (not reliably in PDF)
5. Group/Test Group ✗ (not in PDF)
6. Application Type ✗ (not in PDF)

## Recommendations
1. Keep engine_size, test_group, and application_type as optional fields for future data sources
2. Model field works but is rare in this PDF
3. Make extraction could be improved but covers main manufacturers
4. All core fields from PDF are being extracted correctly
