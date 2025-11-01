from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.api import api_router
from contextlib import asynccontextmanager

from src.util import util_base_de_datos as db_utils
from src.crud import crud_admin
from src.util.util_prompt import PROMPT_CACHE

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Carga al iniciar ---
    print("Cargando prompt (ID: 1) desde la BD al caché...")
    db = next(db_utils.obtener_bd())
    try:
        # 3. Usamos tu lógica: buscar por id_prompt = 1
        prompt_de_la_bd = crud_admin.get_prompt_by_id(db, 1)

        if prompt_de_la_bd:
            # 4. Guardamos el texto en nuestro caché
            PROMPT_CACHE["prompt"] = prompt_de_la_bd.descripcion
            print("¡Prompt principal cargado en caché con éxito!")
        else:
            print("ADVERTENCIA: No se encontró el prompt con ID 1 en la BD.")
    finally:
        db.close()

    yield
    # --- Se ejecuta al apagar ---
    print("Apagando...")
app = FastAPI(
    title="API de Agente Inteligente de Soporte",
    lifespan=lifespan,
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