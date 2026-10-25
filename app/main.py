from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="O2O Smart Hyperlocal Campaigner",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def home():
    return {"message": "O2O Campaigner API is running"}