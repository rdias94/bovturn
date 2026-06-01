"""
BovTurn — Endpoint de Engorda (peso final por frame score)
POST /api/engorda/calcular  → cenário de engorda com peso de abate do frame
GET  /api/engorda/tabela     → tabela frame → @ → peso de abate
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.engorda import EngordaEntrada, calcular, tabela_frame

router = APIRouter()


class EngordaRequest(BaseModel):
    peso_entrada_kg: float = Field(360, gt=0)
    frame_score: float = Field(6, ge=1, le=11)
    sexo: str = "macho"
    rendimento_carcaca: float = 54.0
    gmd_esperado: float = Field(1.0, gt=0)
    preco_compra_arroba: float = 320.0
    preco_venda_arroba: float = 349.7
    diaria_total: float = 6.0
    arroba_abate_alvo: Optional[float] = None
    peso_vaca_adulta: Optional[float] = None
    fator_abate_matriz: Optional[float] = None


@router.post("/calcular")
def calcular_engorda(req: EngordaRequest):
    e = EngordaEntrada(**req.model_dump())
    return {"sucesso": True, "resultado": calcular(e),
            "tabela_frame": tabela_frame(req.sexo, req.rendimento_carcaca)}


@router.get("/tabela")
def tabela(sexo: str = "macho", rendimento_carcaca: float = 54.0):
    return {"tabela_frame": tabela_frame(sexo, rendimento_carcaca)}
