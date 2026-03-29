#!/usr/bin/env python3
"""
PDF OCR Extraction Script
Extracts text from image-based/scanned PDFs using OCR (Tesseract).

Supports multiple languages including Chinese.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def extract_with_pymupdf_images(pdf_path, lang='chi_sim+eng'):
    """
    Extract text from PDF by converting pages to images and using OCR.

    Args:
        pdf_path: Path to PDF file
        lang: Tesseract language code (default: chi_sim+eng for Chinese Simplified + English)

    Returns:
        Extracted text as string
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text_parts = []

        print(f"Processing {len(doc)} pages...", file=sys.stderr)

        for page_num in range(len(doc)):
            print(f"Processing page {page_num + 1}/{len(doc)}...", file=sys.stderr)
            page = doc[page_num]

            # Convert page to image (300 DPI for good quality)
            mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)

            # Save to temporary image
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                pix.save(tmp_path)

            try:
                # Run tesseract OCR
                result = subprocess.run(
                    ['tesseract', tmp_path, 'stdout', '-l', lang],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode == 0:
                    text_parts.append(result.stdout)
                else:
                    # Try with English only if Chinese fails
                    if lang != 'eng':
                        print(f"Warning: OCR failed with {lang}, trying English only...", file=sys.stderr)
                        result = subprocess.run(
                            ['tesseract', tmp_path, 'stdout', '-l', 'eng'],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode == 0:
                            text_parts.append(result.stdout)
                        else:
                            print(f"Warning: OCR failed for page {page_num + 1}", file=sys.stderr)
                    else:
                        print(f"Warning: OCR failed for page {page_num + 1}: {result.stderr}", file=sys.stderr)
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        doc.close()
        return "\n\n".join(text_parts)
    except ImportError:
        raise ImportError("PyMuPDF (fitz) not installed. Install with: pip3 install pymupdf")
    except Exception as e:
        raise Exception(f"OCR extraction failed: {e}")

def check_tesseract_lang(lang):
    """Check if tesseract language pack is available."""
    try:
        result = subprocess.run(
            ['tesseract', '--list-langs'],
            capture_output=True,
            text=True,
            check=True
        )
        available_langs = result.stdout.strip().split('\n')[1:]  # Skip first line
        return lang in available_langs
    except:
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract text from image-based/scanned PDFs using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract with Chinese + English OCR
  python3 extract_pdf_ocr.py document.pdf

  # Extract with English only
  python3 extract_pdf_ocr.py --lang eng document.pdf

  # Extract with Traditional Chinese + English
  python3 extract_pdf_ocr.py --lang chi_tra+eng document.pdf
        """
    )

    parser.add_argument(
        'pdf_file',
        help='PDF file to extract text from'
    )

    parser.add_argument(
        '--lang',
        default='chi_sim+eng',
        help='Tesseract language code (default: chi_sim+eng for Chinese Simplified + English)'
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)

    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not pdf_path.suffix.lower() == '.pdf':
        print(f"Error: File is not a PDF: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Check if tesseract is available
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: tesseract not found. Install with: brew install tesseract", file=sys.stderr)
        sys.exit(1)

    # Check language support
    langs = args.lang.split('+')
    for lang in langs:
        if not check_tesseract_lang(lang):
            print(f"Warning: Language '{lang}' may not be installed.", file=sys.stderr)
            print(f"Install with: brew install tesseract-lang", file=sys.stderr)
            print(f"Or try: tesseract --list-langs to see available languages", file=sys.stderr)
            if lang != 'eng':
                print(f"Falling back to English only...", file=sys.stderr)
                args.lang = 'eng'

    # Extract text
    try:
        print(f"Extracting text from: {pdf_path}", file=sys.stderr)
        print(f"Using OCR language: {args.lang}", file=sys.stderr)
        text = extract_with_pymupdf_images(pdf_path, lang=args.lang)

        if text.strip():
            print(f"\n=== Extracted Text ===\n", file=sys.stderr)
            print(text)
        else:
            print("Warning: No text extracted from PDF", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()




