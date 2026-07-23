import asyncio
from app.core.database import AsyncSessionLocal
from app.services.ai.rag_service import generate_rag_answer
from app.models.user import User
from sqlalchemy import select

async def test_rag():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User))).scalars().first()
        
        q1 = "What is the student name and fee amount in the receipt?"
        print(f"\n==========================================")
        print(f"Question 1: {q1}")
        res1 = await generate_rag_answer(q1, db, str(user.id))
        print("------------------------------------------")
        print("AI Answer:")
        print(res1["answer"])
        print("Sources:", [s["filename"] for s in res1["sources"]])
        
        q2 = "Which college did the applicant attend for HSC?"
        print(f"\n==========================================")
        print(f"Question 2: {q2}")
        res2 = await generate_rag_answer(q2, db, str(user.id))
        print("------------------------------------------")
        print("AI Answer:")
        print(res2["answer"])
        print("Sources:", [s["filename"] for s in res2["sources"]])
        print("==========================================\n")

asyncio.run(test_rag())
