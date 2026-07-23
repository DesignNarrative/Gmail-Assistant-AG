import asyncio
import os
import shutil
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import text, select

async def reset_all():
    print("WARNING: Resetting database and uploads for clean manual testing...")
    
    # 1. Truncate tables
    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE chat_messages, document_chunks, processed_documents, attachments, emails, threads, sync_logs, audit_logs RESTART IDENTITY CASCADE;"))
        await db.commit()
        print("Cleared database tables: chat_messages, document_chunks, processed_documents, attachments, emails, threads, sync_logs, audit_logs.")

        # 2. Ensure Director user exists
        user = (await db.execute(select(User).where(User.email == 'mayurbangera24@gmail.com'))).scalars().first()
        if not user:
            user = User(
                email='mayurbangera24@gmail.com',
                full_name='Mayur Bangera',
                hashed_password=hash_password('mayur@24'),
                role='director',
                is_active=True
            )
            db.add(user)
            await db.commit()
            print("Created fresh Director user: mayurbangera24@gmail.com / mayur@24")
        else:
            user.hashed_password = hash_password('mayur@24')
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.commit()
            print("Reset Director user: mayurbangera24@gmail.com / mayur@24")

    # 3. Clean local uploads directory
    uploads_dir = "./uploads"
    if os.path.exists(uploads_dir):
        for f in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, f)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print("Cleaned ./uploads directory.")

    print("\nRESET COMPLETE! System is ready for a fresh test run.")

if __name__ == "__main__":
    asyncio.run(reset_all())
