from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String(255), nullable=False)
    dxf_filename = Column(String(255), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    dxf_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    entities = relationship(
        "DXFEntity",
        back_populates="upload",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    pdf_parse = relationship(
        "PDFParse",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    comparison_results = relationship(
        "ComparisonResult",
        back_populates="upload",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reports = relationship(
        "Report",
        back_populates="upload",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ocr_results = relationship(
        "OCRResult",
        back_populates="upload",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DXFEntity(Base):
    __tablename__ = "dxf_entities"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    layer = Column(String(100), nullable=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    upload = relationship("Upload", back_populates="entities")


class PDFParse(Base):
    __tablename__ = "pdf_parses"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    page_count = Column(Integer, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    text_blocks = Column(JSON, nullable=False)
    text_block_count = Column(Integer, nullable=False)
    total_text_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    upload = relationship("Upload", back_populates="pdf_parse")


class ComparisonResult(Base):
    __tablename__ = "comparison_results"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)
    accuracy = Column(Float, nullable=False)
    matched_count = Column(Integer, nullable=False)
    missing_count = Column(Integer, nullable=False)
    extra_count = Column(Integer, nullable=False)
    matched = Column(JSON, nullable=False)
    missing = Column(JSON, nullable=False)
    extra = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    upload = relationship("Upload", back_populates="comparison_results")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(500), nullable=True)
    ocr_data = Column(JSON, nullable=False)
    text_block_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    upload = relationship("Upload", back_populates="ocr_results")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    report_filename = Column(String(255), nullable=False)
    report_path = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False)
    accuracy = Column(Float, nullable=False)
    matched_count = Column(Integer, nullable=False)
    missing_count = Column(Integer, nullable=False)
    extra_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    upload = relationship("Upload", back_populates="reports")
