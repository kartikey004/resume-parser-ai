import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageOps
import docx
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def _extract_text_from_pdf(file_path: Path) -> str:
    """
    Extracts text from a PDF.
    First tries direct text extraction. If that yields little text,
    it falls back to using OCR.
    """
    log.info(f"Attempting direct text extraction from PDF: {file_path.name}")
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # If text is very short, it might be a scanned PDF.
        if len(text.strip()) < 100:
            log.warning(f"Direct extraction yielded minimal text. Attempting OCR fallback for {file_path.name}")
            return _extract_text_with_ocr(file_path)
            
        log.info(f"Successfully extracted text directly from {file_path.name}")
        return text

    except Exception as e:
        log.error(f"Error during direct PDF extraction, falling back to OCR: {e}")
        # Fallback to OCR if any error occurs
        return _extract_text_with_ocr(file_path)

def _extract_text_with_ocr(file_path: Path) -> str:
    """
    Extracts text from a PDF using OCR (Tesseract).
    """
    log.info(f"Performing OCR on {file_path.name}...")
    text = ""
    try:
        # Convert PDF pages to images
        images = convert_from_path(file_path)
        
        # Process each image with Tesseract
        for i, img in enumerate(images):
            log.info(f"Processing page {i+1} with OCR...")
            # Pre-process image for better OCR
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)
            text += pytesseract.image_to_string(img) + "\n"
            
        log.info(f"Successfully extracted text via OCR from {file_path.name}")
        return text
    except Exception as e:
        log.error(f"Failed to process PDF with OCR ({file_path.name}): {e}")
        return ""

def _extract_text_from_docx(file_path: Path) -> str:
    """
    Extracts text from a .docx file.
    """
    log.info(f"Extracting text from DOCX: {file_path.name}")
    try:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        log.info(f"Successfully extracted text from {file_path.name}")
        return text
    except Exception as e:
        log.error(f"Failed to extract text from DOCX ({file_path.name}): {e}")
        return ""

def _extract_text_from_image(file_path: Path) -> str:
    """
    Extracts text from a single image file (PNG, JPG, etc.) using OCR.
    """
    log.info(f"Extracting text from image: {file_path.name}")
    try:
        img = Image.open(file_path)
        # Pre-process image
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        text = pytesseract.image_to_string(img)
        log.info(f"Successfully extracted text from {file_path.name}")
        return text
    except Exception as e:
        log.error(f"Failed to extract text from image ({file_path.name}): {e}")
        return ""

def _extract_text_from_txt(file_path: Path) -> str:
    """
    Extracts text from a plain .txt file.
    """
    log.info(f"Extracting text from TXT: {file_path.name}")
    try:
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        log.error(f"Failed to read text from TXT ({file_path.name}): {e}")
        return ""

def extract_text_from_file(file_path_str: str, content_type: str) -> str:
    """
    Main dispatcher function.
    Selects the correct parsing function based on the file's content type.
    """
    file_path = Path(file_path_str)
    
    if not file_path.exists():
        log.error(f"File not found at path: {file_path_str}")
        return ""

    log.info(f"Extracting text from {file_path.name} with content_type {content_type}")

    if content_type == "application/pdf":
        return _extract_text_from_pdf(file_path)
    
    elif content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
        "application/msword" # .doc (might need antiword, but python-docx is standard)
    ]:
        return _extract_text_from_docx(file_path)
    
    elif content_type.startswith("image/"): # image/png, image/jpeg
        return _extract_text_from_image(file_path)
        
    elif content_type == "text/plain":
        return _extract_text_from_txt(file_path)

    else:
        log.warning(f"Unsupported content_type '{content_type}' for file {file_path.name}. Attempting plain text read as fallback.")
        try:
            return _extract_text_from_txt(file_path)
        except Exception:
            log.error(f"Fallback text read failed for {file_path.name}.")
            return ""

