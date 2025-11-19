import hashlib
import json
import threading
import time
from typing import Union, Literal

import gspread
import pandas as pd
from cacherator import Cached, JSONCache
from logorator import Logger


def _calculate_data_hash(data: Union[pd.DataFrame, list[dict], list[list]]):
    if isinstance(data, pd.DataFrame):
        data_bytes = pd.util.hash_pandas_object(data, index=True).values.tobytes()
    elif isinstance(data, list):
        data_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    else:
        raise TypeError("Unsupported data type for hashing.")
    return hashlib.md5(data_bytes).hexdigest()


class SmartTab(JSONCache):
    """
        A utility class for managing and interacting with individual tabs (worksheets) in a Google spreadsheet.

        The `SmartTab` class provides high-level methods for reading, writing, and updating data
        within a specific tab of a Google spreadsheet. It supports various data formats (e.g., Pandas
        DataFrame, list of dictionaries, or list of lists) and integrates caching to optimize performance.

        Attributes:
            sheet (gspread.Spreadsheet): The Google spreadsheet object containing this tab.
            tab_name (str): The name of the tab (worksheet) within the spreadsheet.
            data_format (str): The preferred format for tab data. Supported formats are "DataFrame", "list", and "dict".
            keep_number_formatting (bool): Whether to preserve number formatting from Google Sheets.
            clear_cache (bool): Whether to clear cached data on initialization.
            data (Union[pd.DataFrame, list[dict], list[list]]): The current data stored in the tab.
            _stored_data_hash (str): A hash of the current data to detect changes for updates.
            _background_writer (threading.Thread): A thread object for background writing operations.
            _stop_event (threading.Event): A threading event to control the background writer.

        Methods:
            read_data(): Reads data from the tab and returns it in the preferred format.
            data_as_list: Converts and returns the tab's data as a list of lists.
            data_as_dataframe: Converts and returns the tab's data as a Pandas DataFrame.
            filter_rows_by_column(column, pattern): Filters rows where the specified column matches a pattern.
            write_data(overwrite_tab, as_table): Writes the current data to the tab, optionally overwriting it.
            update_row_by_column_pattern(column, value, updates): Updates a row based on an exact match in a column.
            start_background_write(interval, overwrite_tab, as_table): Starts a background thread to periodically write data.
            stop_background_write(): Stops the background writing thread.
            create_tab(): Creates the tab if it does not already exist.

        Notes:
            - This class integrates with gspread for Google Sheets API interactions.
            - Caching is used to minimize redundant API calls, improving performance.
            - Supports both manual and automated (background) data updates.
        """


    def __init__(self,
                 sheet: gspread.Spreadsheet,
                 tab_name="",
                 data_format: Literal["DataFrame", "list", "dict"] = "DataFrame",
                 keep_number_formatting: bool = False,
                 clear_cache: bool = True):
        """
            Initializes a SmartTab object for managing a specific tab in a Google spreadsheet.

            Args:
                sheet (gspread.Spreadsheet): The Google spreadsheet object containing the tab.
                    - Required for interacting with the Google Sheets API.
                tab_name (str): The name of the tab (worksheet) within the spreadsheet.
                    - If the tab does not exist, it will be created automatically.
                data_format (str): The preferred format for working with tab data. Default is "DataFrame".
                    - Supported formats: "DataFrame", "list", "dict".
                    - Determines how data is returned or stored within the tab.
                keep_number_formatting (bool): Whether to preserve number formatting from Google Sheets. Default is False.
                    - When False, numeric data is returned in raw form (e.g., numbers as numbers, dates as serials).
                clear_cache (bool): Whether to clear any cached data for the tab on initialization. Default is True.

            Attributes:
                data (Union[pd.DataFrame, list[dict], list[list]]): The current data in the tab, loaded during initialization.
                _stored_data_hash (str): A hash of the current data, used to detect changes before writing updates.
                _background_writer (threading.Thread): A background thread for automated data writing.
                _stop_event (threading.Event): An event to control the background writer thread.

            Raises:
                ValueError: If the `tab_name` is invalid or empty.
                TypeError: If unsupported values are provided for `data_format`.

            Notes:
                - The tab is created automatically if it does not already exist in the spreadsheet.
                - The `data` attribute is loaded during initialization, respecting the specified `data_format`.
                - Integrates with caching to optimize performance and minimize API calls.
            """

        self.sheet = sheet
        self.tab_name = tab_name
        self.data_format = data_format
        self.keep_number_formatting = keep_number_formatting
        self.clear_cache = clear_cache
        JSONCache.__init__(self, data_id=f"sheet_{sheet.title}_tab_{tab_name}", directory="data/smart_spread/tabs", clear_cache=clear_cache)
        if not self._tab_exists:
            self._create_tab()
        self.data: pd.DataFrame | list[dict] | list[list] = self.read_data()
        self._stored_data_hash = _calculate_data_hash(self.data)
        self._background_writer = None
        self._stop_event = threading.Event()

    def __str__(self):
        return f"Tab '{self.tab_name}'"

    def __repr__(self):
        return self.__str__()

    @property
    def _tab_exists(self):
        try:
            self._worksheet
            return True
        except:
            return False

    @property
    def _worksheet(self):
        return self.sheet.worksheet(self.tab_name)

    @Logger()
    def _create_tab(self):
        """
        Creates a new tab (worksheet) in the Google spreadsheet.

        If the specified tab does not already exist, this method creates a new tab
        with the name provided during the initialization of the `SmartTab` instance.
        The new tab will have default dimensions of 1000 rows and 26 columns.

        Raises:
            Exception: If the tab creation process fails due to API errors or other
                       unexpected issues.

        Notes:
            - This method is called automatically during initialization if the tab
              does not exist.
            - Logs the creation process and success/failure messages.

        """
        self.sheet.add_worksheet(title=self.tab_name, rows=1000, cols=26)
        Logger.note(f"Tab '{self.tab_name}' created.")

    def _read_values(self):
        """
           Reads raw data values from the Google Sheets tab (worksheet).

           This method fetches all the data from the specified tab. Depending on the
           `keep_number_formatting` attribute, it either retrieves the raw, unformatted
           values or the formatted values as they appear in the sheet.

           Returns:
               list[list]: A nested list where each inner list represents a row from
                           the tab.

           Raises:
               Exception: If the data retrieval process fails due to API errors or
                          other unexpected issues.

           Notes:
               - If `keep_number_formatting` is True, formatted values are retrieved
                 (e.g., numbers may include currency symbols or percentages).
               - If `keep_number_formatting` is False, unformatted raw values are
                 returned (e.g., numbers as floats, dates as serials).
               - Handles missing or empty tabs gracefully by returning an empty list.
           """
        if self.keep_number_formatting:
            return self._worksheet.get_all_values()
        else:
            result = self.sheet.values_batch_get(
                    ranges=[self.tab_name],
                    params={"valueRenderOption": "UNFORMATTED_VALUE"}
            )
            values = result.get("valueRanges", [])[0].get("values", [])
            return values

    @Cached()
    @Logger()
    def read_data(self):
        """
            Reads data from the Google Sheets tab and returns it in the specified format.

            This method retrieves all values from the tab and converts them into one of
            the supported formats (`DataFrame`, `list`, or `dict`) based on the
            `data_format` attribute. It handles data type conversions and ensures proper
            column naming.

            Returns:
                Union[pd.DataFrame, list[dict], list[list]]: The tab's data in the
                format specified by `data_format`.

            Raises:
                ValueError: If the tab is empty or contains invalid data.
                Exception: For unexpected errors during the reading process.

            Notes:
                - The first row of the tab is treated as column headers.
                - Columns with missing or empty headers are automatically renamed
                  (e.g., `Column_1`, `Column_2`).
                - Data type conversions:
                    - Tries to convert each column to `int`, then `float`, and finally
                      falls back to `str` if numeric conversion fails.
                - Handles caching to minimize redundant API calls.
            """
        try:
            values = self._read_values()
            if not values or not values[0]:
                Logger.note(f"Tab '{self.tab_name}' is empty or has no headers.")
                return pd.DataFrame()

            df = pd.DataFrame(values[1:], columns=values[0])
            df.columns = [
                    (f"Column"
                     f"_{i + 1}") if not col else col
                    for i, col in enumerate(df.columns)
            ]

            for col in df.columns:
                try:
                    df[col] = df[col].fillna(0).astype(int)
                    continue
                except ValueError:
                    pass
                try:
                    df[col] = df[col].fillna(0).astype(float)
                    continue
                except ValueError:
                    df[col] = df[col].fillna("").astype(str)

            Logger.note(f"Tab '{self.tab_name}' successfully read as DataFrame.")
            if self.data_format == "dict":
                return df.to_dict(orient="records")
            if self.data_format == "list":
                return [df.columns.tolist()] + df.values.tolist()
            return df
        except Exception as e:
            Logger.note(f"Error reading tab '{self.tab_name}': {e}")
            raise

    @property
    def _data_as_list(self):
        if isinstance(self.data, pd.DataFrame):
            values = [self.data.columns.tolist()] + self.data.values.tolist()
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
        """
            Filters rows in the tab's data where the specified column matches a given pattern.

            This method searches for rows in the tab's data where the values in the
            specified column contain the given pattern. The result is returned as a
            Pandas DataFrame.

            Args:
                column (str): The name of the column to filter by.
                    - Must exist in the tab's data; otherwise, an empty DataFrame is returned.
                pattern (str): The pattern to search for within the column values.
                    - Supports regex patterns for advanced matching.

            Returns:
                pd.DataFrame: A DataFrame containing rows that match the pattern in the
                specified column. If no matches are found, an empty DataFrame is returned.

            Raises:
                Exception: For unexpected errors during the filtering process.

            Notes:
                - The column must exist in the tab's data. If it does not, a log message
                  is recorded, and an empty DataFrame is returned.
                - Only rows with non-NaN values in the specified column are considered
                  for matching.
                - The method uses `str.contains()` for pattern matching, which supports
                  regular expressions.
            """

        try:
            df = self._data_as_dataframe
            if column not in df.columns:
                Logger.note(f"Column '{column}' not found in the data.")
                return pd.DataFrame()
            matching_rows = df[df[column].str.contains(pattern, na=False)]
            return matching_rows
        except Exception as e:
            Logger.note(f"Error filtering rows by column '{column}': {e}", mode="short")
            raise

    @Logger(mode="short")
    def write_data(self, overwrite_tab: bool = False, as_table=False):
        """
            Writes the current data to the Google Sheets tab.

            This method writes the data stored in the `SmartTab` object to the associated
            tab in Google Sheets. The operation can either overwrite the entire tab or
            update only the existing data. Optionally, the tab can be formatted as a table.

            Args:
                overwrite_tab (bool): Whether to overwrite the entire tab. Default is False.
                    - If True, clears all existing data before writing.
                    - If False, appends or updates data within the existing tab.
                as_table (bool): Whether to apply table formatting to the written data. Default is False.
                    - Freezes the header row and applies a basic filter.

            Notes:
                - The method checks if the data has changed by comparing hashes (`_stored_data_hash`).
                  If the data has not changed, no write operation is performed.
                - When `as_table` is True, the header row is bolded, and a filter is applied for easy navigation.
                - Logs relevant details, including success and failure messages.
            """
        if self._stored_data_hash == _calculate_data_hash(self.data):
            Logger.note(f"Data for tab '{self.tab_name}' has not changed.")
            return
        try:
            values = self._data_as_list
            if overwrite_tab:
                self._worksheet.clear()
                self._worksheet.update(values, value_input_option='USER_ENTERED')
            else:
                # Prepare range for the batch update
                start_cell = 'A1'
                end_cell = f'{chr(65 + len(values[0]) - 1)}{len(values)}'  # Calculates range based on data size
                self._worksheet.update(f'{start_cell}:{end_cell}', values, value_input_option='USER_ENTERED')
            if as_table:
                self._worksheet.set_basic_filter()
                self._worksheet.freeze(rows=1)
                self._worksheet.format('A1:Z1', {'textFormat': {'bold': True}})

            Logger.note(f"Data written successfully to '{self.tab_name}'.", )

        except Exception as e:
            Logger.note(f"Error writing data to tab '{self.tab_name}': {e}")

    @Logger(mode="short")
    def update_row_by_column_pattern(self, column: str, value, updates: dict):
        """
            Updates a row in the tab's data based on an exact match in a specified column.

            This method searches for the first row in the tab's data where the specified
            column has a value that matches the given `value`. If a match is found, the row
            is updated with the values provided in the `updates` dictionary. If no match
            is found, a new row is added with the `value` and the updates. Missing columns
            are created as needed.

            Args:
                column (str): The name of the column to match.
                    - If the column does not exist, it will be added automatically.
                value: The value to search for in the specified column.
                    - The search is performed using exact matching.
                updates (dict): A dictionary of column-value pairs to update in the matching row.
                    - If a column in the updates does not exist, it will be added automatically.

            Notes:
                - If no matching row is found, a new row is appended to the data.
                - Columns in the updates that do not exist in the tab are created automatically.
                - Data changes are reflected in the `self.data` attribute, respecting the current `data_format`.

            Raises:
                ValueError: If `updates` is not a dictionary or contains invalid keys.
                Exception: For unexpected errors during the update process.

            Usage Example:
                ```python
                # Update the row where "Name" equals "Alice"
                smart_tab.update_row_by_column_pattern(
                    column="Name",
                    value="Alice",
                    updates={"Age": 30, "City": "New York"}
                )

                # Add a new row if no match is found
                smart_tab.update_row_by_column_pattern(
                    column="Name",
                    value="Dave",
                    updates={"Age": 40, "City": "San Francisco"}
                )
                ```
            """
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


    def start_background_write(self, interval=10, overwrite_tab: bool = False, as_table=False):
        """
            Starts a background thread to periodically write data to the Google Sheets tab.

            This method launches a background thread that writes the current data from
            the `SmartTab` object to the associated Google Sheets tab at regular intervals.
            It is useful for keeping the tab data synchronized without blocking the main
            program execution.

            Args:
                interval (int): The interval, in seconds, between consecutive writes. Default is 10 seconds.
                overwrite_tab (bool): Whether to overwrite the entire tab on each write. Default is False.
                    - If True, clears all existing data before writing.
                    - If False, appends or updates data within the existing tab.
                as_table (bool): Whether to apply table formatting to the written data. Default is False.
                    - Freezes the header row and applies a basic filter for easy navigation.

            Notes:
                - The background thread continues to run until explicitly stopped using `stop_background_write`.
                - Logs any errors encountered during the write operation.
                - Only writes data if there are changes detected in `self.data`.
                - Uses a daemon thread to ensure it terminates when the main program exits.

            Raises:
                Exception: If a background writer is already running.

            Usage Example:
                ```python
                # Start background writing with 15-second intervals
                smart_tab.start_background_write(interval=15, overwrite_tab=True, as_table=True)

                # Stop the background writer
                smart_tab.stop_background_write()
                ```
            """
        if self._background_writer and self._background_writer.is_alive():
            Logger.note("Background write already running. Stop it first.")
            return

        self._stop_event.clear()

        def writer():
            while not self._stop_event.is_set():
                try:
                    if self.data is not None:
                        self.write_data(overwrite_tab=overwrite_tab, as_table=as_table)
                except Exception as e:
                    Logger.note(f"Error during background write: {e}")
                time.sleep(interval)

        self._background_writer = threading.Thread(target=writer, daemon=True)
        self._background_writer.start()

    def stop_background_write(self):
        if self._background_writer:
            self._stop_event.set()
            self._background_writer.join()
            Logger.note(f"Background write for tab '{self.tab_name}' stopped.")
