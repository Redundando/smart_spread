# SmartSpread

Python library for Google Sheets operations with automatic type inference, caching, and multiple data format support. Built on [gspread](https://gspread.readthedocs.io/).

## Core Concepts

**Two main classes:**
- `SmartSpread`: Represents a Google Sheets spreadsheet, manages authentication and tab access
- `SmartTab`: Represents a single worksheet tab, handles data read/write operations

**Three data formats:**
- `DataFrame`: pandas DataFrame (default) - best for data manipulation
- `dict`: List of dictionaries - each row is a dict with column names as keys
- `list`: List of lists - first row is headers, remaining rows are data

**Type inference:**
- Empty cells → `None`
- Integers → nullable `Int64` dtype (preserves `None`)
- Floats → `float64`
- Strings → `object` dtype
- Empty columns → inferred as needed when data is added

**Caching behavior:**
- Data is cached after first read to minimize API calls
- Hash comparison prevents unnecessary writes
- Use `refresh()` to reload from Google Sheets after external changes

## Installation & Setup

```bash
pip install smartspread
```

**Authentication requirements:**
1. Google Cloud Project with Sheets API enabled
2. Service account credentials JSON file
3. Spreadsheet shared with service account email

## Usage Patterns

### Basic workflow
```python
from smartspread import SmartSpread

spread = SmartSpread(
    sheet_identifier="spreadsheet-id-or-name",
    key_file="credentials.json"
)
tab = spread.tab("MyTab")  # Get or create tab
tab.data["new_column"] = "value"  # Modify DataFrame
tab.write_data(overwrite_tab=True)  # Write to Sheets
```

### Data format selection
```python
tab_df = spread.tab("Sheet1", data_format="DataFrame")  # pandas DataFrame
tab_dict = spread.tab("Sheet2", data_format="dict")     # [{"col": "val"}, ...]
tab_list = spread.tab("Sheet3", data_format="list")     # [["header"], ["val"], ...]
```

### Update or insert rows
```python
# Updates existing row where ID=123, or inserts new row if not found
tab.update_row_by_column_pattern(
    column="ID",
    value=123,
    updates={"Status": "completed", "Date": "2024-01-01"}
)
tab.write_data(overwrite_tab=True)
```

### Filter and refresh
```python
filtered = tab.filter_rows_by_column("Name", "Alice")  # Returns DataFrame
tab.refresh()  # Reload from Sheets after external changes
```

## API Reference

### SmartSpread(sheet_identifier, key_file=None, service_account_data=None, user_email=None)
**Constructor parameters:**
- `sheet_identifier`: Spreadsheet ID or name
- `key_file`: Path to service account JSON credentials
- `service_account_data`: Dict of credentials (alternative to key_file)
- `user_email`: Email for user-based auth (alternative to service account)

**Methods:**
- `tab(tab_name, data_format="DataFrame", keep_number_formatting=False)` → SmartTab
- `refresh()` → None (clears cache, reloads metadata)
- `grant_access(email, role="owner")` → None

**Properties:**
- `tab_names` → list[str]
- `url` → str
- `tab_exists(tab_name)` → bool

### SmartTab
**Attributes:**
- `data`: DataFrame | list[dict] | list[list] (mutable, modify directly)
- `tab_name`: str
- `data_format`: "DataFrame" | "dict" | "list"

**Methods:**
- `read_data()` → DataFrame | list[dict] | list[list]
- `write_data(overwrite_tab=False, as_table=False)` → None
- `update_row_by_column_pattern(column, value, updates)` → None (modifies `data` in-place)
- `filter_rows_by_column(column, pattern)` → DataFrame
- `refresh()` → None (reloads from Sheets)

## Important Implementation Details

**Type handling:**
- Empty cells → `None` (not empty string)
- Nullable integers use `Int64` dtype (not `int64`)
- Mixed-type columns automatically convert to `object` dtype when needed
- `pd.NA` values are sanitized to `None` in dict/list formats
- NaN values are converted to empty strings before writing to Sheets

**Write behavior:**
- `write_data()` only writes if data hash has changed
- `overwrite_tab=True` clears entire tab before writing
- `overwrite_tab=False` updates only the data range
- `as_table=True` adds header formatting and freeze

**Rate limits:**
- Google Sheets API: 60 requests/minute (free tier)
- Caching minimizes API calls automatically

**Error handling:**
- Empty tabs raise `ValueError` on read
- Missing columns are auto-created with `None` values
- Type mismatches trigger automatic dtype conversion

## Changelog

### v1.1.5 (2024)
- Fixed: InvalidJSONError with NaN values in dict format by sanitizing in _data_as_list dict branch

### v1.1.4 (2024)
- Fixed: TypeError when writing strings to float64 columns in update_row_by_column_pattern
- Fixed: InvalidJSONError with NaN values in write_data by converting to object dtype before fillna

### v1.1.3 (2024)
- Fixed: pd.NA values sanitized to None in list/dict formats

### v1.1.2 (2024)
- Changed: Package renamed to smartspread (no underscore)

### v1.1.1 (2024)
- Fixed: JSON serialization with Int64 columns containing pd.NA

## Links

- GitHub: https://github.com/Redundando/smart_spread
- PyPI: https://pypi.org/project/smartspread/
- License: MIT
