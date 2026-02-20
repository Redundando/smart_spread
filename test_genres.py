"""Test reading Genres tab with list format"""
from smartspread import SmartSpread
import json

try:
    spread = SmartSpread(
        sheet_identifier="1s1diMjy1VgvTBoKmroVF0OXTyio5sgb9wbdpKzfi_nc",
        key_file="config.json"
    )
    print("✓ SmartSpread initialized")
    
    tab = spread.tab("Genres", data_format="list")
    print("✓ Tab loaded successfully")
    
    print(f"\nData type: {type(tab.data)}")
    print(f"Number of rows: {len(tab.data)}")
    print(f"Headers: {tab.data[0]}")
    
    # Check for pd.NA in the data
    has_pd_na = False
    for i, row in enumerate(tab.data):
        for j, val in enumerate(row):
            if hasattr(val, '__class__') and 'NAType' in str(type(val)):
                print(f"✗ Found pd.NA at row {i}, col {j}: {val}")
                has_pd_na = True
    
    if not has_pd_na:
        print("\n✓ No pd.NA values found in output")
    
    # Test JSON serialization
    try:
        json_str = json.dumps(tab.data)
        print("✓ JSON serialization succeeded")
    except TypeError as e:
        print(f"✗ JSON serialization failed: {e}")
    
    # Show sample rows
    print(f"\nFirst 3 rows:")
    for i in range(min(3, len(tab.data))):
        print(f"  Row {i}: {tab.data[i]}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
