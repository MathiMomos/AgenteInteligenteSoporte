from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.api import api_router

app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:9002", "https://soporte-pi.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluye todas las rutas de la API bajo el prefijo /api
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Root"])
def root():
    return {"message": "API del Agente Inteligente de Soporte funcionando."}