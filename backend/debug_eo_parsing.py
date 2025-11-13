import PyPDF2
import re

pdf_path = "/Users/muhmmadkashif/Desktop/Data.pdf"

with open(pdf_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)

    # Get page 2 (where Magnaflow data is)
    page = pdf_reader.pages[1]
    text = page.extract_text()
    lines = text.split('\n')

    print("Looking for D-193-65 in PDF...")
    print()

    for i, line in enumerate(lines):
        if 'D-193-65' in line:
            print(f"Line {i}: '{line}'")
            print()
            print("Context (previous 3 lines):")
            for j in range(max(0, i-3), i):
                print(f"  Line {j}: '{lines[j]}'")
            print()
            print("Context (next 3 lines):")
            for j in range(i+1, min(len(lines), i+4)):
                print(f"  Line {j}: '{lines[j]}'")
            print()

            # Test the regex pattern
            print("Testing series_model extraction:")
            # Simulate what happens after EO is extracted
            eo_match = re.search(r'(\*?D-\d+-\d+)/(\d{2}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})', line)
            if eo_match:
                rest_of_line = line[eo_match.end():].strip()
                print(f"  rest_of_line after EO: '{rest_of_line}'")

                series_match = re.search(r'^\s*([0-9/]+)', rest_of_line)
                if series_match:
                    print(f"  ✓ Series/Model found: '{series_match.group(1)}'")
                else:
                    print(f"  ✗ Series/Model NOT matched by pattern")
            break
