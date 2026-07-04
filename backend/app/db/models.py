from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.db.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String(255), nullable=False)
    dxf_filename = Column(String(255), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    dxf_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
