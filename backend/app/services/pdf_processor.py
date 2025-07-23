"""
PDF Processing Service

Handles PDF preprocessing for AI document analysis including text extraction,
image optimization, and document structure analysis.
"""

import io
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class PreprocessingResult:
    """PDF preprocessing result"""
    text_content: str
    images: List[str]  # Base64 encoded images
    document_analysis: Dict[str, Any]
    file_metadata: Dict[str, Any]


class PDFProcessor:
    """PDF preprocessing pipeline for AI analysis"""
    
    def __init__(self):
        self.max_image_size = (1024, 1024)
        self.max_pages = 3  # Limit pages for cost control
        self.supported_formats = ['.pdf']
        
    async def process(self, pdf_path: str) -> PreprocessingResult:
        """Comprehensive PDF preprocessing for AI analysis"""
        
        # Validate file
        if not await self._validate_pdf_file(pdf_path):
            raise ValueError(f"Invalid PDF file: {pdf_path}")
        
        logger.debug(f"Processing PDF: {pdf_path}")
        
        # Extract text content
        text_content = await self._extract_text_content(pdf_path)
        
        # Extract and optimize images
        images = await self._extract_and_optimize_images(pdf_path)
        
        # Analyze document structure
        document_analysis = await self._analyze_document_structure(pdf_path)
        
        # Get file metadata
        file_metadata = await self._get_file_metadata(pdf_path)
        
        logger.debug(f"PDF processing complete: {len(text_content)} chars text, "
                    f"{len(images)} images extracted")
        
        return PreprocessingResult(
            text_content=text_content,
            images=images,
            document_analysis=document_analysis,
            file_metadata=file_metadata
        )
    
    async def _validate_pdf_file(self, pdf_path: str) -> bool:
        """Validate PDF file"""
        try:
            path = Path(pdf_path)
            
            # Check if file exists
            if not path.exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return False
            
            # Check file extension
            if path.suffix.lower() not in self.supported_formats:
                logger.error(f"Unsupported file format: {path.suffix}")
                return False
            
            # Check file size (max 50MB)
            file_size = path.stat().st_size
            if file_size > 50 * 1024 * 1024:
                logger.error(f"PDF file too large: {file_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return False
    
    async def _extract_text_content(self, pdf_path: str) -> str:
        """Extract text using multiple methods for best coverage"""
        text_content = ""
        
        # Method 1: PyMuPDF (fast, good for text-based PDFs)
        try:
            text_content = await self._extract_with_pymupdf(pdf_path)
            if text_content.strip():
                logger.debug("Text extracted successfully with PyMuPDF")
                return text_content
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Method 2: pdf-plumber (better for complex layouts)
        try:
            text_content = await self._extract_with_pdfplumber(pdf_path)
            if text_content.strip():
                logger.debug("Text extracted successfully with pdfplumber")
                return text_content
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Method 3: OCR fallback for scanned documents
        try:
            text_content = await self._extract_with_ocr(pdf_path)
            logger.debug("Text extracted with OCR fallback")
            return text_content
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
        
        return text_content
    
    async def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """Extract text with PyMuPDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page_num in range(min(doc.page_count, self.max_pages)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
            
            doc.close()
            return "\n".join(text_parts)
            
        except ImportError:
            logger.warning("PyMuPDF not available")
            return ""
        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {e}")
            return ""
    
    async def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text with pdf-plumber"""
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    if page_num >= self.max_pages:
                        break
                    
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
            
            return "\n".join(text_parts)
            
        except ImportError:
            logger.warning("pdfplumber not available")
            return ""
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {e}")
            return ""
    
    async def _extract_with_ocr(self, pdf_path: str) -> str:
        """Extract text with OCR (fallback for scanned documents)"""
        try:
            # This would use Tesseract OCR in production
            # For now, return placeholder
            logger.warning("OCR not implemented, returning placeholder")
            return "OCR_PLACEHOLDER_TEXT"
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ""
    
    async def _extract_and_optimize_images(self, pdf_path: str) -> List[str]:
        """Extract images and optimize for AI processing"""
        images = []
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(doc.page_count, self.max_pages)):
                page = doc[page_num]
                
                # Render page as high-quality image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Optimize image for AI processing
                optimized_img = await self._optimize_image_for_ai(img_data)
                
                # Convert to base64 for AI APIs
                import base64
                base64_img = base64.b64encode(optimized_img).decode('utf-8')
                images.append(base64_img)
            
            doc.close()
            
        except ImportError:
            logger.warning("PyMuPDF not available for image extraction")
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
        
        return images
    
    async def _optimize_image_for_ai(self, image_data: bytes) -> bytes:
        """Optimize image for AI processing (size, quality, format)"""
        try:
            from PIL import Image, ImageEnhance
            
            # Load image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
            
            # Enhance contrast for better OCR
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Save optimized image
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            
            return output.getvalue()
            
        except ImportError:
            logger.warning("PIL not available for image optimization")
            return image_data
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return image_data
    
    async def _analyze_document_structure(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze document structure and characteristics"""
        
        analysis = {
            "page_count": 0,
            "has_images": False,
            "has_text": False,
            "is_scanned": False,
            "language": "unknown",
            "layout_complexity": "simple"
        }
        
        try:
            import fitz
            
            doc = fitz.open(pdf_path)
            analysis["page_count"] = doc.page_count
            
            # Analyze first page
            if doc.page_count > 0:
                page = doc[0]
                
                # Check for text
                text = page.get_text()
                analysis["has_text"] = bool(text.strip())
                
                # Check for images
                image_list = page.get_images()
                analysis["has_images"] = len(image_list) > 0
                
                # Simple heuristic for scanned documents
                if not analysis["has_text"] and analysis["has_images"]:
                    analysis["is_scanned"] = True
                
                # Simple language detection
                if text:
                    if any(char in text for char in ['ă', 'â', 'î', 'ș', 'ț']):
                        analysis["language"] = "romanian"
                    else:
                        analysis["language"] = "english"
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Document structure analysis failed: {e}")
        
        return analysis
    
    async def _get_file_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Get file metadata"""
        
        metadata = {}
        
        try:
            path = Path(pdf_path)
            stat = path.stat()
            
            metadata.update({
                "filename": path.name,
                "file_size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "extension": path.suffix.lower()
            })
            
            # Try to get PDF-specific metadata
            try:
                import fitz
                doc = fitz.open(pdf_path)
                pdf_metadata = doc.metadata
                doc.close()
                
                metadata.update({
                    "pdf_version": pdf_metadata.get("format", ""),
                    "title": pdf_metadata.get("title", ""),
                    "author": pdf_metadata.get("author", ""),
                    "subject": pdf_metadata.get("subject", ""),
                    "creator": pdf_metadata.get("creator", "")
                })
                
            except Exception as e:
                logger.debug(f"Could not extract PDF metadata: {e}")
            
        except Exception as e:
            logger.error(f"File metadata extraction failed: {e}")
        
        return metadata 