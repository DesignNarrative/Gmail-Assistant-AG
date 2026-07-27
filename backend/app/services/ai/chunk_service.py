from typing import List
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for semantic search.
    Returns a list of chunk strings.
    """
    if not text or len(text.strip()) == 0:
        return []

    text = text.strip()
    
    # If text is shorter than chunk_size, return as single chunk
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at a sentence or newline boundary
        if end < len(text):
            # Look for last newline or period before end
            break_pos = text.rfind('\n', start, end)
            if break_pos == -1 or break_pos <= start:
                break_pos = text.rfind('. ', start, end)
            if break_pos != -1 and break_pos > start:
                end = break_pos + 1
                
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # Move start forward with overlap (must always advance to avoid infinite loop)
        next_start = end - overlap
        if next_start <= start:
            # Boundary break pulled 'end' too close to 'start'; skip overlap to guarantee progress
            next_start = end
        start = next_start
        if start >= len(text):
            break

    logger.info(f"Chunked text ({len(text)} chars) into {len(chunks)} chunks")
    return chunks
