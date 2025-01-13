# SmartSpread

SmartSpread is a Python library that extends [gspread](https://gspread.readthedocs.io/) with advanced features for managing and manipulating Google Sheets. It offers a higher-level API for spreadsheet and tab operations, seamless integration with Pandas, and automation capabilities like background data syncing.

## Features

- **Spreadsheet Management**:
  - Create and retrieve spreadsheets with ease.
  - Grant access to collaborators programmatically.

- **Tab Operations**:
  - Create, read, write, and update individual tabs.
  - Support for multiple data formats: `DataFrame`, `list[dict]`, and `list[list]`.

- **Automation**:
  - Background writing to Google Sheets at regular intervals.
  - Efficient caching to minimize redundant API calls.

- **Pandas Integration**:
  - Convert Google Sheets data to Pandas DataFrames and vice versa.
  - Seamless handling of numeric, string, and date formats.

## Installation

Install the library using `pip`:

```bash
pip install smartspread
```

## Getting Started
### Authentication
- Set up a Google Cloud Project and enable the Google Sheets API.
- Create a service account and download the credentials JSON file.
- Share your spreadsheet with the service account email.
## Example Usage
### Initialize a Spreadsheet
```python
from smart_spread import SmartSpread

# Initialize SmartSpread with a Google Sheets ID and credentials file
spread = SmartSpread(
    sheet_identifier="your-spreadsheet-id-or-name",
    key_file="path/to/credentials.json"
)
```
### Work with Tabs
```python

# Get or create a tab
tab = spread.tab(tab_name="MyTab", data_format="DataFrame")

# Read data as a Pandas DataFrame
df = tab.read_data()
print(df)

# Update rows based on a column value
tab.update_row_by_column_pattern(
    column="Name",
    value="Alice",
    updates={"Age": 30, "City": "New York"}
)

# Write updated data back to the tab
tab.write_data(overwrite_tab=True)
```
### Automate Background Writing
```python

# Start background writing every 15 seconds
tab.start_background_write(interval=15, overwrite_tab=True)

# Stop background writing
tab.stop_background_write()
```
## Documentation
Homepage: [SmartSpread GitHub](https://github.com/Redundando/smart_spread)

## License
This project is licensed under the MIT License. See the LICENSE file for details.
