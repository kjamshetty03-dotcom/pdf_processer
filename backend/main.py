from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import io
import hashlib
import os

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"

if os.path.exists("test.db"):
    os.remove("test.db")
    print("Old database deleted, recreating with new schema...")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PDFDocument(Base):
    __tablename__ = "pdf_documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    text_preview = Column(String)
    file_hash = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_file_hash(contents):
    return hashlib.md5(contents).hexdigest()

@app.get("/check-db")
async def check_db():
    db = SessionLocal()
    try:
        documents = db.query(PDFDocument).all()
        return {
            "status": "connected",
            "total_documents": len(documents),
            "documents": [{"id": doc.id, "filename": doc.filename} for doc in documents]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    file_hash = get_file_hash(contents)
    
    db = SessionLocal()
    try:
        existing_doc = db.query(PDFDocument).filter(PDFDocument.file_hash == file_hash).first()
        if existing_doc:
            return {
                "status": "error",
                "message": "This PDF file already exists in the database",
                "existing_file": existing_doc.filename
            }
        
        pdf = PdfReader(io.BytesIO(contents))
        extracted_text = "".join(page.extract_text() or "" for page in pdf.pages)
        
        db_document = PDFDocument(
            filename=file.filename, 
            text_preview=extracted_text[:500],
            file_hash=file_hash
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return {
            "status": "success",
            "id": db_document.id,
            "filename": file.filename,
            "text_preview": extracted_text[:500]
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.get("/fetch-pdfs")
async def fetch_pdfs():
    db = SessionLocal()
    try:
        documents = db.query(PDFDocument).all()
        return {
            "status": "success",
            "total_documents": len(documents),
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "text_preview": doc.text_preview
                }
                for doc in documents
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.get("/fetch-pdfs/{doc_id}")
async def fetch_pdf_by_id(doc_id: int):
    db = SessionLocal()
    try:
        document = db.query(PDFDocument).filter(PDFDocument.id == doc_id).first()
        if not document:
            return {"status": "error", "message": "Document not found"}
        return {
            "status": "success",
            "id": document.id,
            "filename": document.filename,
            "text_preview": document.text_preview
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.delete("/delete-pdf/{document_id}")
async def delete_pdf(document_id: int):
    """
    Delete a PDF document from the database by document ID
    """
    db = SessionLocal()
    try:
        # Find the document
        document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Payslip with ID {document_id} not found"
                }
            )
        
        # Delete the document
        db.delete(document)
        db.commit()
        
        print(f"✓ Deleted document: {document.filename} (ID: {document_id})")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Payslip deleted successfully",
                "deleted_filename": document.filename
            }
        )
    
    except Exception as e:
        db.rollback()
        print(f"✗ Error deleting document: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Error deleting payslip: {str(e)}"
            }
        )
    finally:
        db.close()