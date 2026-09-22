import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def fix_labels():
    async with AsyncSessionLocal() as db:
        stmt = select(User)
        users = (await db.execute(stmt)).scalars().all()
        for u in users:
            print(f"User {u.email}: current gmail_label = '{u.gmail_label}'")
            if u.gmail_label != "InboxIQ":
                u.gmail_label = "InboxIQ"
                print(f"  -> Fixed {u.email} to 'InboxIQ'")
        await db.commit()
        print("All users now strictly set to 'InboxIQ'.")

if __name__ == "__main__":
    asyncio.run(fix_labels())
