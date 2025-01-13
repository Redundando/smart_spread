import time
import pandas as pd
import numpy as np
from smart_spread.smart_spread import SmartSpread

s = SmartSpread(key_file="sheets-407013-4ed6be3cc1ab.json", sheet_identifier="187BLSoxsXg5MDpKCM2cqHN4rlH1OdP58AeOhEwBrHSA", user_email="arved.kloehn@gmail.com", clear_cache=False)

t = s.tab("test 1", data_format="DataFrame", keep_number_formatting=False, clear_cache=True,)
print(t.data)