import PyPDF2

pdf_path = r"C:\Users\user\Downloads\InputTaxInvoice-e69d55ec-13b2-4cd9-95fd-914277e0f2fd-0936113042618000-04002600044178747-0032319170701000.pdf"
with open(pdf_path, "rb") as file:
    reader = PyPDF2.PdfReader(file)
    
    all_text = ""
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text += text + "\n"

print(all_text)


