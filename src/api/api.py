from fastapi import APIRouter
from src.api.routes import auth, chat, analyst, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chatbot"])
api_router.include_router(analyst.router, prefix="/analista", tags=["Analista"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])