# app/utils/document_utils.py
import io
import PyPDF2
import asyncio
import logging
from fastapi import HTTPException, status, UploadFile
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Define allowed document types
ALLOWED_DOCUMENT_TYPES = [
    "application/pdf", 
    "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
]

class DocumentProcessingError(Exception):
    """Exception raised for errors in document processing."""
    pass

async def validate_document_type(document: UploadFile) -> None:
    """
    Validate that the uploaded document is of an allowed type.
    
    Args:
        document: The uploaded file to validate
    
    Raises:
        HTTPException: If the document type is not allowed
    """
    if document.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "File must be a PDF, Word document or a text file"}
        )

async def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        pdf_file: The PDF file to extract text from
    
    Returns:
        Extracted text from the PDF
    
    Raises:
        DocumentProcessingError: If text extraction fails
    """
    try:
        # Read file content
        await pdf_file.seek(0)  # Reset file position
        content = await pdf_file.read()
        
        # Use PyPDF2 to extract text
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        
        # Process in chunks to prevent memory issues
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
            
            # Allow other async tasks to run
            if page_num % 5 == 0:
                await asyncio.sleep(0)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise DocumentProcessingError(f"Error extracting text from PDF: {str(e)}")

async def extract_text_from_document(document: UploadFile) -> str:
    """
    Extract text from a document based on its content type.
    
    Args:
        document: The document to extract text from
    
    Returns:
        Extracted text from the document
    
    Raises:
        DocumentProcessingError: If text extraction fails
    """
    try:
        content_type = document.content_type.lower()
        
        if "pdf" in content_type:
            return await extract_text_from_pdf(document)
        elif "docx" in content_type or "doc" in content_type or "word" in content_type:
            # You can add Word document extraction here if needed
            # For now, we'll read raw content and convert to string
            await document.seek(0)
            content = await document.read()
            return f"Document content (binary): {len(content)} bytes"
        elif "text/plain" in content_type:
            await document.seek(0)
            content = await document.read()
            return content.decode('utf-8')
        else:
            await document.seek(0)
            content = await document.read()
            return f"Unknown document type: {content_type}, size: {len(content)} bytes"
    except Exception as e:
        logger.error(f"Error extracting text from document: {str(e)}")
        raise DocumentProcessingError(f"Error extracting text from document: {str(e)}")

async def process_document(document: UploadFile) -> Tuple[str, float]:
    """
    Process a document:
    1. Validate document type
    2. Extract text
    3. Return text and size
    
    Args:
        document: The document to process
    
    Returns:
        Tuple containing extracted text and its size in KB
    
    Raises:
        HTTPException: If document processing fails
    """
    try:
        # Validate document type
        await validate_document_type(document)
        
        # Extract text
        extracted_text = await extract_text_from_document(document)
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Could not extract text from document"}
            )
        
        # Calculate text size
        text_size_kb = len(extracted_text) / 1024
        logger.info(f"Extracted text size: {text_size_kb:.2f} KB")
        
        return extracted_text, text_size_kb
    except DocumentProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)}
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Error processing document: {str(e)}"}
        )