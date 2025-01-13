import gspread
from cacherator import Cached, JSONCache
from gspread import Spreadsheet
from logorator import Logger
from typing import Union

from smart_spread import smart_tab


class SmartSpread(JSONCache):
    """
        A utility class for managing Google Sheets at the spreadsheet level.

        SmartSpread provides functionality to interact with a Google spreadsheet,
        including creating new spreadsheets, managing access, retrieving tabs, and
        caching data for improved performance.

        Attributes:
            sheet_identifier (str): Identifier for the spreadsheet, either its name or ID.
            directory (str): Directory for storing cached data.
            user_email (str): Email of the user to share the spreadsheet with (optional).
            key_file (str): Path to the Google service account key file for authentication.
            clear_cache (bool): Whether to clear the cache on initialization.

        Methods:
            sheet: Retrieves the spreadsheet object, creating it if it doesn't exist.
            create_sheet(): Creates a new spreadsheet.
            grant_access(email, role): Grants access to the spreadsheet for a user.
            url: Returns the URL of the spreadsheet.
            tab(tab_name, data_format, keep_number_formatting, clear_cache):
                Creates or retrieves a `SmartTab` object for the specified tab.
            tab_names: Returns a list of tab names in the spreadsheet.
            tab_exists(tab_name): Checks if a tab with the given name exists in the spreadsheet.
        """

    def __init__(self,
                 sheet_identifier="",
                 directory="data/smart_spread",
                 user_email=None,
                 key_file="",
                 clear_cache=False):
        """
            Initializes a SmartSpread object for managing a Google spreadsheet.

            Args:
                sheet_identifier (str): Identifier for the spreadsheet, either its name or ID.
                    - If the spreadsheet is not found, a new one can be created.
                directory (str): Directory for storing cached data. Default is "data/smart_spread".
                user_email (str): Email address to share the spreadsheet with. Default is None.
                    - If provided, the email will be granted access to the spreadsheet.
                key_file (str): Path to the Google service account key file used for authentication.
                    - Required for accessing Google Sheets API.
                clear_cache (bool): Whether to clear existing cache data on initialization. Default is False.

            Raises:
                ValueError: If the provided `key_file` is invalid or the authentication fails.
            """
        super().__init__(directory=directory, data_id=f"{sheet_identifier}", clear_cache=clear_cache)
        self.user_email = user_email
        self.key_file = key_file
        self.sheet_identifier = sheet_identifier
        self.gc = gspread.service_account(filename=key_file)

    def __str__(self):
        return self.sheet.title

    def __repr__(self):
        return self.__str__()

    @property
    @Cached()
    def sheet(self) -> Spreadsheet:
        """
            Retrieves the Google Sheets object associated with this SmartSpread instance.

            This method attempts to open the spreadsheet by its ID or name.
            If the spreadsheet does not exist, it creates a new one.

            Returns:
                gspread.Spreadsheet: The Google Sheets object representing the spreadsheet.

            Raises:
                gspread.exceptions.SpreadsheetNotFound: If the spreadsheet cannot be found
                    and creating a new spreadsheet fails.

            Notes:
                - If the spreadsheet is found by ID, it logs success.
                - If the spreadsheet is found by name after failing to locate it by ID,
                  it also logs success.
                - If neither method succeeds, a new spreadsheet is created, and a log
                  entry is recorded.
            """
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
            return self._create_sheet()

    @Logger(mode="short")
    def _create_sheet(self) -> Spreadsheet:
        """
            Creates a new Google spreadsheet with the identifier provided.

            If a spreadsheet with the specified identifier does not exist, this method
            creates a new one. Optionally, it grants access to a specified user email
            with write permissions.

            Returns:
                gspread.Spreadsheet: The newly created Google spreadsheet object.

            Raises:
                Exception: If an error occurs while creating the spreadsheet or
                           granting access.

            Notes:
                - If `user_email` is provided during initialization, it is granted write
                  access to the spreadsheet.
            """
        Logger.note(f"Creating a new spreadsheet ('{self.sheet_identifier}').", mode="short")
        try:
            new_sheet = self.gc.create(self.sheet_identifier)
            if self.user_email:
                new_sheet.share(email_address=self.user_email, perm_type="user", role="writer")
                Logger.note(f"Access granted to {self.user_email}.", mode="short")
            return new_sheet
        except Exception as e:
            Logger.note(f"Error creating spreadsheet: {e}", mode="short")
            raise

    @Logger(mode="short")
    def grant_access(self, email: str = None, role: str = "owner"):
        """
            Grants access to the Google spreadsheet for a specific user.

            This method allows sharing the spreadsheet with another user by providing
            their email address and assigning them a specific role (e.g., owner, writer,
            reader).

            Args:
                email (str): The email address of the user to share the spreadsheet with.
                    - Required to identify the user to grant access.
                role (str): The role to assign to the user. Default is "owner".
                    - Supported roles: "owner", "writer", "reader".

            Raises:
                ValueError: If the spreadsheet has not been initialized or opened.
                Exception: If there is an error during the access granting process.

            Notes:
                - The spreadsheet must already exist before calling this method.
            """

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

    @Cached()
    def tab(self, tab_name: str="Sheet 1", data_format:Union["DataFrame", "list", "dict"]="DataFrame", keep_number_formatting:bool=False, clear_cache:bool=True) -> smart_tab.SmartTab:
        """
            Creates or retrieves a SmartTab object for a specific tab in the spreadsheet.

            The `tab` method initializes a `SmartTab` object, allowing interaction with
            an individual tab (worksheet) in the spreadsheet. If the tab does not
            already exist, it will be created.

            Args:
                tab_name (str): The name of the tab (worksheet) to retrieve or create.
                    - Default: "Sheet 1".
                data_format (str): The format for the tab's data. Default is an empty string.
                    - Supported formats: "DataFrame", "list", "dict".
                keep_number_formatting (bool): Whether to preserve number formatting
                    from Google Sheets. Default is False.
                clear_cache (bool): Whether to clear cached data for the tab. Default is True.

            Returns:
                SmartTab: An instance of the SmartTab class for interacting with the specified tab.

            Notes:
                - The `SmartTab` object provides functionality for reading, writing, and
                  updating data in the tab.
                - This method integrates with caching to improve performance and reduce
                  redundant API calls.
            """
        return smart_tab.SmartTab(sheet=self.sheet, tab_name=tab_name, data_format=data_format, keep_number_formatting=keep_number_formatting, clear_cache=clear_cache)

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



    def tab_exists(self, tab_name: str) -> bool:
        try:
            # Attempt to get the worksheet by name
            self.sheet.worksheet(tab_name)
            return True
        except gspread.exceptions.WorksheetNotFound:
            return False
