import fitz 
import os
import sys
from pathlib import Path

def extract_text_from_pdf(pdf_path: Path) -> str:

    doc = fitz.open(str(pdf_path))  
    
    all_pages_text = []  
    
    for page_number in range(len(doc)): 
        page = doc[page_number]          
        text = page.get_text()         
        all_pages_text.append(text)
    
    doc.close()  
    
    return "\n\n".join(all_pages_text)


def find_all_pdfs(data_dir: Path) -> list[Path]:

    pdfs = sorted(data_dir.rglob("*.pdf"))  
    return pdfs


def save_extracted_text(pdf_path: Path, data_dir: Path, extracted_dir: Path, text: str) -> Path:

    relative = pdf_path.relative_to(data_dir)
    txt_path = (extracted_dir / relative).with_suffix(".txt")
    
    # Create parent directories if they don't exist yet
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    
    # UTF-8 encoding to handle special characters
    txt_path.write_text(text, encoding="utf-8")
    
    return txt_path


def main():

    script_dir = Path(__file__).parent          
    project_root = script_dir.parent            
    data_dir = project_root / "data"            
    extracted_dir = data_dir / "extracted"      

    if not data_dir.exists():
        print(f"ERROR: Data directory not found at {data_dir}")
        sys.exit(1)

    # Create the output directory (and any parents) if it doesn't exist
    extracted_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {extracted_dir}")

    # Find all PDFs
    pdfs = [p for p in find_all_pdfs(data_dir) if extracted_dir not in p.parents]

    if not pdfs:
        print(f"No PDF files found in {data_dir}")
        sys.exit(0)

    print(f"Found {len(pdfs)} PDF file(s) in {data_dir}\n")
    print("=" * 70)

    # Process each PDF
    total_chars = 0       
    total_pages = 0       
    successful = 0        
    failed = []           

    for i, pdf_path in enumerate(pdfs, start=1):

        relative_path = pdf_path.relative_to(data_dir)
        print(f"\n[{i}/{len(pdfs)}] Processing: {relative_path}")

        try:
            # Count pages before extraction
            doc = fitz.open(str(pdf_path))
            num_pages = len(doc)
            doc.close()

            # Extract the text
            text = extract_text_from_pdf(pdf_path)
            num_chars = len(text)

            # Save to .txt inside data/extracted/
            txt_path = save_extracted_text(pdf_path, data_dir, extracted_dir, text)

            # Print summary for this file
            print(f"   Pages:      {num_pages}")
            print(f"   Characters: {num_chars:,}")
            print(f"   Saved to:   {txt_path.relative_to(data_dir)}")

            total_chars += num_chars
            total_pages += num_pages
            successful += 1

        except Exception as e:
            print(f"   ERROR: {e}")
            failed.append((relative_path, str(e)))

    # Final summary
    print("\n" + "=" * 70)
    print(f"\nDONE!")
    print(f"  Processed:    {successful}/{len(pdfs)} PDFs successfully")
    print(f"  Total pages:  {total_pages:,}")
    print(f"  Total chars:  {total_chars:,}")

    if failed:
        print(f"\n  FAILED ({len(failed)}):")
        for path, error in failed:
            print(f"    - {path}: {error}")

    print()


if __name__ == "__main__":
    main()
