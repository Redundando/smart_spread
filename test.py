import pandas as pd
import numpy as np
from smart_spread.smart_spread import SmartSpread

s = SmartSpread(key_file="sheets-407013-4ed6be3cc1ab.json", sheet_identifier="187BLSoxsXg5MDpKCM2cqHN4rlH1OdP58AeOhEwBrHSA", user_email="arved.kloehn@gmail.com", clear_cache=True)
#s.open("Cuckoo Settings")
print(s.tab_names)
df = pd.DataFrame(np.random.randint(0, 100, size=(10, 4)), columns=['A', 'B', 'C', 'D'])
list_of_dicts = df.to_dict(orient='records')
s.write_to_tab(tab_name="test", data=list_of_dicts)
#print(s.url)
#print(s.tab_to_df(tab_name=("Einkaufen")))
#print(s.update_row_by_column_pattern(tab_name="Einkaufen", column_name="Produkt", pattern="Eier$", updates={"Anzahl": 40, "Gekauft": True}))
#print(s.filter_rows_by_column(tab_name="Einkaufen", column_name="Produkt", pattern="Eier$"))
#s.grant_access(s.owner_email)
#wks = s.gc.open("Cuckoo Settings").sheet1
#print(wks)