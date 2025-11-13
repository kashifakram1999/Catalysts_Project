import re

# Test the engine size extraction regex
test_strings = [
    "1.6L Honda Civics",
    "2.9L Ford PC",
    "3.5l Toyota",
    "1.6 L Honda",
    "Honda Civic",
]

pattern = r'(\d+\.?\d*)[Ll]'

for test in test_strings:
    match = re.search(pattern, test)
    if match:
        print(f"'{test}' -> Engine: {match.group(1)}")
    else:
        print(f"'{test}' -> No match")
