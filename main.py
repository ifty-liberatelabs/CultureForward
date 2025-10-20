from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import logger
from app.api.v1.endpoints import chat, survey
from app.db.init_db import check_and_create_db, init_db
from app.db.db_manager import DatabaseManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DB_SAVE:
        logger.info("Initializing database")
        check_and_create_db()
        init_db()
        
        db_manager = DatabaseManager(settings.DATABASE_URL)
        await db_manager.initialize()
        logger.info("Database initialized successfully")
        
        try:
            yield {"db_manager": db_manager}
        finally:
            await db_manager.cleanup()
            logger.info("Database connection closed")
    else:
        yield {}


app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.VERSION,
    lifespan=lifespan
)
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Survey Theme"])
app.include_router(survey.router, prefix=f"{settings.API_V1_STR}/survey", tags=["Conversational Survey"])


@app.get("/")
async def root():
    return {"message": "Survey Theme Agent API", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
