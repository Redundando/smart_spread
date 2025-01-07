# SmartSpread

SmartSpread is a Python library that extends the functionality of `gspread` for enhanced spreadsheet manipulation, enabling easier integration with Google Sheets.

## Features
- Simplified spreadsheet creation and access.
- Easy tab (worksheet) management.
- Supports data handling with Pandas DataFrames, lists, and dictionaries.
- Batch updates and row-level modifications.
- Cached properties for optimized performance.

## Installation
```bash
pip install smartspread
```

## Requirements
- Python 3.7+
- `gspread`
- `pandas`
- `cacherator`
- `logorator`

## Usage
```python
from smartspread import SmartSpread

# Initialize
spread = SmartSpread(sheet_identifier="MySheet", key_file="path/to/google_service_account_keyfile.json")

# Write data
data = [["Name", "Age"], ["Alice", 30], ["Bob", 25]]
spread.write_to_tab(data, tab_name="Sheet1", overwrite_tab=True)

# Read data
df = spread.tab_to_df("Sheet1")
print(df)
```

## License
This project is licensed under the MIT License.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Author
Arved Klöhn - [Redundando](https://github.com/Redundando/)
