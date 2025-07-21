import os
import json
import fitz  # PyMuPDF

NOISE_WORDS = {"open access", "research", "sustainable environment", "article", "journal"}

def is_noisy(text):
    return text.lower().strip() in NOISE_WORDS or len(text.strip()) <= 3

def clean_text(text):
    return " ".join(text.replace("\n", " ").split()).strip()

def extract_title(page):
    blocks = page.get_text("dict")["blocks"]
    spans_by_size = {}

    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span["size"]
                text = clean_text(span["text"])
                if len(text) < 10:
                    continue
                spans_by_size.setdefault(size, []).append(text)

    if not spans_by_size:
        return None

    max_size = max(spans_by_size)
    title_lines = spans_by_size[max_size]
    return clean_text(" ".join(title_lines))

def detect_heading_level(size, thresholds):
    if size >= thresholds["H1"]:
        return "H1"
    elif size >= thresholds["H2"]:
        return "H2"
    elif size >= thresholds["H3"]:
        return "H3"
    return None

def extract_outline(pdf_path):
    doc = fitz.open(pdf_path)
    title = extract_title(doc[0]) or os.path.splitext(os.path.basename(pdf_path))[0]

    all_sizes = []
    heading_candidates = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = clean_text(span["text"])
                    size = span["size"]

                    if len(text) > 3:
                        all_sizes.append(size)

                    if is_noisy(text):
                        continue

                    heading_candidates.append((size, text, page_num))

    unique_sizes = sorted(set(all_sizes), reverse=True)
    thresholds = {
        "H1": unique_sizes[0] if len(unique_sizes) > 0 else 16,
        "H2": unique_sizes[1] if len(unique_sizes) > 1 else 14,
        "H3": unique_sizes[2] if len(unique_sizes) > 2 else 12,
    }

    used = set()
    outline = []

    for size, text, page_num in heading_candidates:
        text = clean_text(text)
        if text.lower() in used:
            continue

        level = detect_heading_level(size, thresholds)
        if level:
            outline.append({
                "level": level,
                "text": text,
                "page": page_num
            })
            used.add(text.lower())

    return {
        "title": title,
        "outline": outline
    }

if __name__ == "__main__":
    input_dir = "input"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".pdf"):
            in_path = os.path.join(input_dir, filename)
            out_path = os.path.join(output_dir, filename.replace(".pdf", ".json"))
            result = extract_outline(in_path)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"✅ Processed {filename} → {os.path.basename(out_path)}")
