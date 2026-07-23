from app.workers.celery_app import celery_app
from app.models.processed_document import ProcessedDocument
from app.models.attachment import Attachment
from app.models.email import Email
from app.models.document_chunk import DocumentChunk
from app.services.ai.chunk_service import chunk_text
from app.services.ai.embedding_service import generate_embeddings
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
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
@celery_app.task(name="app.workers.embedding_tasks.generate_email_embeddings_task")
def generate_email_embeddings_task(email_id_str: str):
    logger.info(f"Starting Celery email embedding task wrapper for {email_id_str}")
    asyncio.run(run_generate_email_embeddings(email_id_str))

async def run_generate_email_embeddings(email_id_str: str):
    logger.info(f"Running async generate_email_embeddings for {email_id_str}")
    e_id = uuid.UUID(email_id_str)
    SessionLocal, engine = get_fresh_session_factory()
    try:
        # Step 1: Fetch email data
        full_text = None
        header_info = None
        async with SessionLocal() as db:
            email_rec = (await db.execute(select(Email).where(Email.id == e_id))).scalars().first()
            if not email_rec:
                logger.error(f"Email {email_id_str} not found in DB")
                return

            header_info = (
                f"[EMAIL | Subject: {email_rec.subject} | "
                f"From: {email_rec.sender_name or ''} <{email_rec.sender_email}> | "
                f"Date: {email_rec.date_sent or email_rec.date_received}]"
            )
            body = email_rec.body_text or email_rec.snippet or ""
            full_text = (
                f"{header_info}\n\n"
                f"Subject: {email_rec.subject}\n"
                f"From: {email_rec.sender_name or ''} <{email_rec.sender_email}>\n"
                f"Date: {email_rec.date_sent or email_rec.date_received}\n\n"
                f"Body:\n{body}"
            )

        if not full_text or not full_text.strip():
            logger.warning(f"Email {email_id_str} has no text content. Skipping.")
            return

        # Step 2: Generate chunks + embeddings OUTSIDE DB session
        chunks = chunk_text(full_text)
        if not chunks:
            logger.warning(f"No chunks produced for email {email_id_str}")
            return

        embeddings = generate_embeddings(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings for email {email_id_str}")

        # Step 3: Save chunks to DB
        async with SessionLocal() as db:
            # Delete old chunks for this email (in case of re-sync)
            await db.execute(delete(DocumentChunk).where(DocumentChunk.email_id == e_id))

            # Fetch email record to assign user_id and mark as processed
            stmt_email = select(Email).where(Email.id == e_id)
            email_rec = (await db.execute(stmt_email)).scalars().first()

            if email_rec:
                user_id = email_rec.user_id
                for idx, (chunk_str, emb_vector) in enumerate(zip(chunks, embeddings)):
                    formatted_chunk = f"{header_info}\n{chunk_str}" if not chunk_str.startswith("[EMAIL") else chunk_str
                    chunk_obj = DocumentChunk(
                        email_id=e_id,
                        user_id=user_id,
                        chunk_text=formatted_chunk,
                        chunk_index=idx,
                        embedding=emb_vector
                    )
                    db.add(chunk_obj)

                # Set email.is_processed to True so we don't re-embed it next time
                email_rec.is_processed = True

            await db.commit()
            logger.info(f"Saved {len(chunks)} email chunks and marked email as processed for {email_id_str}")

    except Exception as e:
        logger.error(f"Failed to generate email embeddings for {email_id_str}: {e}", exc_info=True)
    finally:
        await engine.dispose()


# Deprecated Celery task - keeping wrapper for interface compatibility, but core runs async
@celery_app.task(name="app.workers.embedding_tasks.generate_document_embeddings_task")
def generate_document_embeddings_task(processed_doc_id_str: str):
    logger.info(f"Starting Celery embedding task wrapper for processed document {processed_doc_id_str}")
    asyncio.run(run_generate_document_embeddings(processed_doc_id_str))

async def run_generate_document_embeddings(processed_doc_id_str: str):
    logger.info(f"Running async generate_document_embeddings for processed document {processed_doc_id_str}")
    doc_id = uuid.UUID(processed_doc_id_str)
    SessionLocal, engine = get_fresh_session_factory()

    extracted_text = None
    att_filename = None
    att_id = None
    email_subject = None
    email_sender_name = None
    email_sender_email_addr = None
    email_date = None
    email_id = None
    user_id = None

    try:
        # Step 1: Fetch doc metadata
        async with SessionLocal() as db:
            stmt = (
                select(ProcessedDocument, Attachment, Email)
                .join(Attachment, Attachment.id == ProcessedDocument.attachment_id)
                .join(Email, Email.id == Attachment.email_id)
                .where(ProcessedDocument.id == doc_id)
            )
            row = (await db.execute(stmt)).first()

            if not row:
                # Try without email join (standalone attachment)
                stmt2 = (
                    select(ProcessedDocument, Attachment)
                    .join(Attachment, Attachment.id == ProcessedDocument.attachment_id)
                    .where(ProcessedDocument.id == doc_id)
                )
                row2 = (await db.execute(stmt2)).first()
                if not row2:
                    logger.error(f"Processed document {processed_doc_id_str} not found in DB")
                    return
                doc, att = row2
                email_rec = None
            else:
                doc, att, email_rec = row

            if not doc.extracted_text or not doc.extracted_text.strip():
                logger.warning(f"Document {processed_doc_id_str} has no extracted text. Skipping.")
                return

            extracted_text = doc.extracted_text
            att_filename = att.filename
            att_id = att.id
            if email_rec:
                email_subject = email_rec.subject
                email_sender_name = email_rec.sender_name
                email_sender_email_addr = email_rec.sender_email
                email_date = email_rec.date_sent or email_rec.date_received
                email_id = email_rec.id
                user_id = email_rec.user_id

        # Step 2: Build metadata prefix + generate chunks + embeddings OUTSIDE DB session
        if email_id:
            meta_prefix = (
                f"[DOCUMENT ATTACHMENT: {att_filename} | "
                f"From Email: '{email_subject}' | "
                f"Sender: {email_sender_name or ''} <{email_sender_email_addr}> | "
                f"Date: {email_date}]"
            )
        else:
            meta_prefix = f"[DOCUMENT ATTACHMENT: {att_filename}]"

        chunks = chunk_text(extracted_text)
        if not chunks:
            logger.warning(f"No chunks produced for document {processed_doc_id_str}")
            return

        embeddings = generate_embeddings(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings for document {processed_doc_id_str} ({att_filename})")

        # Step 3: Save chunks to DB
        async with SessionLocal() as db:
            await db.execute(delete(DocumentChunk).where(DocumentChunk.processed_doc_id == doc_id))

            for idx, (chunk_str, emb_vector) in enumerate(zip(chunks, embeddings)):
                formatted_chunk = f"{meta_prefix}\n{chunk_str}"
                chunk_obj = DocumentChunk(
                    processed_doc_id=doc_id,
                    attachment_id=att_id,
                    email_id=email_id,
                    user_id=user_id,
                    chunk_text=formatted_chunk,
                    chunk_index=idx,
                    embedding=emb_vector
                )
                db.add(chunk_obj)

            await db.commit()
            logger.info(f"Saved {len(chunks)} document chunks for {processed_doc_id_str} ({att_filename})")

    except Exception as e:
        logger.error(f"Failed to generate embeddings for document {processed_doc_id_str}: {e}", exc_info=True)
    finally:
        await engine.dispose()
