import fitz  # PyMuPDF

def extract_pdf_elements(pdf_path):
    doc = fitz.open(pdf_path)
    elements = []

    for page_number, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        elements.append({
                            "text": text,
                            "size": span["size"],
                            "font": span["font"],
                            "page": page_number
                        })
    return elements
