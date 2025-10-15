from fastapi import FastAPI

from app.core.config import settings
from app.api.v1.endpoints import survey

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(
    survey.router,
    prefix=settings.API_V1_STR,
    tags=["survey"]
)

@app.get("/")
async def root():
    return {"message": "Survey Theme Agent API", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

