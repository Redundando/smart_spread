import hashlib
import json
from typing import Union, Literal
from functools import cached_property

import gspread
import pandas as pd
from logorator import Logger


def _calculate_data_hash(data: Union[pd.DataFrame, list[dict], list[list]]):
    if isinstance(data, pd.DataFrame):
        data_bytes = pd.util.hash_pandas_object(data, index=True).values.tobytes()
    elif isinstance(data, list):
        def sanitize(obj):
            if isinstance(obj, list):
                return [sanitize(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif pd.isna(obj):
                return None
            return obj
        data_bytes = json.dumps(sanitize(data), sort_keys=True).encode("utf-8")
    else:
        raise TypeError("Unsupported data type for hashing.")
    return hashlib.md5(data_bytes).hexdigest()


class SmartTab:
    """Interface for reading and writing data to a Google Sheets tab.
    
    Supports DataFrame, list of dicts, and list of lists formats with
    automatic type inference and caching.
    """


    def __init__(self,
                 sheet: gspread.Spreadsheet,
                 tab_name="",
                 data_format: Literal["DataFrame", "list", "dict"] = "DataFrame",
                 keep_number_formatting: bool = False):
        """Initialize SmartTab for a specific worksheet.
        
        Args:
            sheet: gspread Spreadsheet object
            tab_name: Name of the worksheet tab
            data_format: Format for data operations ('DataFrame', 'list', 'dict')
            keep_number_formatting: If True, preserve number formatting as strings
            
        Raises:
            ValueError: If sheet, tab_name invalid or data_format not supported
        """
        if not sheet:
            raise ValueError("sheet parameter is required")
        if not tab_name:
            raise ValueError("tab_name cannot be empty")
        if data_format not in ["DataFrame", "list", "dict"]:
            raise ValueError(f"Invalid data_format '{data_format}'. Must be 'DataFrame', 'list', or 'dict'")

        self.sheet = sheet
        self.tab_name = tab_name
        self.data_format = data_format
        self.keep_number_formatting = keep_number_formatting
        
        if not self._tab_exists:
            self._create_tab()
        
        try:
            self.data: pd.DataFrame | list[dict] | list[list] = self.read_data()
            self._stored_data_hash = _calculate_data_hash(self.data)
        except ValueError:
            self.data = pd.DataFrame()
            self._stored_data_hash = None

    def __str__(self):
        return f"Tab '{self.tab_name}'"

    def __repr__(self):
        return self.__str__()

    @property
    def _tab_exists(self) -> bool:
        try:
            self._worksheet
            return True
        except:
            return False

    @cached_property
    def _worksheet(self) -> gspread.Worksheet:
        try:
            return self.sheet.worksheet(self.tab_name)
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError(f"Worksheet '{self.tab_name}' not found") from None
        except Exception as e:
            raise RuntimeError(f"Failed to access worksheet '{self.tab_name}': {e}") from e

    @Logger()
    def _create_tab(self) -> None:
        try:
            self.sheet.add_worksheet(title=self.tab_name, rows=1000, cols=26)
            Logger.note(f"Tab '{self.tab_name}' created.")
        except Exception as e:
            Logger.note(f"Error creating tab '{self.tab_name}': {e}")
            raise RuntimeError(f"Failed to create tab '{self.tab_name}': {e}") from e

    def _read_values(self) -> list[list]:
        try:
            if self.keep_number_formatting:
                return self._worksheet.get_all_values()
            else:
                result = self.sheet.values_batch_get(
                        ranges=[self.tab_name],
                        params={"valueRenderOption": "UNFORMATTED_VALUE"}
                )
                values = result.get("valueRanges", [])[0].get("values", [])
                return values
        except Exception as e:
            raise RuntimeError(f"Failed to read values from tab '{self.tab_name}': {e}") from e

    @Logger()
    def read_data(self) -> Union[pd.DataFrame, list[dict], list[list]]:
        """Read data from the tab with automatic type inference.
        
        Returns:
            Data in the format specified by data_format (DataFrame, list of dicts, or list of lists)
            
        Raises:
            ValueError: If tab is empty or has no headers
            RuntimeError: If reading fails
        """
        try:
            values = self._read_values()
            if not values or not values[0]:
                Logger.note(f"Tab '{self.tab_name}' is empty or has no headers.")
                raise ValueError(f"Tab '{self.tab_name}' is empty or has no headers.")

            headers = values[0]
            num_cols = len(headers)
            
            # Pad rows to match header length
            data_rows = []
            for row in values[1:]:
                padded_row = row + [""] * (num_cols - len(row))
                data_rows.append(padded_row[:num_cols])
            
            df = pd.DataFrame(data_rows, columns=headers)
            df.columns = [
                    (f"Column"
                     f"_{i + 1}") if not col else col
                    for i, col in enumerate(df.columns)
            ]

            for col in df.columns:
                # Replace empty strings with None for proper type inference
                df[col] = df[col].replace("", None)
                
                # Skip type conversion if all values are None
                if df[col].isna().all():
                    continue
                
                # Try numeric conversion only on non-null values
                try:
                    # Try int conversion
                    converted = pd.to_numeric(df[col], errors='coerce')
                    if converted.notna().any() and (converted.dropna() % 1 == 0).all():
                        df[col] = converted.astype('Int64')  # Nullable integer
                        continue
                except (ValueError, TypeError):
                    pass
                
                try:
                    # Try float conversion
                    converted = pd.to_numeric(df[col], errors='coerce')
                    if converted.notna().any():
                        df[col] = converted
                        continue
                except (ValueError, TypeError):
                    pass
                
                # Keep as string, but preserve None values
                df[col] = df[col].astype(str).replace('None', None)

            Logger.note(f"Tab '{self.tab_name}' successfully read as DataFrame.")
            if self.data_format == "dict":
                result = df.to_dict(orient="records")
                return [{k: (None if pd.isna(v) else v) for k, v in row.items()} for row in result]
            if self.data_format == "list":
                return [df.columns.tolist()] + [[None if pd.isna(v) else v for v in row] for row in df.values.tolist()]
            return df
        except Exception as e:
            Logger.note(f"Error reading tab '{self.tab_name}': {e}")
            raise

    @property
    def _data_as_list(self) -> list[list]:
        if isinstance(self.data, pd.DataFrame):
            # Replace NaN/None with empty strings for Google Sheets compatibility
            df_clean = self.data.fillna("")
            values = [df_clean.columns.tolist()] + df_clean.values.tolist()
        elif isinstance(self.data, list) and all(isinstance(row, dict) for row in self.data):
            keys = list(self.data[0].keys())
            values = [keys] + [[row.get(k, "") for k in keys] for row in self.data]
        elif isinstance(self.data, list) and all(isinstance(row, list) for row in self.data):
            values = self.data
        else:
            raise ValueError("Unsupported data format. Provide a DataFrame, List of Lists, or List of Dicts.")
        return values

    @property
    def _data_as_dataframe(self) -> pd.DataFrame:
        if isinstance(self.data, pd.DataFrame):
            return self.data
        else:
            return pd.DataFrame(self.data)


    @Logger(mode="short")
    def filter_rows_by_column(self, column: str, pattern: str) -> pd.DataFrame:
        """Filter rows where column contains the pattern.
        
        Args:
            column: Column name to search
            pattern: String pattern to match
            
        Returns:
            pd.DataFrame: Filtered rows
            
        Raises:
            ValueError: If column not found or parameters empty
            RuntimeError: If filtering fails
        """
        if not column:
            raise ValueError("column parameter cannot be empty")
        if not pattern:
            raise ValueError("pattern parameter cannot be empty")
        
        try:
            df = self._data_as_dataframe
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in the data")
            matching_rows = df[df[column].str.contains(pattern, na=False)]
            return matching_rows
        except ValueError:
            raise
        except Exception as e:
            Logger.note(f"Error filtering rows by column '{column}': {e}", mode="short")
            raise RuntimeError(f"Failed to filter rows by column '{column}': {e}") from e

    @Logger(mode="short")
    def write_data(self, overwrite_tab: bool = False, as_table: bool = False) -> None:
        """Write data to the tab if it has changed.
        
        Args:
            overwrite_tab: If True, clear tab before writing
            as_table: If True, format as table with frozen header
            
        Raises:
            ValueError: If data is empty
            RuntimeError: If writing fails
        """
        if self._stored_data_hash and self._stored_data_hash == _calculate_data_hash(self.data):
            Logger.note(f"Data for tab '{self.tab_name}' has not changed.")
            return
        try:
            values = self._data_as_list
            if not values or not values[0]:
                raise ValueError("Cannot write empty data to Google Sheets")
            
            if overwrite_tab:
                self._worksheet.clear()
                self._worksheet.update(values, value_input_option='USER_ENTERED')
            else:
                start_cell = 'A1'
                end_cell = f'{chr(65 + len(values[0]) - 1)}{len(values)}'
                self._worksheet.update(f'{start_cell}:{end_cell}', values, value_input_option='USER_ENTERED')
            if as_table:
                self._worksheet.set_basic_filter()
                self._worksheet.freeze(rows=1)
                self._worksheet.format('A1:Z1', {'textFormat': {'bold': True}})

            self._stored_data_hash = _calculate_data_hash(self.data)
            Logger.note(f"Data written successfully to '{self.tab_name}'.", )

        except ValueError:
            raise
        except Exception as e:
            Logger.note(f"Error writing data to tab '{self.tab_name}': {e}")
            raise RuntimeError(f"Failed to write data to tab '{self.tab_name}': {e}") from e

    @Logger(mode="short")
    def update_row_by_column_pattern(self, column: str, value, updates: dict) -> None:
        """Update or insert a row based on column value match.
        
        Args:
            column: Column name to match
            value: Value to search for
            updates: Dict of column:value pairs to update
            
        Raises:
            ValueError: If column empty or updates invalid
            TypeError: If updates is not a dict
        """
        if not column:
            raise ValueError("column parameter cannot be empty")
        if not isinstance(updates, dict):
            raise TypeError("updates parameter must be a dictionary")
        if not updates:
            raise ValueError("updates dictionary cannot be empty")
        
        # Ensure the data is a DataFrame for easier manipulation
        df = self._data_as_dataframe

        # Add the target column if it doesn't exist
        if column not in df.columns:
            df[column] = None

        # Ensure all update columns are in the DataFrame
        for update_column in updates.keys():
            if update_column not in df.columns:
                df[update_column] = None

        # Find the first matching row
        matching_rows = df[df[column] == value]
        if matching_rows.empty:
            # No match found, add a new row with the updates
            new_row = {col: None for col in df.columns}  # Default row with None values
            new_row.update({column: value})
            new_row.update(updates)  # Apply updates to the new row

            # Append the new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            # Match found, update the first matching row
            row_index = matching_rows.index[0]
            for update_column, update_value in updates.items():
                if update_column not in df.columns:
                    # Add the update column if it doesn't exist
                    df[update_column] = None
                df.at[row_index, update_column] = update_value

        # Update self.data to reflect changes
        if self.data_format.lower() == "dataframe":
            self.data = df
        if self.data_format.lower() == "dict":
            self.data = df.to_dict(orient="records")
        if self.data_format.lower() == "list":
            self.data = [df.columns.tolist()] + df.values.tolist()
    
    def refresh(self) -> None:
        """Reload data from Google Sheets and clear cached worksheet.
        
        Use this after external changes to get the latest data.
        """
        if hasattr(self, '_worksheet'):
            del self._worksheet
        self.data = self.read_data()
        self._stored_data_hash = _calculate_data_hash(self.data)
