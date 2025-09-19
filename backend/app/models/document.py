from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from ..database import Base

class BusinessDocument(Base):
    __tablename__ = "business_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, nullable=False)
    document_type = Column(String, nullable=False)  # contract, invoice, receipt, etc.
    file_path = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
