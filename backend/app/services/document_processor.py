# app/services/document_processor.py
"""
Service for processing uploaded documents and images
Supports: PDF, Word, Text files, Images (jpg, jpeg, png, etc.)
"""
import os
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import mimetypes
import PyPDF2
import docx

class DocumentProcessor:
    """Process various document types and images"""
    
    SUPPORTED_IMAGE_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
        'image/webp', 'image/bmp', 'image/svg+xml'
    }
    
    SUPPORTED_DOC_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/csv',
        'text/markdown',
        'application/json'
    }
    
    def __init__(self, upload_dir: str = None):
        """Initialize the document processor"""
        if upload_dir is None:
            # Use absolute path relative to the backend directory
            backend_dir = Path(__file__).parent.parent.parent
            upload_dir = backend_dir / "uploads"
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    def is_supported(self, mime_type: str) -> bool:
        """Check if the file type is supported"""
        return mime_type in self.SUPPORTED_IMAGE_TYPES or mime_type in self.SUPPORTED_DOC_TYPES
    
    def process_file(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """
        Process uploaded file and extract content
        Returns a dictionary with file info and extracted content
        """
        if not self.is_supported(mime_type):
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        result = {
            "file_path": file_path,
            "mime_type": mime_type,
            "file_type": self._get_file_type(mime_type),
            "content": None,
            "metadata": {}
        }
        
        # Process based on file type
        if mime_type in self.SUPPORTED_IMAGE_TYPES:
            result["content"] = self._process_image(file_path)
        elif mime_type in self.SUPPORTED_DOC_TYPES:
            result["content"] = self._process_document(file_path, mime_type)
        
        return result
    
    def _get_file_type(self, mime_type: str) -> str:
        """Get file type category"""
        if mime_type in self.SUPPORTED_IMAGE_TYPES:
            return "image"
        elif mime_type in self.SUPPORTED_DOC_TYPES:
            return "document"
        return "unknown"
    
    def _process_image(self, file_path: str) -> str:
        """Process image file - return base64 encoded data for vision models"""
        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            return image_data
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    def _process_document(self, file_path: str, mime_type: str) -> str:
        """Process document file and extract text"""
        try:
            # Text files - direct read
            if mime_type in ['text/plain', 'text/csv', 'text/markdown', 'application/json']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # PDF files
            elif mime_type == 'application/pdf':
                return self._extract_pdf_text(file_path)
            
            # Word documents
            elif mime_type in ['application/msword', 
                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return self._extract_docx_text(file_path)
            
            return None
        except Exception as e:
            print(f"Error processing document: {e}")
            return None
    
    def _extract_pdf_text(self, file_path: str) -> Optional[str]:
        """Extract text from PDF"""
        try:
            text_content = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
            return "\n\n".join(text_content)
        except ImportError:
            return "[PDF content - PyPDF2 required for text extraction]"
        except Exception as e:
            return f"[Error extracting PDF: {str(e)}]"
    
    def _extract_docx_text(self, file_path: str) -> Optional[str]:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
        except ImportError:
            return "[Word document content - python-docx required for text extraction]"
        except Exception as e:
            return f"[Error extracting Word document: {str(e)}]"
    
    def cleanup_file(self, file_path: str):
        """Delete uploaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up file: {e}")

# Global instance
document_processor = DocumentProcessor()

