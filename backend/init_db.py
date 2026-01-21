from db import engine, Base
from models import Article, Analysis

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Datenbank initialisiert")
