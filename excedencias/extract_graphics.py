"""
Extract Graphics from All PDFs
Runs extraction for all aircraft families
"""
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.pdf_graphics_extractor import PDFGraphicsExtractor
from utils.logger import logger

def main():
    print("="*70)
    print("PDF GRAPHICS EXTRACTION")
    print("="*70)
    
    extractor = PDFGraphicsExtractor()
    # Famílias: E145, E170 (E170/E175), E1 (E190/E195), E2 (E190-E2/E195-E2)
    families = ['E145', 'E170', 'E1', 'E2']
    
    total_extracted = 0
    
    for family in families:
        print(f"\n{'='*70}")
        print(f"Processing: {family}")
        print(f"{'='*70}")
        
        try:
            results = extractor.extract_all_graphics(family)
            
            family_total = sum(len(paths) for paths in results.values())
            total_extracted += family_total
            
            print(f"\n✅ {family}: {family_total} graphics extracted from {len(results)} PDFs")
            
            for pdf_name, image_paths in results.items():
                print(f"   - {pdf_name}: {len(image_paths)} images")
            
            # Create index
            index = extractor.create_graphics_index(family)
            index_file = Path(f"docs/graphics_index_{family}.md")
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index)
            print(f"   📄 Index saved: {index_file}")
            
        except Exception as e:
            print(f"❌ Error processing {family}: {e}")
            logger.error(f"Error extracting graphics for {family}: {e}")
    
    print(f"\n{'='*70}")
    print(f"EXTRACTION COMPLETE!")
    print(f"{'='*70}")
    print(f"Total graphics extracted: {total_extracted}")
    print(f"Output directory: assets/pdf_graphics/")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
