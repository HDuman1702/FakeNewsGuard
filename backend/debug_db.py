from db import SessionLocal
from models import Article, Analysis

db = SessionLocal()

print("ARTICLES:", db.query(Article).count())
print("ANALYSES:", db.query(Analysis).count())

db.close()
