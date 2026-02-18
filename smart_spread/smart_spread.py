import gspread
from gspread import Spreadsheet
from logorator import Logger
from typing import Union, Dict, Optional, Literal
from functools import cached_property

from . import smart_tab


class SmartSpread:
    """High-level interface for managing Google Sheets spreadsheets.
    
    Provides methods to create, access, and manage spreadsheets and their tabs
    with automatic authentication and caching.
    """

    def __init__(
        self,
        sheet_identifier: str = "",
        user_email: Optional[str] = None,
        key_file: Optional[str] = None,
        service_account_data: Optional[Dict] = None,
    ):
        """Initialize SmartSpread with Google Sheets credentials.
        
        Args:
            sheet_identifier: Spreadsheet ID or name
            user_email: Email to grant access to (optional)
            key_file: Path to service account JSON credentials file
            service_account_data: Service account credentials as dict
            
        Raises:
            ValueError: If neither key_file nor service_account_data provided
        """
        self.user_email = user_email
        self.sheet_identifier = sheet_identifier

        if service_account_data:
            # Auth from dict
            try:
                self.gc = gspread.service_account_from_dict(service_account_data)
            except Exception as e:
                Logger.note(f"Failed to authenticate using service_account_data: {e}", mode="short")
                raise ValueError("Invalid service_account_data provided") from e
        elif key_file:
            # Auth from file
            try:
                self.gc = gspread.service_account(filename=key_file)
            except Exception as e:
                Logger.note(f"Failed to authenticate using key_file: {e}", mode="short")
                raise ValueError("Invalid key_file provided") from e
        else:
            raise ValueError("Must provide either a 'key_file' path or 'service_account_data' for authentication.")


    def __str__(self):
        return self.sheet_identifier

    def __repr__(self):
        return self.__str__()

    @cached_property
    def sheet(self) -> Spreadsheet:
        """Get the spreadsheet object, trying by ID first then by name.
        
        Returns:
            gspread.Spreadsheet: The spreadsheet object
            
        Raises:
            ValueError: If spreadsheet not found
        """
        try:
            sheet = self.gc.open_by_key(self.sheet_identifier)
            Logger.note(f"Spreadsheet '{sheet.title}' successfully opened by ID.")
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            pass
        
        try:
            sheet = self.gc.open(self.sheet_identifier)
            Logger.note(f"Spreadsheet '{sheet.title}' successfully opened by name.")
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            Logger.note(f"Spreadsheet '{self.sheet_identifier}' not found.")
            raise ValueError(f"Spreadsheet '{self.sheet_identifier}' not found. Create it first using _create_sheet().")

    @Logger(mode="short")
    def _create_sheet(self, share_publicly: bool = False) -> Spreadsheet:
        """Create a new spreadsheet.
        
        Args:
            share_publicly: If True, share with anyone with write access
            
        Returns:
            gspread.Spreadsheet: The newly created spreadsheet
        """
        Logger.note(f"Creating a new spreadsheet ('{self.sheet_identifier}').", mode="short")
        new_sheet = self.gc.create(self.sheet_identifier)
        
        if share_publicly:
            new_sheet.share(email_address=None, perm_type="anyone", role="writer")
            Logger.note("Spreadsheet shared publicly with write access.", mode="short")
        
        if self.user_email:
            new_sheet.share(email_address=self.user_email, perm_type="user", role="writer")
            Logger.note(f"Access granted to {self.user_email}.", mode="short")
        
        return new_sheet

    @Logger(mode="short")
    def grant_access(self, email: Optional[str] = None, role: str = "owner"):
        """Grant access to the spreadsheet.
        
        Args:
            email: Email address to grant access to. If None, grants to anyone
            role: Permission role ('owner', 'writer', 'reader')
            
        Raises:
            RuntimeError: If granting access fails
        """
        try:
            if email:
                self.sheet.share(email, perm_type="user", role=role)
                Logger.note(f"Access granted to '{email}' with role '{role}' for sheet '{self.sheet.title}'.", mode="short")
            else:
                self.sheet.share(email_address=None, perm_type="anyone", role=role)
                Logger.note(f"Access granted to anyone with role '{role}' for sheet '{self.sheet.title}'.", mode="short")
        except Exception as e:
            Logger.note(f"Error granting access: {e}", mode="short")
            raise RuntimeError(f"Failed to grant access to spreadsheet: {e}") from e

    @property
    def url(self) -> str:
        """Get the spreadsheet URL.
        
        Returns:
            str: The spreadsheet URL
        """
        return self.sheet.url

    def tab(self, tab_name: str = "Sheet 1", data_format: Literal["DataFrame", "list", "dict"] = "DataFrame", keep_number_formatting: bool = False) -> "smart_tab.SmartTab":
        """Get or create a tab in the spreadsheet.
        
        Args:
            tab_name: Name of the tab
            data_format: Format for data operations ('DataFrame', 'list', 'dict')
            keep_number_formatting: If True, preserve number formatting as strings
            
        Returns:
            SmartTab: Tab interface object
        """
        tab = smart_tab.SmartTab(sheet=self.sheet, tab_name=tab_name, data_format=data_format, keep_number_formatting=keep_number_formatting)
        
        # Invalidate tab_names cache since a new tab may have been created
        try:
            del self.tab_names
        except AttributeError:
            pass
        
        return tab

    @cached_property
    def tab_names(self) -> list[str]:
        """Get list of all tab names in the spreadsheet.
        
        Returns:
            list[str]: List of tab names
            
        Raises:
            RuntimeError: If fetching tab names fails
        """
        try:
            return [worksheet.title for worksheet in self.sheet.worksheets()]
        except Exception as e:
            Logger.note(f"Error fetching tab names: {e}", mode="short")
            raise RuntimeError(f"Failed to fetch tab names: {e}") from e



    def tab_exists(self, tab_name: str) -> bool:
        """Check if a tab exists in the spreadsheet.
        
        Args:
            tab_name: Name of the tab to check
            
        Returns:
            bool: True if tab exists, False otherwise
            
        Raises:
            ValueError: If tab_name is empty
            RuntimeError: If check fails
        """
        if not tab_name:
            raise ValueError("tab_name cannot be empty")
        try:
            self.sheet.worksheet(tab_name)
            return True
        except gspread.exceptions.WorksheetNotFound:
            return False
        except Exception as e:
            Logger.note(f"Error checking if tab exists: {e}", mode="short")
            raise RuntimeError(f"Failed to check if tab '{tab_name}' exists: {e}") from e
    
    def refresh(self) -> None:
        """Clear all cached properties to force refresh from Google Sheets.
        
        Use this after external changes to reload spreadsheet metadata.
        """
        try:
            del self.sheet
        except AttributeError:
            pass
        try:
            del self.tab_names
        except AttributeError:
            pass
