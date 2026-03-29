#!/usr/bin/env python3
"""
PDF Text Extraction Script
Extracts raw text from PDF files for reconstruction into clean Markdown.

Supports multiple extraction methods:
- PyMuPDF (fitz) - Fast, good for most PDFs
- pdfplumber - Better for complex layouts and tables
"""

import sys
import argparse
from pathlib import Path

def extract_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF (fitz)"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(text)

        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("PyMuPDF (fitz) not installed. Install with: pip3 install pymupdf")
    except Exception as e:
        raise Exception(f"PyMuPDF extraction failed: {e}")

def extract_with_pdfplumber(pdf_path):
    """Extract text using pdfplumber"""
    try:
        import pdfplumber
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("pdfplumber not installed. Install with: pip3 install pdfplumber")
    except Exception as e:
        raise Exception(f"pdfplumber extraction failed: {e}")

def extract_pdf_text(pdf_path, method='auto'):
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file
        method: Extraction method ('auto', 'pymupdf', 'pdfplumber')

    Returns:
        Extracted text as string
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.suffix.lower() == '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")

    # Try PyMuPDF first (faster)
    if method == 'auto' or method == 'pymupdf':
        try:
            return extract_with_pymupdf(pdf_path)
        except ImportError:
            if method == 'pymupdf':
                raise
            # Fall back to pdfplumber if PyMuPDF not available
            print(f"Warning: PyMuPDF not available, trying pdfplumber...", file=sys.stderr)
        except Exception as e:
            if method == 'pymupdf':
                raise
            # Fall back to pdfplumber on error
            print(f"Warning: PyMuPDF extraction failed: {e}", file=sys.stderr)
            print(f"Trying pdfplumber...", file=sys.stderr)

    # Try pdfplumber
    if method == 'auto' or method == 'pdfplumber':
        try:
            return extract_with_pdfplumber(pdf_path)
        except ImportError:
            if method == 'pdfplumber':
                raise
            raise ImportError("Neither PyMuPDF nor pdfplumber is installed. Install with: pip3 install pymupdf pdfplumber")
        except Exception as e:
            if method == 'pdfplumber':
                raise
            raise Exception(f"Both extraction methods failed. Last error: {e}")

    raise ValueError(f"Unknown extraction method: {method}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract raw text from PDF files for reconstruction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract single PDF
  python3 extract_pdf_text.py document.pdf

  # Extract multiple PDFs
  python3 extract_pdf_text.py doc1.pdf doc2.pdf doc3.pdf

  # Use specific extraction method
  python3 extract_pdf_text.py --method pdfplumber document.pdf

  # Save to file
  python3 extract_pdf_text.py document.pdf > output.txt
        """
    )

    parser.add_argument(
        'pdf_files',
        nargs='+',
        help='PDF file(s) to extract text from'
    )

    parser.add_argument(
        '--method',
        choices=['auto', 'pymupdf', 'pdfplumber'],
        default='auto',
        help='Extraction method to use (default: auto)'
    )

    parser.add_argument(
        '--separator',
        default='\n\n' + '='*80 + '\n\n',
        help='Separator between multiple PDFs (default: horizontal line)'
    )

    args = parser.parse_args()

    # Process each PDF
    all_texts = []
    errors = []

    for pdf_file in args.pdf_files:
        try:
            print(f"Extracting text from: {pdf_file}", file=sys.stderr)
            text = extract_pdf_text(pdf_file, method=args.method)

            if text.strip():
                all_texts.append(f"=== {Path(pdf_file).name} ===\n\n{text}")
            else:
                errors.append(f"{pdf_file}: No text extracted (may be image-only PDF)")
                print(f"Warning: No text extracted from {pdf_file}", file=sys.stderr)

        except Exception as e:
            errors.append(f"{pdf_file}: {e}")
            print(f"Error processing {pdf_file}: {e}", file=sys.stderr)

    # Output all extracted text
    if all_texts:
        output = args.separator.join(all_texts)
        print(output)

    # Report errors
    if errors:
        print("\n" + "="*80, file=sys.stderr)
        print("Errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    if not all_texts and not errors:
        print("No text extracted from any PDF files.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()




