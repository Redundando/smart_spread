import gspread
from cacherator import JSONCache, Cached
from logorator import Logger
import pandas as pd

class SmartSpread(JSONCache):

    def __init__(self,
                 sheet_identifier="",
                 directory = "data/smart_spread",
                 user_email = None,
                 key_file = "",
                 clear_cache = False):
        super().__init__(directory=directory, data_id=f"{sheet_identifier}", clear_cache=clear_cache)
        self.user_email = user_email
        self.key_file = key_file
        self.sheet_identifier = sheet_identifier
        self.gc = gspread.service_account(filename=key_file)



    @property
    @Cached()
    def sheet(self):
        try:
            try:
                # Attempt to open by ID
                sheet = self.gc.open_by_key(self.sheet_identifier)
                Logger.note(f"Spreadsheet '{sheet.title}' successfully opened by ID.")
            except gspread.exceptions.SpreadsheetNotFound:
                # If not found by ID, try to open by name
                sheet = self.gc.open(self.sheet_identifier)
                Logger.note(f"Spreadsheet '{sheet.title}' successfully opened by name.")
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            Logger.note(f"Spreadsheet '{self.sheet_identifier}' not found.")
            return self.create_sheet()

    @Logger(mode="short")
    def create_sheet(self):
        Logger.note(f"Creating a new spreadsheet ('{self.sheet_identifier}').", mode="short")
        try:
            # Create a new spreadsheet if it does not exist
            new_sheet = self.gc.create(self.sheet_identifier)
            if self.user_email:
                new_sheet.share(email_address=self.user_email,perm_type="user", role="writer")
                Logger.note(f"Access granted to {self.user_email}.", mode="short")
            return new_sheet
        except Exception as e:
            Logger.note(f"Error creating spreadsheet: {e}", mode="short")
            raise



    @Logger(mode="short")
    def grant_access(self, email:str=None, role:str="owner"):
        if not self.sheet:
            raise ValueError("No spreadsheet is currently opened. Please open or create a sheet first.")
        try:
            self.sheet.share(email, perm_type="user", role=role)
            Logger.note(f"Access granted to '{email}' with role '{role}' for sheet '{self.sheet.title}'.", mode="short")
        except Exception as e:
            Logger.note(f"Error granting access to '{email}': {e}", mode="short")
            raise

    @property
    @Cached()
    def url(self):
        return self.sheet.url

    @property
    @Cached()
    def tab_names(self):
        if not self.sheet:
            raise ValueError("No spreadsheet is currently opened. Please open a sheet first.")

        try:
            tab_names = [worksheet.title for worksheet in self.sheet.worksheets()]
            return tab_names
        except Exception as e:
            Logger.note(f"Error fetching tab names: {e}", mode="short")
            raise

    @Cached()
    @Logger(mode="short")
    def get_tab_values(self, tab_name:str=None):
        if not self.sheet:
            Logger.note("No spreadsheet is currently opened. Please open or create a sheet first.", mode="short")
            raise ValueError("No spreadsheet is currently opened. Please open or create a sheet first.")

        try:
            if tab_name is None:
                tab_name = self.tab_names[0]
            worksheet = self.sheet.worksheet(tab_name)
            data = worksheet.get_all_values()
            return data
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError(f"Worksheet '{tab_name}' not found in spreadsheet '{self.sheet.title}'.")
        except Exception as e:
            Logger.note(f"Error retrieving data from worksheet '{tab_name}': {e}", mode="short")
            raise

    def tab_to_list(self, tab_name: str = None):
        return self.get_tab_values(tab_name=tab_name)

    @Cached()
    def tab_to_flat_list(self, tab_name: str = None):
        try:
            data = self.get_tab_values(tab_name)
            return [item for row in data for item in row]
        except Exception as e:
            Logger.note(f"Error converting tab values to list: {e}", mode="short")
            raise

    @Cached()
    @Logger(mode="short")
    def tab_to_dict(self, tab_name: str = None):
        try:
            data = self.get_tab_values(tab_name)
            if len(data) < 2:
                raise ValueError("Insufficient data to create a dictionary. Need at least headers and one row.")
            headers = data[0]
            rows = data[1:]
            return [dict(zip(headers, row)) for row in rows]
        except Exception as e:
            Logger.note(f"Error converting tab values to dict: {e}", mode="short")
            raise

    @Cached()
    @Logger(mode="short")
    def tab_to_df(self, tab_name: str = None):
        try:
            data = self.get_tab_values(tab_name)
            if len(data) < 2:
                raise ValueError("Insufficient data to create a DataFrame. Need at least headers and one row.")
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        except Exception as e:
            Logger.note(f"Error converting tab values to DataFrame: {e}", mode="short")
            raise

    @Logger(mode="short")
    def filter_rows_by_column(self, tab_name: str, column_name: str, pattern: str):
        try:
            df = self.tab_to_df(tab_name)
            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' not found in the data.")
            matching_rows = df[df[column_name].str.contains(pattern, na=False)]
            return matching_rows
        except Exception as e:
            Logger.note(f"Error filtering rows by column '{column_name}': {e}", mode="short")
            raise

    @Logger(mode="short")
    def update_row_by_column_pattern(self, tab_name: str, column_name: str, pattern: str, updates: dict):
        try:
            worksheet = self.sheet.worksheet(tab_name)
            df = self.tab_to_df(tab_name)
            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' not found in the data.")

            # Find the first matching row index
            matching_row_index = df[df[column_name].str.contains(pattern, na=False)].index[0]

            # Add missing columns and apply updates
            headers = df.columns.tolist()
            row = worksheet.row_values(matching_row_index + 2)  # Adjust for 1-based index and header row
            while len(row) < len(headers):
                row.append("")

            # Update only the modified columns
            for col, value in updates.items():
                if col not in headers:
                    headers.append(col)
                    worksheet.update_cell(1, len(headers), col)
                col_idx = headers.index(col) + 1
                worksheet.update_cell(matching_row_index + 2, col_idx, value)

            Logger.note(f"Row updated successfully in tab '{tab_name}'.", mode="short")

        except Exception as e:
            Logger.note(f"Error updating row by column pattern: {e}", mode="short")
            raise


    def tab_exists(self, tab_name: str) -> bool:
        try:
            # Attempt to get the worksheet by name
            self.sheet.worksheet(tab_name)
            return True
        except gspread.exceptions.WorksheetNotFound:
            return False


    @Logger(mode="short")
    def write_to_tab(self, data, tab_name: str, overwrite_tab: bool = False):
        try:
            if self.tab_exists(tab_name):
                worksheet = self.sheet.worksheet(tab_name)
            else:
                Logger.note(f"Tab '{tab_name}' not found. Creating new tab.")
                worksheet = self.sheet.add_worksheet(title=tab_name, rows=1000, cols=26)

            # Prepare data
            if isinstance(data, pd.DataFrame):
                values = [data.columns.tolist()] + data.values.tolist()
            elif isinstance(data, list) and all(isinstance(row, dict) for row in data):
                keys = list(data[0].keys())
                values = [keys] + [[row.get(k, "") for k in keys] for row in data]
            elif isinstance(data, list) and all(isinstance(row, list) for row in data):
                values = data
            else:
                raise ValueError("Unsupported data format. Provide a DataFrame, List of Lists, or List of Dicts.")

            # Overwrite behavior
            if overwrite_tab:
                worksheet.clear()
                worksheet.update(values)
            else:
                # Prepare range for the batch update
                start_cell = 'A1'
                end_cell = f'{chr(65 + len(values[0]) - 1)}{len(values)}'  # Calculates range based on data size
                worksheet.update(f'{start_cell}:{end_cell}', values)

            Logger.note(f"Data written successfully to '{tab_name}'.",)

        except Exception as e:
            Logger.note(f"Error writing data to tab '{tab_name}': {e}")
            raise