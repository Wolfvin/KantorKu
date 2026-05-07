import PyPDF2

pdf_path = r"C:\Users\TOSHIBA\Downloads\TARIKAN CORETAX\M_01-DOC002_Ebupot_2126_English_BP21_id-fo-xsl_DN2025638878070177138765000.pdf"

with open(pdf_path, "rb") as file:
    reader = PyPDF2.PdfReader(file)
    
    all_text = ""
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text += text + "\n"

print(all_text)


