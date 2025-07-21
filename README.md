# PDF Outline Extractor

Extracts title, H1, H2, H3 headings from PDFs using font size analysis.

## 🛠️ Usage

1. Put your PDF files into the `input/` folder.
2. Run the project using Docker or Python.
3. Outputs will be in the `output/` folder as JSON files.

## 🐳 Run with Docker

```bash
docker build -t pdf_extractor .
docker run -v %cd%/input:/app/input -v %cd%/output:/app/output pdf_extractor
