from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints import chat

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["survey theme"])

@app.get("/")
async def root():
    return {"message": "Survey Theme Agent API", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
