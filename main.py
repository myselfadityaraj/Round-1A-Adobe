import os
import json
import fitz  # PyMuPDF
from collections import defaultdict
import re

NOISE_WORDS = {
    "open access", "research", "sustainable environment", "article", "journal",
    "abstract", "introduction", "references", "acknowledgments", "appendix",
    "received", "accepted", "published", "volume", "issue", "pp.", "pages"
}

def clean_text(text):
    """Clean text by removing extra whitespace and newlines, and fixing word breaks."""
    # First normalize all whitespace
    text = " ".join(text.replace("\n", " ").split())
    
    # Fix hyphenated word breaks (e.g., "under- standing" -> "understanding")
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    
    # Fix cases where words are broken across lines without hyphens
    text = re.sub(r'(\w)\s+(\w)', lambda m: m.group(1) + m.group(2) if len(m.group(1)) > 2 and len(m.group(2)) > 2 else m.group(0), text)
    
    return text.strip()

def is_noisy(text):
    """Check if text should be filtered out as noise."""
    text_lower = text.lower().strip()
    return (any(noise_word in text_lower for noise_word in NOISE_WORDS) or len(text.strip()) <= 3)

def extract_title(page):
    """Extract the title from the first page by finding the largest text and combining multi-line titles."""
    size_to_texts = defaultdict(list)
    blocks = page.get_text("dict")["blocks"]
    
    # First pass: collect all text spans by their size
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = round(span["size"], 1)
                text = clean_text(span["text"])
                if is_noisy(text) or len(text) < 5:
                    continue
                size_to_texts[size].append(text)
    
    if not size_to_texts:
        return "", None
    
    # Find the dominant title size (largest text that appears at the top)
    max_size = max(size_to_texts.keys())
    
    # Second pass: collect multi-line title by finding consecutive large text blocks
    title_parts = []
    previous_block_pos = None
    current_title_block = []
    
    for block in blocks:
        block_pos = block.get("bbox", (0, 0))[1]  # y-coordinate of the block
        for line in block.get("lines", []):
            line_texts = []
            line_has_title = False
            
            for span in line.get("spans", []):
                if round(span["size"], 1) == max_size:
                    text = clean_text(span["text"])
                    if not is_noisy(text):
                        line_has_title = True
                        line_texts.append(text)
            
            if line_has_title:
                full_line_text = " ".join(line_texts)
                # Check if this is a continuation of the previous line
                if (previous_block_pos is not None and 
                    abs(block_pos - previous_block_pos) < 20 and  # Lines are close vertically
                    len(current_title_block) > 0):
                    current_title_block.append(full_line_text)
                else:
                    if current_title_block:
                        title_parts.append(" ".join(current_title_block))
                    current_title_block = [full_line_text]
                previous_block_pos = block_pos
    
    if current_title_block:
        title_parts.append(" ".join(current_title_block))
    
    title = " ".join(title_parts)
    return clean_text(title), max_size

def group_multiline_headings(heading_candidates):
    """Group consecutive lines with same size into multi-line headings, fixing word breaks."""
    if not heading_candidates:
        return []
    
    grouped = []
    current_group = list(heading_candidates[0])
    
    for candidate in heading_candidates[1:]:
        size, text, page = candidate
        # If same size and page as previous, and text appears to be a continuation
        if (size == current_group[0] and 
            page == current_group[2] and 
            (text[0].islower() or  # Starts with lowercase (continuation)
             len(current_group[1].split()[-1]) <= 3 or  # Last word was short
             len(text.split()[0]) <= 3)):  # First word is short
            # Join without space if it looks like a word break
            if (current_group[1].endswith('-') or 
                len(current_group[1].split()[-1]) <= 2 or 
                len(text.split()[0]) <= 2):
                current_group[1] = current_group[1].rstrip('- ') + text
            else:
                current_group[1] += " " + text
        else:
            grouped.append(tuple(current_group))
            current_group = list(candidate)
    
    grouped.append(tuple(current_group))
    return grouped

def detect_heading_level(size, thresholds, title_size):
    """Determine heading level based on size thresholds, excluding title size."""
    if size == title_size:
        return None  # Skip the title
    if size >= thresholds["H1"]:
        return "H1"
    elif size >= thresholds["H2"]:
        return "H2"
    elif size >= thresholds["H3"]:
        return "H3"
    return None

def extract_outline(pdf_path):
    """Extract title and outline (headings) from PDF with proper multi-line and word break handling."""
    doc = fitz.open(pdf_path)
    
    # Extract title from first page
    title, title_size = extract_title(doc[0])
    if not title:
        title = os.path.basename(pdf_path).replace(".pdf", "")

    heading_candidates = []

    # Collect all heading candidates from all pages
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                line_text = []
                max_size_in_line = 0
                for span in line.get("spans", []):
                    text = clean_text(span["text"])
                    size = round(span["size"], 1)
                    
                    if is_noisy(text):
                        continue
                    
                    if size > max_size_in_line:
                        max_size_in_line = size
                    line_text.append(text)

                full_line_text = clean_text(" ".join(line_text))
                if full_line_text and len(full_line_text) > 3 and not is_noisy(full_line_text):
                    heading_candidates.append((max_size_in_line, full_line_text, page_num))

    # Group multi-line headings and fix word breaks
    heading_candidates = group_multiline_headings(heading_candidates)

    if not heading_candidates:
        return {"title": title, "outline": []}

    # Analyze sizes and define H1, H2, H3 thresholds
    heading_sizes = [size for size, _, _ in heading_candidates if size != title_size]
    if not heading_sizes:
        return {"title": title, "outline": []}
    
    unique_sizes = sorted(set(heading_sizes), reverse=True)
    
    thresholds = {
        "H1": unique_sizes[0] if len(unique_sizes) > 0 else 16,
        "H2": unique_sizes[1] if len(unique_sizes) > 1 else unique_sizes[0] * 0.85,
        "H3": unique_sizes[2] if len(unique_sizes) > 2 else unique_sizes[-1] * 0.7,
    }

    # Assign heading levels
    outline = []
    seen = set()
    for size, text, page in heading_candidates:
        key = (text.lower(), page)
        if key in seen:
            continue
        seen.add(key)

        level = detect_heading_level(size, thresholds, title_size)
        if level:
            outline.append({
                "level": level,
                "text": text,
                "page": page
            })

    return {"title": title, "outline": outline}

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
