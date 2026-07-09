"""
Test PDF Rules Extraction
"""
from pathlib import Path
from services.pdf_rules_extractor import PDFRulesExtractor

def main():
    print("="*60)
    print("PDF RULES EXTRACTION TEST")
    print("="*60)
    
    extractor = PDFRulesExtractor()
    
    # Famílias: E145, E170 (E170/E175), E1 (E190/E195), E2 (E190-E2/E195-E2)
    families = ['E145', 'E170', 'E1', 'E2']
    
    for family in families:
        print(f"\n{'='*60}")
        print(f"Extracting rules for: {family}")
        print(f"{'='*60}\n")
        
        # Generate summary
        summary = extractor.generate_rules_summary(family)
        
        # Save to file
        output_file = Path(f"docs/rules_summary_{family}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"✅ Summary saved to: {output_file}")
        print(summary[:500] + "...\n")  # Preview
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE!")
    print("="*60)

if __name__ == "__main__":
    main()
