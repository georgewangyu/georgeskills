#!/usr/bin/env python3
"""
Image OCR Extraction Script
Extracts text from image files (JPEG, PNG, etc.) using OCR (Tesseract).

Supports multiple languages including Chinese.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def extract_text_from_image(image_path, lang='eng'):
    """
    Extract text from an image file using OCR.

    Args:
        image_path: Path to image file
        lang: Tesseract language code (default: eng)

    Returns:
        Extracted text as string
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Check if tesseract is available
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise FileNotFoundError("tesseract not found. Install with: brew install tesseract")

    # Run tesseract OCR
    result = subprocess.run(
        ['tesseract', str(image_path), 'stdout', '-l', lang],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0:
        return result.stdout
    else:
        # Try with English only if other language fails
        if lang != 'eng':
            print(f"Warning: OCR failed with {lang}, trying English only...", file=sys.stderr)
            result = subprocess.run(
                ['tesseract', str(image_path), 'stdout', '-l', 'eng'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout

        raise Exception(f"OCR extraction failed: {result.stderr}")

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
        description='Extract text from image files using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract with English OCR
  python3 extract_image_ocr.py image.jpeg

  # Extract with Chinese + English OCR
  python3 extract_image_ocr.py --lang chi_sim+eng image.jpeg

  # Extract multiple images
  python3 extract_image_ocr.py img1.jpeg img2.jpeg img3.jpeg
        """
    )

    parser.add_argument(
        'image_files',
        nargs='+',
        help='Image file(s) to extract text from'
    )

    parser.add_argument(
        '--lang',
        default='eng',
        help='Tesseract language code (default: eng)'
    )

    parser.add_argument(
        '--separator',
        default='\n\n' + '='*80 + '\n\n',
        help='Separator between multiple images (default: horizontal line)'
    )

    args = parser.parse_args()

    # Check language support
    langs = args.lang.split('+')
    for lang in langs:
        if not check_tesseract_lang(lang):
            print(f"Warning: Language '{lang}' may not be installed.", file=sys.stderr)
            print(f"Install with: brew install tesseract-lang", file=sys.stderr)
            if lang != 'eng':
                print(f"Falling back to English only...", file=sys.stderr)
                args.lang = 'eng'

    # Process each image
    all_texts = []
    errors = []

    for image_file in args.image_files:
        image_path = Path(image_file)

        if not image_path.exists():
            errors.append(f"{image_file}: File not found")
            continue

        # Extract text
        try:
            print(f"Extracting text from: {image_path}", file=sys.stderr)
            text = extract_text_from_image(image_path, lang=args.lang)

            if text.strip():
                all_texts.append(f"=== {image_path.name} ===\n\n{text}")
            else:
                errors.append(f"{image_file}: No text extracted")
                print(f"Warning: No text extracted from {image_file}", file=sys.stderr)

        except Exception as e:
            errors.append(f"{image_file}: {e}")
            print(f"Error processing {image_file}: {e}", file=sys.stderr)

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
        if not all_texts:
            sys.exit(1)

    if not all_texts and not errors:
        print("No text extracted from any image files.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()




