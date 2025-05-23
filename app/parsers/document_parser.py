import os
from typing import Dict
from app.parsers.docling_parser import DoclingParser, DOCLING_AVAILABLE

class DocumentParser:
    """Universal document parser using Docling for superior multimodal extraction"""
    
    def __init__(self):
        if DOCLING_AVAILABLE:
            self.parser = DoclingParser()
        else:
            raise ImportError("Docling is required for document parsing. Install with: pip install docling")
    
    def parse_document(self, file_path: str) -> Dict:
        """Parse any supported document format using Docling"""
        return self.parser.parse_document(file_path)
    
    def get_document_summary(self, parsed_document: Dict) -> Dict:
        """Generate a summary of parsed document content"""
        return self.parser.get_document_summary(parsed_document)