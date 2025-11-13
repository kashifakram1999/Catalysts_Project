import PyPDF2

pdf_path = "/Users/muhmmadkashif/Desktop/Data.pdf"

with open(pdf_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)

    # Get page 2 and 3
    for page_num in [1, 2, 3]:
        if page_num < len(pdf_reader.pages):
            print(f"\n{'='*60}")
            print(f"=== Page {page_num + 1} (First 40 lines) ===")
            print(f"{'='*60}")
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            lines = text.split('\n')

            for i, line in enumerate(lines[:40], 1):
                print(f"{i:3d}: '{line}'")
