import PyPDF2

pdf_path = "/Users/muhmmadkashif/Desktop/Data.pdf"

with open(pdf_path, 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)

    # Get first page
    page = pdf_reader.pages[0]
    text = page.extract_text()

    lines = text.split('\n')

    print("=== First 50 lines of PDF ===")
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3d}: '{line}'")
