import re
from typing import List
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for semantic search.
    Cleans invisible unicode characters, respects natural boundaries,
    and guarantees strict forward progress without infinite loops or memory leaks.
    """
    if not text or len(text.strip()) == 0:
        return []

    # Clean zero-width and invisible unicode characters that often appear in automated/marketing emails
    text = re.sub(r'[\u200b-\u200d\ufeff\u034f\u200e\u200f]', '', text)
    # Normalize excessive whitespaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    # If text is shorter than chunk_size, return as single chunk
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Try to break at a sentence or newline boundary if not at the very end
        if end < text_len:
            # Only search for boundaries in the upper section of the chunk window
            # to guarantee substantial chunk sizes and prevent backwards/stalled stepping
            min_boundary = start + max(overlap + 50, chunk_size // 2)
            break_pos = text.rfind('\n', min_boundary, end)
            if break_pos == -1:
                break_pos = text.rfind('. ', min_boundary, end)
            if break_pos != -1:
                end = break_pos + 1
                
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # Strictly guarantee forward progress
        next_start = end - overlap
        if next_start <= start:
            next_start = end
            
        start = next_start

    logger.info(f"Chunked text ({text_len} chars) into {len(chunks)} chunks")
    return chunks
