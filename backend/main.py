from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Backend API")

class MessageResponse(BaseModel):
    message: str
    status: str

@app.get("/api/health", response_model=MessageResponse)
async def health_check():
    return {"message": "FastAPI is running", "status": "ok"}
