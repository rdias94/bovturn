import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from app import db
from app.routes import giros
from app.routes import agente_whatsapp
from app.routes import curadoria


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: abre o pool de banco (no-op se DATABASE_URL ausente)
    await db.conectar()
    yield
    # Shutdown: fecha o pool
    await db.desconectar()


app = FastAPI(title="BovTurn Intelligence API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(giros.router, prefix="/api/giros", tags=["Giros"])
app.include_router(agente_whatsapp.router, prefix="/api/agente", tags=["Agente"])
app.include_router(curadoria.router, prefix="/api/curadoria", tags=["Curadoria"])


@app.get("/")
def raiz():
    return {"status": "BovTurn Intelligence online", "versao": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok", "banco": "conectado" if db.tem_banco() else "mock"}
