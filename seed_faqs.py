from api import engine
from sqlalchemy import text
import time

faqs = [
    {"question": "What are the library timings?", "answer": "The library is open from 9:00 AM to 6:00 PM on weekdays and 10:00 AM to 2:00 PM on Saturdays.", "tags": "library,timings"},
    {"question": "How can I pay fees?", "answer": "Fees can be paid online through the student portal or at the accounts office via cash/DD.", "tags": "fees,payment"},
    {"question": "What are the hostel visiting hours?", "answer": "Visiting hours are 5:00 PM to 8:00 PM on weekdays. Overnight guests are not allowed without prior permission.", "tags": "hostel,visiting"},
    {"question": "How to check bus timings?", "answer": "Bus schedules are posted on the transport noticeboard and on the campus portal under 'Transport'.", "tags": "bus,transport"},
    {"question": "What are the attendance requirements?", "answer": "Students must maintain at least 75% attendance to be eligible for exams unless exempted by the college.", "tags": "attendance,eligibility"},
]

start = time.time()
with engine.begin() as conn:
    params = [{"q": f['question'], "a": f['answer'], "t": f['tags']} for f in faqs]
    conn.execute(text("INSERT INTO faqs(question, answer, tags) VALUES (:q, :a, :t)"), params)

print(f"Seeded {len(faqs)} FAQs in {time.time()-start:.2f}s")
