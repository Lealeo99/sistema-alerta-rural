from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os

from database import init_db, listar_proprietarios, adicionar_proprietario, atualizar_coordenadas
from geolocalizacao import filtrar_vizinhos, buscar_coordenadas_incra
from notificador import notificar_vizinhos

app = FastAPI(title="Sistema de Alerta Rural", version="1.0.0")

# Inicializa banco de dados na startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Modelos de dados
class AlertaModel(BaseModel):
    latitude: float
    longitude: float
    invasor: str = "pessoa desconhecida"
    raio_km: float = 20

class ProprietarioModel(BaseModel):
    nome: str
    telegram_id: str
    nome_fazenda: str
    telefone: Optional[str] = None

class CoordenadasModel(BaseModel):
    proprietario_id: int
    latitude: float
    longitude: float

# Rotas da API
@app.get("/")
def root():
    return {"mensagem": "Sistema de Alerta Rural Online", "status": "ativo"}

@app.get("/proprietarios")
def listar():
    """Lista todos proprietários cadastrados"""
    return listar_proprietarios()

@app.post("/proprietarios")
def cadastrar(prop: ProprietarioModel):
    """Cadastra novo proprietário"""
    # Tenta buscar coordenadas automaticamente
    lat, lon = buscar_coordenadas_incra(prop.nome_fazenda)
    
    id_prop = adicionar_proprietario(
        nome=prop.nome,
        telegram_id=prop.telegram_id,
        nome_fazenda=prop.nome_fazenda,
        telefone=prop.telefone,
        lat=lat,
        lon=lon
    )
    
    return {
        "id": id_prop,
        "mensagem": "Proprietário cadastrado com sucesso",
        "coordenadas_encontradas": lat is not None
    }

@app.post("/coordenadas")
def atualizar_coordenadas_manual(coords: CoordenadasModel):
    """Atualiza coordenadas manualmente de um proprietário"""
    atualizar_coordenadas(coords.proprietario_id, coords.latitude, coords.longitude)
    return {"mensagem": "Coordenadas atualizadas"}

@app.post("/alerta")
async def disparar_alerta(alerta: AlertaModel):
    """Dispara alerta para vizinhos"""
    # Busca todos proprietários
    proprietarios = listar_proprietarios()
    
    if not proprietarios:
        raise HTTPException(status_code=404, detail="Nenhum proprietário cadastrado")
    
    # Filtra vizinhos no raio
    vizinhos = filtrar_vizinhos(
        proprietarios,
        alerta.latitude,
        alerta.longitude,
        alerta.raio_km
    )
    
    if not vizinhos:
        return {
            "mensagem": "Nenhum vizinho encontrado no raio",
            "total_vizinhos": 0
        }
    
    # Envia notificações
    resultados = await notificar_vizinhos(vizinhos, alerta.invasor, alerta.latitude, alerta.longitude)
    
    return {
        "mensagem": f"Alertas enviados para {len(vizinhos)} vizinhos",
        "total_vizinhos": len(vizinhos),
        "detalhes": resultados
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)