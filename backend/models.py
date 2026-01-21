from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from db import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, index=True, nullable=False)
    title = Column(String)
    text = Column(Text)
    word_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"))

    label = Column(String)
    confidence = Column(Float)
    category = Column(String)
    reasoning_summary = Column(Text)
    analysis_text = Column(Text)          # Das ist wichtig fürs Frontend
    red_flags = Column(Text)              # JSON als String

    created_at = Column(DateTime(timezone=True), server_default=func.now())
