"""Test to verify pd.NA values don't leak into list/dict output"""
import pandas as pd
import json

# Simulate what read_data does
df = pd.DataFrame({
    'id': [1, 2, None, None],
    'name': ['Alice', 'Bob', 'Charlie', 'Dave'],
    'score': [100, None, 85, None]
})

# Convert to Int64 (as done in read_data)
df['id'] = df['id'].astype('Int64')
df['score'] = df['score'].astype('Int64')

print("DataFrame:")
print(df)
print(f"\nTypes: id={df['id'].dtype}, score={df['score'].dtype}")

# Test list format WITH sanitization
data_as_list = [df.columns.tolist()] + [[None if pd.isna(v) else v for v in row] for row in df.values.tolist()]
print(f"\nSanitized list format:")
for i, row in enumerate(data_as_list):
    print(f"  Row {i}: {row}")

# Test JSON serialization
try:
    json_str = json.dumps(data_as_list)
    print(f"\n✓ List JSON serialization succeeded")
except TypeError as e:
    print(f"\n✗ List JSON serialization failed: {e}")

# Test dict format WITH sanitization
result = df.to_dict(orient="records")
data_as_dict = [{k: (None if pd.isna(v) else v) for k, v in row.items()} for row in result]
print(f"\nSanitized dict format:")
for i, row in enumerate(data_as_dict):
    print(f"  Row {i}: {row}")

# Test JSON serialization
try:
    json_str = json.dumps(data_as_dict)
    print(f"\n✓ Dict JSON serialization succeeded")
except TypeError as e:
    print(f"\n✗ Dict JSON serialization failed: {e}")
