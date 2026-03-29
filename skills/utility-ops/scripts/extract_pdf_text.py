#!/usr/bin/env python3
"""
Extract text from PDF files for analysis.
Uses pypdf library for text extraction.
"""

import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("❌ Error: pypdf not installed. Install with: pip3 install pypdf")
    sys.exit(1)

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pdf_text.py <pdf_file>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Extracting text from: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    print("\n" + "="*80)
    print(text)
    print("="*80)




