from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
from contextlib import asynccontextmanager

from .agent import TravelAgent
from .state import SQLiteStateStore
from .provider import LLMProvider
from .config import settings
from .logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

store = SQLiteStateStore()
provider = LLMProvider()
agent = TravelAgent(provider=provider, store=store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.init_db()
    logger.info("startup_complete")
    yield
    logger.info("shutdown")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
static_dir = os.path.join(project_root, "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"


class ChatResponse(BaseModel):
    response: str


@app.get("/")
async def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Static index.html not found. Please create it."}


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and orchestrators."""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        reply = await agent.run_turn(request.session_id, request.message)
        return ChatResponse(response=reply)
    except Exception as e:
        logger.error(
            "turn_processing_error", error=str(e), session_id=request.session_id
        )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
