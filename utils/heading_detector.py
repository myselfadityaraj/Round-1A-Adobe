def detect_headings(elements):
    # Sort by font size descending
    sorted_elements = sorted(elements, key=lambda x: -x["size"])
    sizes = [el["size"] for el in sorted_elements]
    unique_sizes = sorted(set(sizes), reverse=True)

    size_to_level = {}
    if unique_sizes:
        size_to_level[unique_sizes[0]] = "title"
        if len(unique_sizes) > 1:
            size_to_level[unique_sizes[1]] = "h1"
        if len(unique_sizes) > 2:
            size_to_level[unique_sizes[2]] = "h2"
        if len(unique_sizes) > 3:
            size_to_level[unique_sizes[3]] = "h3"

    outline = {
        "title": None,
        "h1": [],
        "h2": [],
        "h3": []
    }

    for el in elements:
        level = size_to_level.get(el["size"])
        if level:
            if level == "title" and not outline["title"]:
                outline["title"] = el["text"]
            elif level in ["h1", "h2", "h3"]:
                outline[level].append({
                    "text": el["text"],
                    "page": el["page"]
                })

    return outline
