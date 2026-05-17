import sys
try:
    from pypdf import PdfReader
    reader = PdfReader("C:/Users/milky/Documents/GCED/GCED/TOOL/Toán_học.pdf")
    text = reader.pages[0].extract_text()
    print("PAGE 1 TEXT:")
    print(text[:2000])
except Exception as e:
    print("Error:", e)
