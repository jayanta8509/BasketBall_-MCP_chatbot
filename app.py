from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

from client import ask_question

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Basketball League Management API",
    description="AI-powered basketball league management for team registrations, brackets, and waitlists",
    version="1.0.0"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BasketballLeagueRequest(BaseModel):
    question: str
    user_id : str

@app.post("/api/v1/basketball/ask-question")
async def ask_question_endpoint(request: BasketballLeagueRequest):
    """
    Ask a basketball league management question to the AI Assistant

    Examples:
    - "How many teams are registered in 3rd Boys?"
    - "Show me all teams on the waitlist for 4th Girls"
    - "What's the contact info for the coach of 'Eldon 3rd Grade A'?"
    - "Which divisions are currently full?"
    - "Show me the bracket assignments for 5th Grade Boys"
    """
    try:
        logger.info(f"Received question: {request.question}")
        
        if not request.question or request.question.strip() == "":
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Process the question with optional division filter
        answer = await ask_question(question=request.question)
        
        logger.info(f"Successfully processed question")
        return {
            "answer": answer, 
            "status": "success", 
            "code": 200,
            "question": request.question
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Basketball League Management API",
        "version": "1.0.0",
        "description": "AI-powered basketball league management for team registrations, brackets, and waitlists",
        "endpoints": {
            "ask_question": "POST /api/v1/basketball/ask-question with {question: 'your question', division_filter: 'optional'}"
        },
        "example_questions": [
            "How many teams are registered in 3rd Boys?",
            "Show me all teams on the waitlist for 4th Girls",
            "What's the contact info for the coach of 'Eldon 3rd Grade A'?",
            "Which divisions are currently full?",
            "Give me a summary of all registered teams by division",
            "Show me the bracket assignments for 5th Grade Boys",
            "Who is on the manual waitlist and in what position?",
            "What's the total revenue from team registrations?",
            "Find teams registered by coach 'Aaron Kliethermes'",
            "Which divisions still need more teams?"
        ],
        "available_divisions": [
            "3rd Boys", "3rd Girls",
            "4th Boys", "4th Girls",
            "5th Boys", "5th Girls",
            "6th Boys", "6th Girls",
            "7/8 Boys", "7/8 Girls"
        ],
        "data_sources": {
            "registrations": "Team registration data from Form Responses 1",
            "brackets": "Grade-specific bracket assignments (3rd-8th Grade)",
            "waitlists": "Manual and automatic waitlist management",
            "summary": "Team counts, revenue, and division status"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Basketball League Management API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8032,
        reload=True,
        log_level="info"
    )