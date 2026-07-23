import asyncio
from app.core.database import AsyncSessionLocal
from app.models.attachment import Attachment
from app.models.processed_document import ProcessedDocument
from app.models.email import Email
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        # Check emails
        emails = (await db.execute(select(Email))).scalars().all()
        print(f"\n{'='*50}")
        print(f"Total emails in DB: {len(emails)}")
        for e in emails:
            print(f"  - [{e.subject[:50]}] from {e.sender_email} | attachments={e.has_attachments}")

        # Check attachments
        atts = (await db.execute(select(Attachment))).scalars().all()
        print(f"\nTotal attachments in DB: {len(atts)}")
        for a in atts:
            print(f"  - {a.filename} | {a.mime_type} | size={a.file_size} | processed={a.is_processed}")

        # Check processed documents
        docs = (await db.execute(select(ProcessedDocument))).scalars().all()
        print(f"\nTotal processed documents (OCR/text extracted): {len(docs)}")
        for d in docs:
            print(f"\n  Method : {d.processing_method}")
            print(f"  Pages  : {d.page_count}")
            print(f"  Time   : {d.processing_time_seconds:.2f}s")
            print(f"  Text   : {d.extracted_text[:300]}")
        print(f"\n{'='*50}")

asyncio.run(check())
