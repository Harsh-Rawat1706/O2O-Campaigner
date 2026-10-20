
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_database_connection

app = FastAPI(
    title="O2O Smart Hyperlocal Campaigner",
    version="0.1.0",
)


@app.get("/")
def home():
    return {"message": "O2O Campaigner API is running"}


@app.get("/health")
def health_check():
    try:
        check_database_connection()
        return {
            "status": "healthy",
            "database": "connected",
        }
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
            },
        )
