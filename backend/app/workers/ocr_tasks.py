from app.workers.celery_app import celery_app
from app.models.attachment import Attachment
from app.models.processed_document import ProcessedDocument
from app.services.document.document_processor import DocumentProcessor
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_fresh_session_factory():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
    )
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False), engine


# Deprecated Celery task - keeping wrapper for interface compatibility, but core runs async
@celery_app.task(name="app.workers.ocr_tasks.process_attachment_task")
def process_attachment_task(attachment_id_str: str):
    logger.info(f"Starting Celery document processing task wrapper for {attachment_id_str}")
    asyncio.run(run_process_attachment(attachment_id_str))

async def run_process_attachment(attachment_id_str: str):
    logger.info(f"Running async process_attachment for {attachment_id_str}")
    att_id = uuid.UUID(attachment_id_str)
    storage_path = None
    mime_type = None

    SessionLocal, engine = get_fresh_session_factory()
    try:
        # Step 1: Fetch attachment metadata
        async with SessionLocal() as db:
            att = (await db.execute(select(Attachment).where(Attachment.id == att_id))).scalars().first()
            if not att:
                logger.error(f"Attachment {attachment_id_str} not found in DB")
                return
            if att.is_processed:
                logger.info(f"Attachment {attachment_id_str} already processed. Skipping.")
                return
            storage_path = att.storage_path
            mime_type = att.mime_type

        # Step 2: Extract text OUTSIDE any DB session (can be slow - OCR, Excel parsing, etc.)
        try:
            extracted_text, page_count, method, duration = DocumentProcessor.extract_text(
                file_path=storage_path,
                mime_type=mime_type
            )
        except Exception as e:
            logger.error(f"Text extraction failed for {attachment_id_str}: {e}", exc_info=True)
            return

        # Step 3: Save processed document to DB
        async with SessionLocal() as db:
            att = (await db.execute(select(Attachment).where(Attachment.id == att_id))).scalars().first()
            if not att:
                return

            doc_stmt = select(ProcessedDocument).where(ProcessedDocument.attachment_id == att_id)
            doc = (await db.execute(doc_stmt)).scalars().first()

            if doc:
                doc.extracted_text = extracted_text
                doc.page_count = page_count
                doc.processing_method = method
                doc.processing_time_seconds = duration
            else:
                doc = ProcessedDocument(
                    attachment_id=att_id,
                    extracted_text=extracted_text,
                    page_count=page_count,
                    processing_method=method,
                    processing_time_seconds=duration
                )
                db.add(doc)

            att.is_processed = True
            await db.commit()
            await db.refresh(doc)
            doc_id_str = str(doc.id)
            logger.info(f"Processed attachment {attachment_id_str} via '{method}' in {duration:.2f}s. Chars: {len(extracted_text or '')}")

        # Step 4: Trigger embedding task directly in async context
        from app.workers.embedding_tasks import run_generate_document_embeddings
        await run_generate_document_embeddings(doc_id_str)

    except Exception as e:
        logger.error(f"Failed to process attachment {attachment_id_str}: {e}", exc_info=True)
    finally:
        await engine.dispose()
