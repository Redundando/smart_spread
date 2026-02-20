import json
import pytest
import pandas as pd
import time
from smartspread import SmartSpread, SmartTab
from smartspread.smart_tab import _calculate_data_hash


@pytest.fixture(scope="session")
def credentials():
    with open("config.json", "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def test_sheet_name():
    return f"SmartSpread_Test_{int(time.time())}"


@pytest.fixture(scope="session")
def spread(credentials, test_sheet_name):
    s = SmartSpread(
        sheet_identifier=test_sheet_name,
        service_account_data=credentials
    )
    try:
        _ = s.sheet
    except ValueError:
        s._create_sheet()
    return s


class TestSmartSpread:
    
    def test_create_spreadsheet(self, spread):
        assert spread.sheet is not None
        assert spread.sheet.title is not None
    
    def test_get_url(self, spread):
        url = spread.url
        assert url.startswith("https://docs.google.com/spreadsheets/")
    
    def test_tab_names(self, spread):
        names = spread.tab_names
        assert isinstance(names, list)
        assert len(names) > 0


class TestSmartTab:
    
    def test_create_tab_with_dataframe(self, spread):
        df = pd.DataFrame({
            "Name": ["Alice", "Bob", "Charlie"],
            "Age": [25, 30, 35],
            "City": ["NYC", "LA", "Chicago"]
        })
        
        tab = spread.tab(tab_name="TestTab_DF", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True, as_table=True)
        
        tab_read = spread.tab(tab_name="TestTab_DF", data_format="DataFrame")
        assert isinstance(tab_read.data, pd.DataFrame)
        assert len(tab_read.data) == 3
        assert list(tab_read.data.columns) == ["Name", "Age", "City"]
    
    def test_create_tab_with_dict(self, spread):
        data = [
            {"Product": "Apple", "Price": 1.5, "Stock": 100},
            {"Product": "Banana", "Price": 0.8, "Stock": 150}
        ]
        
        df = pd.DataFrame(data)
        tab = spread.tab(tab_name="TestTab_Dict", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_read = spread.tab(tab_name="TestTab_Dict", data_format="dict")
        assert isinstance(tab_read.data, list)
        assert len(tab_read.data) == 2
        assert tab_read.data[0]["Product"] == "Apple"
    
    def test_create_tab_with_list(self, spread):
        df = pd.DataFrame({
            "X": [1, 2, 3],
            "Y": [4, 5, 6]
        })
        
        tab = spread.tab(tab_name="TestTab_List", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_read = spread.tab(tab_name="TestTab_List", data_format="list")
        assert isinstance(tab_read.data, list)
        assert tab_read.data[0] == ["X", "Y"]
        assert len(tab_read.data) == 4
    
    def test_update_row_by_column_pattern(self, spread):
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "Status": ["pending", "pending", "pending"]
        })
        
        tab = spread.tab(tab_name="TestTab_Update", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab.update_row_by_column_pattern(
            column="ID",
            value=2,
            updates={"Status": "completed"}
        )
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_read = spread.tab(tab_name="TestTab_Update", data_format="DataFrame")
        row = tab_read.data[tab_read.data["ID"] == 2]
        assert row["Status"].values[0] == "completed"
    
    def test_filter_rows_by_column(self, spread):
        df = pd.DataFrame({
            "Name": ["Alice", "Bob", "Alex", "Charlie"],
            "Score": [85, 90, 88, 75]
        })
        
        tab = spread.tab(tab_name="TestTab_Filter", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        filtered = tab.filter_rows_by_column("Name", "Al")
        assert len(filtered) == 2
        assert "Alice" in filtered["Name"].values
        assert "Alex" in filtered["Name"].values
    
    def test_tab_exists(self, spread):
        tab_name = "TestTab_Exists"
        spread.tab(tab_name=tab_name)
        assert spread.tab_exists(tab_name) is True
        assert spread.tab_exists("NonExistentTab") is False
    
    def test_write_data_no_change(self, spread):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        tab = spread.tab(tab_name="TestTab_NoChange", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab.write_data(overwrite_tab=True)
        assert tab._stored_data_hash is not None
    
    def test_sparse_columns(self, spread):
        df = pd.DataFrame({
            "Name": ["Alice", "Bob", "Charlie"],
            "Age": [25, 30, 35],
            "Email": ["", "", ""],
            "Phone": ["", "", ""],
            "City": ["NYC", "LA", "Chicago"]
        })
        
        tab = spread.tab(tab_name="TestTab_Sparse", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True, as_table=True)
        
        tab_read = spread.tab(tab_name="TestTab_Sparse", data_format="DataFrame")
        assert isinstance(tab_read.data, pd.DataFrame)
        assert len(tab_read.data) == 3
        assert list(tab_read.data.columns) == ["Name", "Age", "Email", "Phone", "City"]
        assert tab_read.data["Name"].tolist() == ["Alice", "Bob", "Charlie"]
        assert tab_read.data["City"].tolist() == ["NYC", "LA", "Chicago"]
        assert tab_read.data["Email"].isna().all()
        assert tab_read.data["Phone"].isna().all()
    
    def test_nan_roundtrip(self, spread):
        df = pd.DataFrame({
            "A": [1, 2, 3],
            "B": ["x", "", "z"],
            "C": [None, None, None]
        })
        
        tab = spread.tab(tab_name="TestTab_NaN", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_read = spread.tab(tab_name="TestTab_NaN", data_format="DataFrame")
        assert len(tab_read.data) == 3
        assert tab_read.data["A"].tolist() == [1, 2, 3]
        assert tab_read.data["B"].tolist()[0] == "x"
        assert pd.isna(tab_read.data["B"].tolist()[1])
        assert tab_read.data["C"].isna().all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestExceptions:
    
    def test_smartspread_no_credentials(self):
        with pytest.raises(ValueError, match="Must provide either"):
            SmartSpread(sheet_identifier="test")
    
    def test_smartspread_invalid_credentials(self):
        with pytest.raises(ValueError, match="Invalid service_account_data"):
            SmartSpread(sheet_identifier="test", service_account_data={"invalid": "data"})
    
    def test_smarttab_empty_tab_name(self, spread):
        with pytest.raises(ValueError, match="tab_name cannot be empty"):
            SmartTab(sheet=spread.sheet, tab_name="")
    
    def test_smarttab_invalid_data_format(self, spread):
        with pytest.raises(ValueError, match="Invalid data_format"):
            SmartTab(sheet=spread.sheet, tab_name="Test", data_format="invalid")
    
    def test_smarttab_no_sheet(self):
        with pytest.raises(ValueError, match="sheet parameter is required"):
            SmartTab(sheet=None, tab_name="Test")
    
    def test_filter_empty_column(self, spread):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        tab = spread.tab(tab_name="TestTab_FilterErr", data_format="DataFrame")
        tab.data = df
        with pytest.raises(ValueError, match="column parameter cannot be empty"):
            tab.filter_rows_by_column("", "test")
    
    def test_filter_empty_pattern(self, spread):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        tab = spread.tab(tab_name="TestTab_FilterErr2", data_format="DataFrame")
        tab.data = df
        with pytest.raises(ValueError, match="pattern parameter cannot be empty"):
            tab.filter_rows_by_column("A", "")
    
    def test_filter_column_not_found(self, spread):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        tab = spread.tab(tab_name="TestTab_FilterErr3", data_format="DataFrame")
        tab.data = df
        with pytest.raises(ValueError, match="Column 'Z' not found"):
            tab.filter_rows_by_column("Z", "test")
    
    def test_update_row_empty_column(self, spread):
        df = pd.DataFrame({"A": [1, 2]})
        tab = spread.tab(tab_name="TestTab_UpdateErr", data_format="DataFrame")
        tab.data = df
        with pytest.raises(ValueError, match="column parameter cannot be empty"):
            tab.update_row_by_column_pattern("", 1, {"A": 2})
    
    def test_update_row_invalid_updates(self, spread):
        df = pd.DataFrame({"A": [1, 2]})
        tab = spread.tab(tab_name="TestTab_UpdateErr2", data_format="DataFrame")
        tab.data = df
        with pytest.raises(TypeError, match="updates parameter must be a dictionary"):
            tab.update_row_by_column_pattern("A", 1, "invalid")
    
    def test_update_row_empty_updates(self, spread):
        df = pd.DataFrame({"A": [1, 2]})
        tab = spread.tab(tab_name="TestTab_UpdateErr3", data_format="DataFrame")
        tab.data = df
        with pytest.raises(ValueError, match="updates dictionary cannot be empty"):
            tab.update_row_by_column_pattern("A", 1, {})
    
    def test_tab_exists_empty_name(self, spread):
        with pytest.raises(ValueError, match="tab_name cannot be empty"):
            spread.tab_exists("")


class TestRefresh:
    
    def test_smartspread_refresh(self, spread):
        _ = spread.sheet
        _ = spread.tab_names
        assert 'sheet' in spread.__dict__
        assert 'tab_names' in spread.__dict__
        spread.refresh()
        assert 'sheet' not in spread.__dict__
        assert 'tab_names' not in spread.__dict__
    
    def test_smarttab_refresh(self, spread):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        tab = spread.tab(tab_name="TestTab_Refresh", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        old_hash = tab._stored_data_hash
        tab.refresh()
        assert tab._stored_data_hash == old_hash
        assert isinstance(tab.data, pd.DataFrame)


class TestDataHash:
    
    def test_hash_with_pd_na_in_list(self):
        df = pd.DataFrame({'id': [1, 2, None], 'name': ['Alice', 'Bob', 'Charlie']})
        df['id'] = df['id'].astype('Int64')
        data_as_list = [df.columns.tolist()] + df.values.tolist()
        hash_value = _calculate_data_hash(data_as_list)
        assert isinstance(hash_value, str)
    
    def test_hash_with_pd_na_in_dict(self):
        df = pd.DataFrame({'id': [1, None], 'name': ['Alice', 'Bob']})
        df['id'] = df['id'].astype('Int64')
        data_as_dict = df.to_dict(orient='records')
        hash_value = _calculate_data_hash(data_as_dict)
        assert isinstance(hash_value, str)
    
    def test_hash_with_dataframe(self):
        df = pd.DataFrame({'id': [1, None], 'name': ['Alice', 'Bob']})
        df['id'] = df['id'].astype('Int64')
        hash_value = _calculate_data_hash(df)
        assert isinstance(hash_value, str)
    
    def test_list_format_sanitizes_pd_na(self, spread):
        df = pd.DataFrame({'id': [1, None], 'name': ['Alice', 'Bob']})
        tab = spread.tab(tab_name="TestTab_ListNA", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_list = spread.tab(tab_name="TestTab_ListNA", data_format="list")
        # Verify no pd.NA in output
        import json
        json.dumps(tab_list.data)  # Should not raise TypeError
        assert tab_list.data[2][0] is None  # Second row, first column should be None
    
    def test_dict_format_sanitizes_pd_na(self, spread):
        df = pd.DataFrame({'id': [1, None], 'name': ['Alice', 'Bob']})
        tab = spread.tab(tab_name="TestTab_DictNA", data_format="DataFrame")
        tab.data = df
        tab._stored_data_hash = None
        tab.write_data(overwrite_tab=True)
        
        tab_dict = spread.tab(tab_name="TestTab_DictNA", data_format="dict")
        # Verify no pd.NA in output
        import json
        json.dumps(tab_dict.data)  # Should not raise TypeError
        assert tab_dict.data[1]['id'] is None  # Second row id should be None
