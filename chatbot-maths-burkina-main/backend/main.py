from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from config import config
from curriculum_data import get_classes, get_class_name, get_chapters
from rag_system import RAGSystem
from document_processor import DocumentProcessor

app = FastAPI(title="Chatbot Maths Burkina Faso API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem()
rag_system.initialize_vector_store()

# Request/Response models
class QuestionRequest(BaseModel):
    question: str
    class_level: str
    chapter: str

class ExerciseRequest(BaseModel):
    class_level: str
    chapter: str

class SimplifyRequest(BaseModel):
    answer: str
    class_level: str
    question: str = ""

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    from_rag: bool
    internet_search: Optional[bool] = False
    error: Optional[str] = None

class ExerciseResponse(BaseModel):
    exercise: str
    chapter: str
    class_level: str
    error: Optional[str] = None

@app.get("/")
def read_root():
    return {
        "message": "Chatbot Maths Burkina Faso API",
        "version": "1.0",
        "status": "running"
    }

@app.get("/api/classes")
def get_all_classes():
    """Get list of all available classes"""
    classes = []
    for class_code in get_classes():
        classes.append({
            "code": class_code,
            "name": get_class_name(class_code)
        })
    return {"classes": classes}

@app.get("/api/classes/{class_code}/chapters")
def get_class_chapters(class_code: str):
    """Get chapters for a specific class"""
    if class_code not in get_classes():
        raise HTTPException(status_code=404, detail="Class not found")
    
    chapters = get_chapters(class_code)
    return {
        "class_code": class_code,
        "class_name": get_class_name(class_code),
        "chapters": chapters
    }

@app.post("/api/chat", response_model=ChatResponse)
def ask_question(request: QuestionRequest):
    """Ask a question to the chatbot"""
    try:
        if request.class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        
        if request.chapter not in get_chapters(request.class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")
        
        response = rag_system.generate_response(
            request.question,
            request.class_level,
            request.chapter
        )
        
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/exercise", response_model=ExerciseResponse)
def generate_exercise(request: ExerciseRequest):
    """Generate a practice exercise"""
    try:
        if request.class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        
        if request.chapter not in get_chapters(request.class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")
        
        response = rag_system.generate_exercise(
            request.class_level,
            request.chapter
        )
        
        return ExerciseResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simplify")
def simplify_answer(request: SimplifyRequest):
    """Simplify an answer for better understanding"""
    try:
        simplified = rag_system.simplify_answer(
            request.question,
            request.answer,
            request.class_level
        )
        
        return {
            "simplified_answer": simplified,
            "original_answer": request.answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    class_level: str = None,
    chapter: str = None
):
    """Upload a document to the knowledge base"""
    try:
        # Create data directory if it doesn't exist
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(config.DATA_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the document
        processor = DocumentProcessor(config.DATA_DIR)
        
        if file.filename.endswith('.pdf'):
            doc = processor.process_pdf(file_path, {"class": class_level, "chapter": chapter})
        elif file.filename.endswith('.docx'):
            doc = processor.process_docx(file_path, {"class": class_level, "chapter": chapter})
        elif file.filename.endswith('.txt'):
            doc = processor.process_txt(file_path, {"class": class_level, "chapter": chapter})
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        if doc:
            rag_system.add_documents([doc], doc["metadata"])
            return {
                "message": "Document uploaded and processed successfully",
                "filename": file.filename,
                "metadata": doc["metadata"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process document")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/initialize-sample")
def initialize_sample_documents():
    """Initialize the knowledge base with sample documents"""
    try:
        processor = DocumentProcessor(config.DATA_DIR)
        sample_docs = processor.create_sample_documents()
        
        rag_system.add_documents(sample_docs)
        
        return {
            "message": f"Initialized {len(sample_docs)} sample documents",
            "documents_count": len(sample_docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_system": "initialized" if rag_system.index else "not initialized",
        "model": config.HUGGINGFACE_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)