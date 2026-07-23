import os
import time
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    @staticmethod
    def extract_text(file_path: str, mime_type: str) -> tuple[str, int, str, float]:
        """
        Extracts text from a file based on its MIME type.
        All OCR/document libraries are imported lazily at call time
        to avoid hard import failures if packages are loaded before PATH is set.

        Returns:
            extracted_text (str)
            page_count (int)
            method (str): 'direct_text' or 'ocr'
            duration (float): execution time in seconds
        """
        start_time = time.time()
        extracted_text = ""
        page_count = 1
        method = "direct_text"

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if mime_type == 'application/pdf' or ext == '.pdf':
                extracted_text, page_count, method = DocumentProcessor._process_pdf(file_path)
            elif mime_type.startswith('image/') or ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                extracted_text = DocumentProcessor._process_image(file_path)
                page_count = 1
                method = "ocr"
            elif mime_type in [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ] or ext in ['.xlsx', '.xls', '.csv']:
                extracted_text = DocumentProcessor._process_excel(file_path)
                page_count = 1
                method = "direct_text"
            elif mime_type in [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword'
            ] or ext in ['.docx', '.doc']:
                extracted_text = DocumentProcessor._process_docx(file_path)
                page_count = 1
                method = "direct_text"
            elif mime_type.startswith('text/') or ext in ['.txt', '.json', '.md']:
                extracted_text = DocumentProcessor._process_text(file_path)
                page_count = 1
                method = "direct_text"
            else:
                try:
                    extracted_text = DocumentProcessor._process_text(file_path)
                    page_count = 1
                    method = "direct_text"
                except Exception:
                    raise ValueError(f"Unsupported file format: {mime_type} ({ext})")

        except Exception as ocr_err:
            logger.error(f"Error extracting text from {file_path}: {ocr_err}")
            return f"[Encrypted/Unreadable PDF Document: {ocr_err}]", 1, "failed", time.time() - start_time

        duration = time.time() - start_time
        # Strip NUL bytes (0x00) that can crash PostgreSQL UTF8 text insertion
        clean_text = extracted_text.replace('\x00', '').strip()
        return clean_text, page_count, method, duration

    @staticmethod
    def _process_pdf(file_path: str) -> tuple[str, int, str]:
        import pdfplumber
        text_content = []
        page_count = 0
        method = "direct_text"

        # 1. Try direct text extraction with pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
        except Exception as e:
            logger.warning(f"Direct PDF text extraction failed for {file_path}, falling back to OCR: {e}")

        full_text = "\n".join(text_content).strip()

        # 2. If text is empty/too short (scanned document), run OCR
        if len(full_text) < 50:
            from pdf2image import convert_from_path
            import pytesseract

            logger.info(f"PDF appears to be scanned (extracted length: {len(full_text)}). Running OCR...")
            text_content = []
            method = "ocr"

            try:
                images = convert_from_path(file_path, dpi=150)
                page_count = len(images)

                for i, img in enumerate(images):
                    logger.info(f"Running OCR on page {i+1}/{page_count}")
                    page_text = pytesseract.image_to_string(img, lang='eng')
                    if page_text:
                        text_content.append(page_text)
            except Exception as e:
                logger.error(f"PDF OCR failed for {file_path}: {e}")
                raise e

            full_text = "\n".join(text_content).strip()

        return full_text, page_count, method

    @staticmethod
    def _process_image(file_path: str) -> str:
        from PIL import Image
        import pytesseract

        logger.info(f"Running OCR on image {file_path}")
        with Image.open(file_path) as img:
            return pytesseract.image_to_string(img, lang='eng')

    @staticmethod
    def _process_docx(file_path: str) -> str:
        import docx
        try:
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as docx_err:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.doc' or 'doc' in file_path:
                logger.info(f"python-docx failed for legacy .doc file {file_path}. Trying binary extraction fallback...")
                try:
                    return DocumentProcessor._process_legacy_doc(file_path)
                except Exception as legacy_err:
                    logger.error(f"Legacy .doc extraction fallback failed: {legacy_err}")
            raise docx_err

    @staticmethod
    def _process_legacy_doc(file_path: str) -> str:
        import re
        with open(file_path, "rb") as f:
            data = f.read()
            
        # Extract UTF-16LE printable strings (since older .doc formats store text in UTF-16LE streams)
        utf16_strings = []
        pattern_utf16 = re.compile(rb'(?:[\x20-\x7E\x0A\x0D]\x00){4,}')
        for match in pattern_utf16.finditer(data):
            try:
                s = match.group(0).decode("utf-16le").strip()
                if s:
                    utf16_strings.append(s)
            except Exception:
                pass
                
        # Extract ASCII printable strings
        ascii_strings = []
        pattern_ascii = re.compile(rb'[\x20-\x7E\x0A\x0D]{4,}')
        for match in pattern_ascii.finditer(data):
            try:
                s = match.group(0).decode("ascii").strip()
                if s:
                    ascii_strings.append(s)
            except Exception:
                pass
                
        # Combine extracted strings
        all_strings = utf16_strings + ascii_strings
        unique_strings = []
        seen = set()
        
        for s in all_strings:
            s_clean = re.sub(r'\s+', ' ', s).strip()
            if len(s_clean) > 8 and s_clean not in seen:
                # Exclude strings that look purely like metadata/binary junk
                if not re.match(r'^[_\W\d]+$', s_clean):
                    unique_strings.append(s_clean)
                    seen.add(s_clean)
                    
        return "\n\n".join(unique_strings)

    @staticmethod
    def _process_text(file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    @staticmethod
    def _process_excel(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            return DocumentProcessor._process_text(file_path)
        try:
            import pandas as pd
            excel_file = pd.ExcelFile(file_path)
            sheet_texts = []
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                # Drop all-NaN rows/cols for clean prompt text
                df = df.dropna(how='all')
                sheet_texts.append(f"--- SHEET: {sheet_name} ---\n" + df.to_string(index=False))
            return "\n\n".join(sheet_texts)
        except Exception as e:
            logger.warning(f"Pandas Excel reading failed for {file_path}, trying basic text fallback: {e}")
            return DocumentProcessor._process_text(file_path)
