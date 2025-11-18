import os
import re
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, List
import google.generativeai as genai
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
PDF_PATH = os.getenv("PDF_PATH")
OUTPUT_BASE = os.getenv("OUTPUT_DIR", "Output")
PDF_PAGE_OFFSET = int(os.getenv("PDF_PAGE_OFFSET", "0"))


class BookDataEnricher:
    def __init__(self, api_key: str, pdf_path: str, output_base: str = "Output"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.pdf_path = pdf_path
        self.file_name = Path(pdf_path).stem
        self.output_dir = Path(output_base) / self.file_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.output_dir / "temp"
        self.temp_pdf_files: List[Path] = []  # Track all temporary PDF files


    def upload_pdf_to_gemini(self, pdf_path: str):
        """Upload PDF file to Gemini API"""
        file = genai.upload_file(pdf_path)
        while file.state.name == "PROCESSING":
            print("Waiting for file processing...")
            time.sleep(2)
            file = genai.get_file(file.name)
        if file.state.name == "FAILED":
            raise ValueError("File processing failed")
        print(f"File uploaded successfully: {file.uri}")
        return file


    def normalize_page_numbers(self, section_info: Dict) -> Dict:
        """Convert page numbers to integers if they're strings"""
        if 'start_page' in section_info:
            section_info['start_page'] = int(section_info['start_page'])
        if 'end_page' in section_info:
            section_info['end_page'] = int(section_info['end_page'])
        return section_info


    def extract_structure(self, pdf_file) -> Dict:
        """Extract complete book structure including all sections"""
        prompt = f"""
        Analyze this book PDF and extract its complete structure. 
        Keep all unicode, including Sanskrit, Hindi, and any other non-English text exactly as in the book.
        Provide JSON only, with:
        {{
            "preface": {{"title": "...", "start_page": 1, "end_page": 5}},
            "foreword": {{"title": "...", "start_page": 6, "end_page": 10}},
            "acknowledgments": {{"title": "...", "start_page": 11, "end_page": 15}},
            "introduction": {{"title": "...", "start_page": 16, "end_page": 30}},
            "table_of_contents": {{"start_page": 1, "end_page": 3}},
            "chapters": [{{"chapter_number": "1", "title": "...", "start_page": 31, "end_page": 55}}],
            "appendixes": [{{"appendix_id": "A", "title": "...", "start_page": 200, "end_page": 220}}],
            "glossary": {{"title": "...", "start_page": 221, "end_page": 235}},
            "bibliography": {{"title": "...", "start_page": 236, "end_page": 250}},
            "references_and_notes": {{"title": "...", "start_page": 251, "end_page": 280}},
            "index": {{"title": "...", "start_page": 281, "end_page": 300}}
        }}
        IMPORTANT: All page numbers MUST be integers (numbers), not strings.
        All page numbers are as printed in the book; PDFs pages start at offset {PDF_PAGE_OFFSET}.
        Include all sections that exist in the book. If a section doesn't exist, omit it from the JSON.
        """
        response = self.model.generate_content([pdf_file, prompt])
        content = response.text.strip()
        json_data = self.extract_json(content)
        
        # Normalize page numbers in all sections
        for key in json_data:
            if isinstance(json_data[key], dict) and ('start_page' in json_data[key] or 'end_page' in json_data[key]):
                json_data[key] = self.normalize_page_numbers(json_data[key])
            elif isinstance(json_data[key], list):
                for item in json_data[key]:
                    if isinstance(item, dict):
                        self.normalize_page_numbers(item)
        
        with open(self.output_dir / "book_structure.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print("Structure extracted and saved to book_structure.json")
        return json_data


    def create_temp_pdf(self, start_page: int, end_page: int, temp_name: str) -> str:
        """Create temporary PDF for specific page range"""
        # Ensure page numbers are integers
        start_page = int(start_page)
        end_page = int(end_page)
        
        reader = PdfReader(self.pdf_path)
        writer = PdfWriter()
        for book_page in range(start_page, end_page + 1):
            pdf_index = book_page + PDF_PAGE_OFFSET - 1
            if 0 <= pdf_index < len(reader.pages):
                writer.add_page(reader.pages[pdf_index])
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.temp_dir / f"{temp_name}.pdf"
        with open(temp_path, "wb") as f:
            writer.write(f)
        self.temp_pdf_files.append(temp_path)
        return str(temp_path)


    def extract_json(self, text) -> Dict:
        """Extract JSON from LLM response"""
        match = re.search(r"{.*}", text, re.DOTALL)
        if match:
            raw_json = match.group(0)
            try:
                return json.loads(raw_json)
            except Exception as e:
                print("Error parsing JSON, raw response:")
                print(text)
                raise e
        else:
            print("No valid JSON found in LLM output!")
            print(text)
            raise ValueError("No valid JSON found")


    def cleanup_temp_files(self):
        """Delete all temporary PDF files and the temp directory"""
        print("\nCleaning up temporary files...")
        deleted_count = 0
        
        # Delete tracked temp PDF files
        for temp_file in self.temp_pdf_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {temp_file}: {e}")
        
        # Delete the entire temp directory if it exists
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print(f"Deleted {deleted_count} temporary PDF files and temp directory")
            else:
                print(f"Deleted {deleted_count} temporary PDF files")
        except Exception as e:
            print(f"Warning: Could not delete temp directory {self.temp_dir}: {e}")
        
        # Clear the tracking list
        self.temp_pdf_files.clear()


    def safe_process_section(self, section_info: Dict, section_name: str, process_func):
        """Safely process a section with error handling"""
        try:
            section_info = self.normalize_page_numbers(section_info)
            process_func(section_info)
            time.sleep(1)
        except Exception as e:
            print(f"Error processing {section_name}: {e}")
            print(f"Section info: {section_info}")


    def process_preface(self, preface_info: Dict):
        """Process the Preface section"""
        print(f"\nProcessing Preface: {preface_info.get('title', 'Preface')}")
        temp_pdf_path = self.create_temp_pdf(
            preface_info['start_page'],
            preface_info['end_page'],
            "preface"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Preface section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{preface_info.get('title', 'Preface')}",
            "number_of_pages": {int(preface_info['end_page']) - int(preface_info['start_page']) + 1},
            "content": "...",
            "summary": "...",
            "author_motivation": "...",
            "book_genesis": "...",
            "intended_audience": "...",
            "key_acknowledgments": ["..."],
            "page_range": "{preface_info['start_page']}-{preface_info['end_page']}"
        }}
        Extract the author's motivation, how the book came to be, and intended readership.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Preface.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Preface processed and saved")
        except Exception as e:
            print(f"Error processing preface: {e}")
        genai.delete_file(temp_file.name)


    def process_foreword(self, foreword_info: Dict):
        """Process the Foreword section"""
        print(f"\nProcessing Foreword: {foreword_info.get('title', 'Foreword')}")
        temp_pdf_path = self.create_temp_pdf(
            foreword_info['start_page'],
            foreword_info['end_page'],
            "foreword"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Foreword section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{foreword_info.get('title', 'Foreword')}",
            "number_of_pages": {int(foreword_info['end_page']) - int(foreword_info['start_page']) + 1},
            "content": "...",
            "summary": "...",
            "foreword_author": "...",
            "foreword_author_credentials": "...",
            "book_significance": "...",
            "key_endorsements": ["..."],
            "page_range": "{foreword_info['start_page']}-{foreword_info['end_page']}"
        }}
        Extract who wrote the foreword, their credentials, and why they endorse this book.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Foreword.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Foreword processed and saved")
        except Exception as e:
            print(f"Error processing foreword: {e}")
        genai.delete_file(temp_file.name)


    def process_acknowledgments(self, ack_info: Dict):
        """Process the Acknowledgments section"""
        print(f"\nProcessing Acknowledgments")
        temp_pdf_path = self.create_temp_pdf(
            ack_info['start_page'],
            ack_info['end_page'],
            "acknowledgments"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Acknowledgments section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{ack_info.get('title', 'Acknowledgments')}",
            "number_of_pages": {int(ack_info['end_page']) - int(ack_info['start_page']) + 1},
            "content": "...",
            "summary": "...",
            "acknowledged_individuals": ["..."],
            "acknowledged_institutions": ["..."],
            "funding_sources": ["..."],
            "research_network": "...",
            "page_range": "{ack_info['start_page']}-{ack_info['end_page']}"
        }}
        Extract all people, institutions, and funding sources acknowledged.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Acknowledgments.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Acknowledgments processed and saved")
        except Exception as e:
            print(f"Error processing acknowledgments: {e}")
        genai.delete_file(temp_file.name)


    def process_introduction(self, intro_info: Dict):
        """Process the Introduction section"""
        print(f"\nProcessing Introduction: {intro_info.get('title', 'Introduction')}")
        temp_pdf_path = self.create_temp_pdf(
            intro_info['start_page'],
            intro_info['end_page'],
            "introduction"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Introduction section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{intro_info.get('title', 'Introduction')}",
            "number_of_pages": {int(intro_info['end_page']) - int(intro_info['start_page']) + 1},
            "content": "... [IMAGE: Description]",
            "summary": "...",
            "key_themes": ["..."],
            "main_arguments": ["..."],
            "methodology": "...",
            "historiographical_context": "...",
            "research_questions": ["..."],
            "book_structure_overview": "...",
            "keywords": ["..."],
            "page_range": "{intro_info['start_page']}-{intro_info['end_page']}"
        }}
        Extract methodology, research questions, and historiographical framework.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Introduction.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Introduction processed and saved")
        except Exception as e:
            print(f"Error processing introduction: {e}")
        genai.delete_file(temp_file.name)


    def process_chapter(self, chapter_info: Dict, chapter_num: int):
        """Process individual chapter with enhanced metadata"""
        print(f"\nProcessing Chapter {chapter_num}: {chapter_info.get('title', 'Untitled')}")
        chapter_info = self.normalize_page_numbers(chapter_info)
        
        temp_pdf_path = self.create_temp_pdf(
            chapter_info['start_page'],
            chapter_info['end_page'],
            f"chapter_{chapter_num}"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this chapter comprehensively. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "chapter_number": "{chapter_info.get('chapter_number', chapter_num)}",
            "chapter_title": "{chapter_info.get('title', 'Unknown')}",
            "number_of_pages": {int(chapter_info['end_page']) - int(chapter_info['start_page']) + 1},
            "sections": [
                {{
                    "section_number": "...",
                    "section_title": "...",
                    "content": "... [IMAGE: Description] [TABLE: Description]",
                    "summary": "...",
                    "key_concepts": ["..."],
                    "page_range": "..."
                }}
            ],
            "chapter_summary": "...",
            "key_arguments": ["..."],
            "key_takeaways": ["..."],
            "historical_figures": [
                {{"name": "...", "role": "...", "significance": "...", "dates": "..."}}
            ],
            "historical_events": [
                {{"event": "...", "date": "...", "significance": "..."}}
            ],
            "geographic_locations": [
                {{"place": "...", "context": "...", "significance": "..."}}
            ],
            "sanskrit_hindi_terms": [
                {{"term": "...", "transliteration": "...", "translation": "...", "context": "..."}}
            ],
            "cross_references": [
                {{"reference_text": "...", "target": "...", "page": "..."}}
            ],
            "quotations": [
                {{"quote": "...", "source": "...", "context": "..."}}
            ],
            "tables_and_charts": [
                {{"type": "table/chart", "description": "...", "data_summary": "...", "page": "..."}}
            ],
            "images_and_diagrams": [
                {{"type": "...", "description": "...", "significance": "...", "page": "..."}}
            ],
            "footnotes_endnotes": [
                {{"note_number": "...", "content": "...", "page": "..."}}
            ],
            "controversial_points": ["..."],
            "alternative_viewpoints": ["..."],
            "keywords": ["..."]
        }}
        Instructions:
        - Extract ALL people mentioned with their roles and dates
        - Create a timeline of historical events with exact dates
        - Map all geographic locations with context
        - List all Sanskrit/Hindi terms with transliterations and translations
        - Identify cross-references to other chapters
        - Extract all quotations with proper attribution
        - Describe all tables, charts, images, and diagrams
        - Extract all footnotes/endnotes
        - Identify controversial or debated points
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            chapter_data = self.extract_json(response.text.strip())
            output_file = self.output_dir / f"Chapter_{chapter_num}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(chapter_data, f, indent=2, ensure_ascii=False)
            print(f"Chapter {chapter_num} processed and saved")
        except Exception as e:
            print(f"Error processing chapter {chapter_num}: {e}")
            print(response.text)
        genai.delete_file(temp_file.name)


    def process_appendix(self, appendix_info: Dict, appendix_num: int):
        """Process appendix section"""
        appendix_id = appendix_info.get('appendix_id', appendix_num)
        print(f"\nProcessing Appendix {appendix_id}: {appendix_info.get('title', 'Untitled')}")
        appendix_info = self.normalize_page_numbers(appendix_info)
        
        temp_pdf_path = self.create_temp_pdf(
            appendix_info['start_page'],
            appendix_info['end_page'],
            f"appendix_{appendix_id}"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this appendix. Keep all unicode exactly as in the original.
        Return JSON:
        {{
            "appendix_id": "{appendix_id}",
            "appendix_title": "{appendix_info.get('title', 'Unknown')}",
            "number_of_pages": {int(appendix_info['end_page']) - int(appendix_info['start_page']) + 1},
            "content": "...",
            "summary": "...",
            "purpose": "...",
            "key_information": ["..."],
            "tables_and_data": [
                {{"description": "...", "data_summary": "..."}}
            ],
            "references_to_chapters": ["..."]
        }}
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / f"Appendix_{appendix_id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Appendix {appendix_id} processed and saved")
        except Exception as e:
            print(f"Error processing appendix {appendix_id}: {e}")
        genai.delete_file(temp_file.name)


    def process_glossary(self, glossary_info: Dict):
        """Process the Glossary section"""
        print(f"\nProcessing Glossary")
        glossary_info = self.normalize_page_numbers(glossary_info)
        
        temp_pdf_path = self.create_temp_pdf(
            glossary_info['start_page'],
            glossary_info['end_page'],
            "glossary"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Glossary section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{glossary_info.get('title', 'Glossary')}",
            "number_of_pages": {int(glossary_info['end_page']) - int(glossary_info['start_page']) + 1},
            "terms": [
                {{
                    "term": "...",
                    "original_script": "...",
                    "transliteration": "...",
                    "definition": "...",
                    "etymology": "...",
                    "usage_context": "..."
                }}
            ],
            "term_count": 0,
            "languages_covered": ["..."],
            "page_range": "{glossary_info['start_page']}-{glossary_info['end_page']}"
        }}
        Extract every term with its definition, transliteration, and context.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Glossary.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Glossary processed and saved")
        except Exception as e:
            print(f"Error processing glossary: {e}")
        genai.delete_file(temp_file.name)


    def process_bibliography(self, bib_info: Dict):
        """Process the Bibliography section"""
        print(f"\nProcessing Bibliography")
        bib_info = self.normalize_page_numbers(bib_info)
        
        temp_pdf_path = self.create_temp_pdf(
            bib_info['start_page'],
            bib_info['end_page'],
            "bibliography"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Bibliography section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{bib_info.get('title', 'Bibliography')}",
            "number_of_pages": {int(bib_info['end_page']) - int(bib_info['start_page']) + 1},
            "sources": [
                {{
                    "citation": "...",
                    "author": "...",
                    "title": "...",
                    "year": "...",
                    "type": "book/journal/website/archive",
                    "language": "..."
                }}
            ],
            "source_count": 0,
            "source_types": {{"books": 0, "journals": 0, "websites": 0, "archives": 0}},
            "languages_represented": ["..."],
            "time_span": "earliest-latest year",
            "most_cited_authors": ["..."],
            "page_range": "{bib_info['start_page']}-{bib_info['end_page']}"
        }}
        Extract every bibliographic entry with complete details.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Bibliography.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Bibliography processed and saved")
        except Exception as e:
            print(f"Error processing bibliography: {e}")
        genai.delete_file(temp_file.name)


    def process_references(self, ref_info: Dict):
        """Process References and Notes section"""
        print(f"\nProcessing References and Notes")
        ref_info = self.normalize_page_numbers(ref_info)
        
        temp_pdf_path = self.create_temp_pdf(
            ref_info['start_page'],
            ref_info['end_page'],
            "references_and_notes"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze the references and notes section. Keep all unicode exactly as in the original.
        Return JSON:
        {{
            "section_title": "{ref_info.get('title', 'References and Notes')}",
            "number_of_pages": {int(ref_info['end_page']) - int(ref_info['start_page']) + 1},
            "content": "...",
            "summary": "...",
            "notes_by_chapter": [
                {{
                    "chapter": "...",
                    "notes": [
                        {{"note_number": "...", "content": "...", "citations": ["..."]}}
                    ]
                }}
            ],
            "reference_count": 0,
            "reference_types": ["books", "journals", "websites"]
        }}
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "References_and_Notes.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("References and notes processed and saved")
        except Exception as e:
            print(f"Error processing references: {e}")
        genai.delete_file(temp_file.name)


    def process_index(self, index_info: Dict):
        """Process the Index section"""
        print(f"\nProcessing Index")
        index_info = self.normalize_page_numbers(index_info)
        
        temp_pdf_path = self.create_temp_pdf(
            index_info['start_page'],
            index_info['end_page'],
            "index"
        )
        temp_file = self.upload_pdf_to_gemini(temp_pdf_path)
        prompt = f"""
        Analyze this Index section. Keep all unicode exactly as in the original.
        Return only valid JSON:
        {{
            "section_title": "{index_info.get('title', 'Index')}",
            "number_of_pages": {int(index_info['end_page']) - int(index_info['start_page']) + 1},
            "index_entries": [
                {{
                    "term": "...",
                    "original_script": "...",
                    "pages": ["..."],
                    "sub_entries": ["..."]
                }}
            ],
            "entry_count": 0,
            "page_range": "{index_info['start_page']}-{index_info['end_page']}"
        }}
        Extract all index entries with page references.
        """
        response = self.model.generate_content([temp_file, prompt])
        try:
            data = self.extract_json(response.text.strip())
            output_file = self.output_dir / "Index.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Index processed and saved")
        except Exception as e:
            print(f"Error processing index: {e}")
        genai.delete_file(temp_file.name)


    def generate_consolidated_metadata(self):
        """Generate consolidated metadata from all extracted data"""
        print("\nGenerating consolidated metadata...")
        
        metadata = {
            "book_title": self.file_name,
            "total_chapters": 0,
            "total_pages": 0,
            "all_historical_figures": [],
            "complete_timeline": [],
            "all_geographic_locations": [],
            "complete_terminology_index": [],
            "cross_reference_map": [],
            "bibliography_network": [],
            "keywords_by_frequency": []
        }
        
        # Aggregate data from all chapter files
        for chapter_file in sorted(self.output_dir.glob("Chapter_*.json")):
            try:
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    chapter_data = json.load(f)
                    metadata["total_chapters"] += 1
                    
                    if "historical_figures" in chapter_data:
                        metadata["all_historical_figures"].extend(chapter_data["historical_figures"])
                    
                    if "historical_events" in chapter_data:
                        metadata["complete_timeline"].extend(chapter_data["historical_events"])
                    
                    if "geographic_locations" in chapter_data:
                        metadata["all_geographic_locations"].extend(chapter_data["geographic_locations"])
                    
                    if "sanskrit_hindi_terms" in chapter_data:
                        metadata["complete_terminology_index"].extend(chapter_data["sanskrit_hindi_terms"])
                    
                    if "cross_references" in chapter_data:
                        metadata["cross_reference_map"].extend(chapter_data["cross_references"])
            except Exception as e:
                print(f"Error processing {chapter_file}: {e}")
        
        # Sort timeline by date
        metadata["complete_timeline"] = sorted(
            metadata["complete_timeline"],
            key=lambda x: x.get("date", "")
        )
        
        # Save consolidated metadata
        output_file = self.output_dir / "Consolidated_Metadata.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print("Consolidated metadata saved")


    def process_book(self):
        """Main processing pipeline"""
        print("=" * 60)
        print("Starting Comprehensive Book Data Enrichment Process")
        print("=" * 60)
        
        try:
            # Upload full PDF and extract structure
            full_pdf_file = self.upload_pdf_to_gemini(self.pdf_path)
            try:
                structure = self.extract_structure(full_pdf_file)
            finally:
                genai.delete_file(full_pdf_file.name)
            
            # Process all front matter
            if 'preface' in structure:
                self.safe_process_section(structure['preface'], 'Preface', self.process_preface)
            
            if 'foreword' in structure:
                self.safe_process_section(structure['foreword'], 'Foreword', self.process_foreword)
            
            if 'acknowledgments' in structure:
                self.safe_process_section(structure['acknowledgments'], 'Acknowledgments', self.process_acknowledgments)
            
            if 'introduction' in structure:
                self.safe_process_section(structure['introduction'], 'Introduction', self.process_introduction)
            
            # Process chapters
            if 'chapters' in structure:
                for idx, chapter in enumerate(structure['chapters'], 1):
                    try:
                        self.process_chapter(chapter, idx)
                        time.sleep(1)
                    except Exception as e:
                        print(f"Error processing chapter {idx}: {e}")
            
            # Process appendixes
            if 'appendixes' in structure:
                for idx, appendix in enumerate(structure['appendixes'], 1):
                    try:
                        self.process_appendix(appendix, idx)
                        time.sleep(1)
                    except Exception as e:
                        print(f"Error processing appendix {idx}: {e}")
            
            # Process back matter
            if 'glossary' in structure:
                self.safe_process_section(structure['glossary'], 'Glossary', self.process_glossary)
            
            if 'bibliography' in structure:
                self.safe_process_section(structure['bibliography'], 'Bibliography', self.process_bibliography)
            
            if 'references_and_notes' in structure:
                self.safe_process_section(structure['references_and_notes'], 'References and Notes', self.process_references)
            
            if 'index' in structure:
                self.safe_process_section(structure['index'], 'Index', self.process_index)
            
            # Generate consolidated metadata
            self.generate_consolidated_metadata()
            
            print("\n" + "=" * 60)
            print("Book Data Enrichment Complete!")
            print(f"Output saved to: {self.output_dir}")
            print("=" * 60)
        
        finally:
            # Always cleanup temporary files, even if processing fails
            self.cleanup_temp_files()


if __name__ == "__main__":
    enricher = BookDataEnricher(API_KEY, PDF_PATH, OUTPUT_BASE)
    enricher.process_book()