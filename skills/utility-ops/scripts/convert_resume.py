#!/usr/bin/env python3
"""
Simple script to convert Word documents to text/markdown format.
Uses macOS built-in textutil (no additional dependencies required).
"""

import sys
import subprocess
from pathlib import Path

def convert_word_to_text(input_file, output_file):
    """
    Convert Word document to plain text using macOS textutil.
    
    Args:
        input_file: Path to input .docx file
        output_file: Path to output .txt file
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        return False
    
    if input_path.suffix.lower() not in ['.docx', '.doc']:
        print(f"❌ Error: Unsupported file format: {input_path.suffix}")
        print("   Supported formats: .docx, .doc (Word documents)")
        return False
    
    try:
        # Use textutil to convert to plain text
        subprocess.run([
            'textutil',
            '-convert', 'txt',
            '-output', str(output_path),
            str(input_path)
        ], check=True, capture_output=True)
        
        print(f"✅ Successfully converted:")
        print(f"   Input:  {input_path}")
        print(f"   Output: {output_path}")
        
        # Read and show preview
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                preview = f.read(500)  # First 500 chars
                print(f"\n📄 Preview (first 500 characters):")
                print("-" * 60)
                print(preview)
                if len(preview) == 500:
                    print("...")
                print("-" * 60)
        except Exception as e:
            print(f"⚠️  Could not read output file: {e}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during conversion: {e}")
        if e.stderr:
            print(f"   Details: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print("❌ Error: textutil not found")
        print("   textutil should be available on macOS")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 convert_resume.py <input_file> [output_file]")
        print("\nExample:")
        print("  python3 convert_resume.py Resume/resume.docx")
        print("  python3 convert_resume.py Resume/resume.docx Resume/resume.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Generate output filename if not provided
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        input_path = Path(input_file)
        output_file = input_path.with_suffix('.txt')
    
    success = convert_word_to_text(input_file, output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
