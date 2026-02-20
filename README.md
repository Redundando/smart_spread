# SmartSpread

A Python library for Google Sheets that extends [gspread](https://gspread.readthedocs.io/) with a high-level API, automatic type inference, and efficient caching.

## Features

- **Simple API**: Intuitive interface for spreadsheet and tab operations
- **Multiple Data Formats**: Work with DataFrames, list of dicts, or list of lists
- **Automatic Type Inference**: Smart conversion of numeric, string, and None values
- **Efficient Caching**: Minimizes API calls to stay within rate limits
- **Pandas Integration**: Seamless DataFrame read/write operations
- **Row Operations**: Update or insert rows based on column patterns

## Installation

```bash
pip install smartspread
```

## Quick Start

### Authentication

1. Create a [Google Cloud Project](https://console.cloud.google.com/)
2. Enable the Google Sheets API
3. Create a service account and download credentials JSON
4. Share your spreadsheet with the service account email

### Basic Usage

```python
from smartspread import SmartSpread

# Initialize with credentials
spread = SmartSpread(
    sheet_identifier="your-spreadsheet-id-or-name",
    key_file="path/to/credentials.json"
)

# Get or create a tab
tab = spread.tab("MyTab")

# Read data as DataFrame
df = tab.read_data()

# Modify data
tab.data["new_column"] = "value"

# Write back to Google Sheets
tab.write_data(overwrite_tab=True)
```

### Update Rows by Pattern

```python
# Update existing row or insert new one
tab.update_row_by_column_pattern(
    column="ID",
    value=123,
    updates={"Status": "completed", "Updated": "2024-01-01"}
)
tab.write_data(overwrite_tab=True)
```

### Filter Data

```python
# Filter rows by pattern
filtered = tab.filter_rows_by_column("Name", "Alice")
print(filtered)
```

### Work with Different Formats

```python
# DataFrame format (default)
tab_df = spread.tab("Sheet1", data_format="DataFrame")
df = tab_df.data  # pandas DataFrame

# List of dicts format
tab_dict = spread.tab("Sheet2", data_format="dict")
data = tab_dict.data  # [{"col1": "val1", ...}, ...]

# List of lists format
tab_list = spread.tab("Sheet3", data_format="list")
data = tab_list.data  # [["header1", "header2"], ["val1", "val2"], ...]
```

### Refresh Data

```python
# Reload data after external changes
tab.refresh()

# Refresh spreadsheet metadata
spread.refresh()
```

## API Reference

### SmartSpread

- `SmartSpread(sheet_identifier, key_file=None, service_account_data=None, user_email=None)`
- `spread.tab(tab_name, data_format="DataFrame", keep_number_formatting=False)` - Get or create tab
- `spread.tab_names` - List all tab names
- `spread.tab_exists(tab_name)` - Check if tab exists
- `spread.url` - Get spreadsheet URL
- `spread.grant_access(email, role="owner")` - Grant access to user
- `spread.refresh()` - Clear cache and reload metadata

### SmartTab

- `tab.read_data()` - Read data from Google Sheets
- `tab.write_data(overwrite_tab=False, as_table=False)` - Write data to Google Sheets
- `tab.update_row_by_column_pattern(column, value, updates)` - Update or insert row
- `tab.filter_rows_by_column(column, pattern)` - Filter rows by pattern
- `tab.refresh()` - Reload data from Google Sheets
- `tab.data` - Access the data (DataFrame, list of dicts, or list of lists)

## Notes

- Google Sheets API has rate limits (60 requests/minute for free tier)
- SmartSpread uses caching to minimize API calls
- Empty cells are represented as `None` in DataFrames
- Integer columns use nullable `Int64` dtype to preserve `None` values

## Changelog

### v1.1.2 (2024)
- Changed: Package renamed to `smartspread` (no underscore) for cleaner imports
- Added: Backwards compatibility for `from smart_spread import ...` with deprecation warning

### v1.1.1 (2024)
- Fixed: JSON serialization error when using `data_format="list"` with nullable Int64 columns containing `pd.NA` values

## License

MIT License - see LICENSE file for details.

## Links

- [GitHub Repository](https://github.com/Redundando/smart_spread)
- [PyPI Package](https://pypi.org/project/smartspread/)
