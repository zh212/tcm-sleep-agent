"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Formula(Base):
    __tablename__ = "formulas"

    id = Column(String(100), primary_key=True)
    name = Column(String(100), nullable=False)
    syndrome = Column(String(200), nullable=False)
    symptoms = Column(Text, nullable=False)
    effects = Column(Text, nullable=False)
    ingredients = Column(Text, nullable=False)
    notes = Column(Text, default="")
    category = Column(String(100), default="")
    source = Column(String(200), default="演示样例")
    example_case = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "syndrome": self.syndrome,
            "symptoms": self.symptoms,
            "effects": self.effects,
            "ingredients": self.ingredients,
            "notes": self.notes or "",
            "category": self.category or "",
            "source": self.source or "",
            "example_case": self.example_case or "",
        }
