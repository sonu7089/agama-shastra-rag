"""
Utility functions for the Book RAG system
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def get_book_statistics(output_dir: str = "Output") -> Dict[str, Any]:
    """Get statistics about indexed books"""
    output_path = Path(output_dir)
    
    if not output_path.exists():
        return {"error": "Output directory not found"}
    
    stats = {
        "total_books": 0,
        "books": []
    }
    
    for book_folder in output_path.iterdir():
        if not book_folder.is_dir():
            continue
        
        book_stats = {
            "name": book_folder.name,
            "chapters": 0,
            "appendixes": 0,
            "has_glossary": False,
            "has_references": False,
            "has_front_matter": []
        }
        
        # Count chapters
        book_stats["chapters"] = len(list(book_folder.glob("Chapter_*.json")))
        
        # Count appendixes
        book_stats["appendixes"] = len(list(book_folder.glob("Appendix_*.json")))
        
        # Check for other files
        if (book_folder / "Glossary.json").exists():
            book_stats["has_glossary"] = True
        
        if (book_folder / "References_and_Notes.json").exists():
            book_stats["has_references"] = True
        
        # Check front matter
        for front_matter in ["Preface.json", "Foreword.json", "Introduction.json", "Acknowledgments.json"]:
            if (book_folder / front_matter).exists():
                book_stats["has_front_matter"].append(front_matter.replace(".json", ""))
        
        # Try to get total pages from structure
        structure_file = book_folder / "book_structure.json"
        if structure_file.exists():
            try:
                with open(structure_file, 'r', encoding='utf-8') as f:
                    structure = json.load(f)
                    if 'chapters' in structure and structure['chapters']:
                        last_chapter = structure['chapters'][-1]
                        book_stats["total_pages"] = last_chapter.get('end_page', 'unknown')
            except Exception:
                pass
        
        stats["books"].append(book_stats)
        stats["total_books"] += 1
    
    return stats


def validate_book_data(book_folder: Path) -> Dict[str, Any]:
    """Validate that a book folder has all expected files"""
    validation = {
        "book_name": book_folder.name,
        "is_valid": True,
        "missing_files": [],
        "warnings": [],
        "file_count": 0
    }
    
    # Check for required files
    required = ["book_structure.json"]
    optional = [
        "Preface.json", "Foreword.json", "Introduction.json",
        "Glossary.json", "References_and_Notes.json",
        "Consolidated_Metadata.json"
    ]
    
    for req_file in required:
        if not (book_folder / req_file).exists():
            validation["missing_files"].append(req_file)
            validation["is_valid"] = False
    
    # Count chapters
    chapters = list(book_folder.glob("Chapter_*.json"))
    if not chapters:
        validation["warnings"].append("No chapters found")
        validation["is_valid"] = False
    else:
        validation["file_count"] = len(chapters)
    
    # Count appendixes
    appendixes = list(book_folder.glob("Appendix_*.json"))
    if appendixes:
        validation["file_count"] += len(appendixes)
    
    # Check optional files
    for opt_file in optional:
        if (book_folder / opt_file).exists():
            validation["file_count"] += 1
    
    return validation


def print_book_info(output_dir: str = "Output"):
    """Print formatted information about all books"""
    stats = get_book_statistics(output_dir)
    
    if "error" in stats:
        print(f"Error: {stats['error']}")
        return
    
    print("\n" + "="*60)
    print(f"  Book Statistics - {stats['total_books']} book(s) found")
    print("="*60 + "\n")
    
    for book in stats["books"]:
        print(f"📚 {book['name']}")
        print(f"   Chapters: {book['chapters']}")
        
        if book['appendixes'] > 0:
            print(f"   Appendixes: {book['appendixes']}")
        
        if book['has_glossary']:
            print(f"   ✓ Has Glossary")
        
        if book['has_references']:
            print(f"   ✓ Has References")
        
        if book['has_front_matter']:
            print(f"   Front Matter: {', '.join(book['has_front_matter'])}")
        
        if 'total_pages' in book:
            print(f"   Total Pages: {book['total_pages']}")
        
        print()


def export_book_outline(book_folder: Path, output_file: str = None):
    """Export a readable outline of the book structure"""
    structure_file = book_folder / "book_structure.json"
    
    if not structure_file.exists():
        print(f"No book_structure.json found in {book_folder}")
        return
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    outline = []
    outline.append(f"\n{'='*60}")
    outline.append(f"  Book Outline: {book_folder.name}")
    outline.append(f"{'='*60}\n")
    
    # Front matter
    front_matter = ['preface', 'foreword', 'acknowledgments', 'introduction']
    for section in front_matter:
        if section in structure:
            info = structure[section]
            title = info.get('title', section.title())
            pages = f"{info.get('start_page', '?')}-{info.get('end_page', '?')}"
            outline.append(f"  {title} (pp. {pages})")
    
    # Chapters
    if 'chapters' in structure:
        outline.append(f"\n  Chapters:")
        for chapter in structure['chapters']:
            num = chapter.get('chapter_number', '?')
            title = chapter.get('title', 'Untitled')
            pages = f"{chapter.get('start_page', '?')}-{chapter.get('end_page', '?')}"
            outline.append(f"    {num}. {title} (pp. {pages})")
    
    # Appendixes
    if 'appendixes' in structure:
        outline.append(f"\n  Appendixes:")
        for appendix in structure['appendixes']:
            app_id = appendix.get('appendix_id', '?')
            title = appendix.get('title', 'Untitled')
            pages = f"{appendix.get('start_page', '?')}-{appendix.get('end_page', '?')}"
            outline.append(f"    {app_id}. {title} (pp. {pages})")
    
    # Back matter
    back_matter = ['glossary', 'bibliography', 'references_and_notes', 'index']
    for section in back_matter:
        if section in structure:
            info = structure[section]
            title = info.get('title', section.replace('_', ' ').title())
            pages = f"{info.get('start_page', '?')}-{info.get('end_page', '?')}"
            outline.append(f"  {title} (pp. {pages})")
    
    outline.append("")
    
    outline_text = "\n".join(outline)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(outline_text)
        print(f"Outline exported to {output_file}")
    else:
        print(outline_text)


def generate_query_suggestions(book_folder: Path) -> List[str]:
    """Generate suggested queries based on book content"""
    suggestions = []
    
    # Check consolidated metadata
    metadata_file = book_folder / "Consolidated_Metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Suggest queries based on content
            if metadata.get('all_historical_figures'):
                figure = metadata['all_historical_figures'][0].get('name', '')
                if figure:
                    suggestions.append(f"Tell me about {figure}")
            
            if metadata.get('complete_timeline'):
                event = metadata['complete_timeline'][0].get('event', '')
                if event:
                    suggestions.append(f"What happened during {event}?")
            
            if metadata.get('all_geographic_locations'):
                location = metadata['all_geographic_locations'][0].get('place', '')
                if location:
                    suggestions.append(f"What is the significance of {location}?")
        except Exception:
            pass
    
    # Generic suggestions
    suggestions.extend([
        "What are the main themes of this book?",
        "Summarize chapter 1",
        "What is the author's main argument?",
        "What are the key takeaways?",
    ])
    
    return suggestions


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "stats":
            print_book_info()
        
        elif command == "outline":
            output_dir = Path("Output")
            for book_folder in output_dir.iterdir():
                if book_folder.is_dir():
                    export_book_outline(book_folder)
        
        elif command == "validate":
            output_dir = Path("Output")
            print("\nValidating book data...\n")
            for book_folder in output_dir.iterdir():
                if book_folder.is_dir():
                    result = validate_book_data(book_folder)
                    status = "✓" if result["is_valid"] else "✗"
                    print(f"{status} {result['book_name']} - {result['file_count']} files")
                    if result["missing_files"]:
                        print(f"   Missing: {', '.join(result['missing_files'])}")
                    if result["warnings"]:
                        print(f"   Warnings: {', '.join(result['warnings'])}")
        
        elif command == "suggestions":
            output_dir = Path("Output")
            for book_folder in output_dir.iterdir():
                if book_folder.is_dir():
                    print(f"\n📚 {book_folder.name}")
                    suggestions = generate_query_suggestions(book_folder)
                    for i, suggestion in enumerate(suggestions[:5], 1):
                        print(f"  {i}. {suggestion}")
        
        else:
            print("Usage: python rag_utils.py [command]")
            print("Commands:")
            print("  stats        - Show statistics about indexed books")
            print("  outline      - Show book outlines")
            print("  validate     - Validate book data integrity")
            print("  suggestions  - Generate query suggestions")
    
    else:
        print_book_info()
