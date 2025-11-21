"""
Manual Book Enrichment Script
Allows processing of specific chapters, appendixes, or sections
"""
import sys
from book_enrichment import BookDataEnricher, API_KEY, PDF_PATH, OUTPUT_BASE
import google.generativeai as genai


def main():
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print("""
Book Data Enrichment Tool - Manual Processing

Usage:
  python manual_enrich.py --chapter <num>    # Process specific chapter
  python manual_enrich.py --appendix <num>   # Process specific appendix
  python manual_enrich.py --section <name>   # Process specific section

Examples:
  python manual_enrich.py --chapter 2        # Process Chapter 2
  python manual_enrich.py --appendix 1       # Process Appendix 1
  python manual_enrich.py --section preface  # Process Preface

Available sections:
  preface, foreword, acknowledgments, introduction, glossary, 
  bibliography, references, index
""")
        return
    
    enricher = BookDataEnricher(API_KEY, PDF_PATH, OUTPUT_BASE)
    
    try:
        if "--chapter" in sys.argv:
            idx = sys.argv.index("--chapter")
            if idx + 1 < len(sys.argv):
                chapter_num = int(sys.argv[idx + 1])
                print(f"\n{'='*60}")
                print(f"Manual Chapter Processing - Chapter {chapter_num}")
                print(f"{'='*60}\n")
                
                # Extract structure
                full_pdf_file = enricher.upload_pdf_to_gemini(enricher.pdf_path)
                try:
                    structure = enricher.extract_structure(full_pdf_file)
                finally:
                    genai.delete_file(full_pdf_file.name)
                
                # Process chapter
                if 'chapters' in structure and len(structure['chapters']) >= chapter_num:
                    chapter_info = structure['chapters'][chapter_num - 1]
                    enricher.process_chapter(chapter_info, chapter_num)
                    print(f"\n{'='*60}")
                    print(f"✓ Chapter {chapter_num} processing complete!")
                    print(f"{'='*60}")
                else:
                    print(f"Error: Chapter {chapter_num} not found in book structure")
            else:
                print("Error: Please specify chapter number")
        
        elif "--appendix" in sys.argv:
            idx = sys.argv.index("--appendix")
            if idx + 1 < len(sys.argv):
                appendix_num = int(sys.argv[idx + 1])
                print(f"\n{'='*60}")
                print(f"Manual Appendix Processing - Appendix {appendix_num}")
                print(f"{'='*60}\n")
                
                # Extract structure
                full_pdf_file = enricher.upload_pdf_to_gemini(enricher.pdf_path)
                try:
                    structure = enricher.extract_structure(full_pdf_file)
                finally:
                    genai.delete_file(full_pdf_file.name)
                
                # Process appendix
                if 'appendixes' in structure and len(structure['appendixes']) >= appendix_num:
                    appendix_info = structure['appendixes'][appendix_num - 1]
                    enricher.process_appendix(appendix_info, appendix_num)
                    print(f"\n{'='*60}")
                    print(f"✓ Appendix {appendix_num} processing complete!")
                    print(f"{'='*60}")
                else:
                    print(f"Error: Appendix {appendix_num} not found in book structure")
            else:
                print("Error: Please specify appendix number")
        
        elif "--section" in sys.argv:
            idx = sys.argv.index("--section")
            if idx + 1 < len(sys.argv):
                section_name = sys.argv[idx + 1].lower()
                print(f"\n{'='*60}")
                print(f"Manual Section Processing - {section_name.title()}")
                print(f"{'='*60}\n")
                
                # Extract structure
                full_pdf_file = enricher.upload_pdf_to_gemini(enricher.pdf_path)
                try:
                    structure = enricher.extract_structure(full_pdf_file)
                finally:
                    genai.delete_file(full_pdf_file.name)
                
                # Process section
                section_processors = {
                    'preface': enricher.process_preface,
                    'foreword': enricher.process_foreword,
                    'acknowledgments': enricher.process_acknowledgments,
                    'introduction': enricher.process_introduction,
                    'glossary': enricher.process_glossary,
                    'bibliography': enricher.process_bibliography,
                    'references': enricher.process_references,
                    'index': enricher.process_index
                }
                
                if section_name in section_processors and section_name in structure:
                    enricher.safe_process_section(
                        structure[section_name],
                        section_name.title(),
                        section_processors[section_name]
                    )
                    print(f"\n{'='*60}")
                    print(f"✓ {section_name.title()} processing complete!")
                    print(f"{'='*60}")
                else:
                    print(f"Error: Section '{section_name}' not found")
                    print(f"Available: {', '.join(section_processors.keys())}")
            else:
                print("Error: Please specify section name")
    
    finally:
        enricher.cleanup_temp_files()


if __name__ == "__main__":
    main()
