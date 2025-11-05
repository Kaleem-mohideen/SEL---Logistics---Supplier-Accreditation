import pandas as pd
import json
from pathlib import Path

# === CONFIGURATION ===

EXCEL_PATH = "C:\\Users\\Hp\\Documents\\logistics//Tables Database FULL 1.3 (1).xlsx"

# Define how each sheet maps to Django model + column names
TABLES = {
    "Table Function Code": {
        "model": "staff.functioncode",
        "fields": {"code": "FUNCTION CODE", "description": "Description"},
        "fixture": "function_code3.json",
    },
    "Table Venue": {
        "model": "staff.venue",
        "fields": {"code": "Venue Code", "name": "Venue Description"},
        "fixture": "venue3.json",
    },
    "Table Gender": {
        "model": "staff.gender",
        "fields": {"code": "Gender Code", "label": "Gender Description"},
        "fixture": "gender3.json",
    },
    "Table Nationality": {
        "model": "staff.nationality",
        "fields": {"code": "Nationality Code", "country_name": "Nationality Description"},
        "fixture": "nationality3.json",
    },
    "Table Document": {
        "model": "staff.document",
        "fields": {"type_name": "Description"},
        "fixture": "document3.json",
    },
    "Table Country Issuing Document": {
        "model": "staff.countryissuingdocument",
        "fields": {
            "code": "Country issuing document Code",
            "country_name": "Country issuing document  Description",
        },
        "fixture": "country_issuing_document3.json",
    },
    "Table Country of Birth": {
        "model": "staff.countryofbirth",
        "fields": {
            "code": "Country or Territory of birth Code",
            "country_name": "Country or Territory of birth Description",
        },
        "fixture": "country_birth3.json",
    },
    "Table Place City of Birth": {
        "model": "staff.placeorcityofbirth",
        "fields": {"city_name": "Place or City of birth (copy & paste excat value if Countr of birth is Italy)"},
        "fixture": "place_city_birth3.json",
    },
    "Table Status": {
        "model": "staff.status",
        "fields": {"status_id": "Status ID", "label": "Status Description"},
        "fixture": "status3.json",
    },
    "Table Supplier": {
        "model": "accounts.supplier",
        "fields": {"code": "Supplier Code", "name": "Name Supplier","function_code": "Function Code"},
        "fixture": "supplier3.json",
    },
}

OUTPUT_DIR = Path("fixtures")
OUTPUT_DIR.mkdir(exist_ok=True)

# === FUNCTION ===

def dataframe_to_fixture(df, model_name, fields_map):
    records = []
    for i, row in df.iterrows():
        # Skip rows where primary column (first) is empty
        first_field = list(fields_map.values())[0]
        if pd.isna(row.get(first_field)):
            continue
        record_fields = {}
        for model_field, excel_col in fields_map.items():
            if excel_col not in df.columns:
                print(f"Missing column {excel_col} in sheet, skipping field {model_field}")
                continue
            value = str(row[excel_col]).strip() if pd.notna(row[excel_col]) else ""
            record_fields[model_field] = value
            if model_name == 'staff.placeorcityofbirth':
                record_fields['category'] = 87

        records.append({
            "model": model_name,
            "pk": i + 1,
            "fields": record_fields,
        })
    return records


# === MAIN ===

print("Generating Django fixtures from Excel...")
for sheet_name, cfg in TABLES.items():
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    except ValueError:
        print(f"Sheet not found: {sheet_name}")
        continue

    model = cfg["model"]
    fields = cfg["fields"]
    fixture_path = OUTPUT_DIR / cfg["fixture"]

    print(f"Processing {sheet_name} → {fixture_path}")
    records = dataframe_to_fixture(df, model, fields)

    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Created {fixture_path} with {len(records)} records")

print("\n All fixtures created successfully!")
