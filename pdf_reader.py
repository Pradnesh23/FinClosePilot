import sys

try:
    import pypdf
except ImportError:
    print("pypdf not found")
    sys.exit(1)

try:
    reader = pypdf.PdfReader(sys.argv[1])
    text = ""
    for p in reader.pages:
        text += p.extract_text() + "\n"
    with open("pdf_content.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("PDF read successfully")
except Exception as e:
    print(f"Error: {e}")
