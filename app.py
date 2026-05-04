from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os

from database import init_db, listar_proprietarios, adicionar_proprietario, atualizar_coordenadas
from geolocalizacao import filtrar_vizinhos, buscar_coordenadas_incra
from notificador import notificar_vizinhos
from datetime import datetime

from fastapi import FastAPI, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
import sqlite3
import os

app = FastAPI(title="Sistema de Alerta Rural", version="2.0.0")

# Configurar templates (pasta "templates" na raiz)
templates = Jinja2Templates(directory="templates")

# Rota para página principal (interface web)
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = sqlite3.connect("fazendas.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, telefone, telegram_id, nome_fazenda, latitude, longitude FROM proprietarios")
    proprietarios = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "proprietarios": proprietarios,
        "total": len(proprietarios)
    })

# Rota para cadastrar (via formulário)
@app.post("/admin/cadastrar")
async def cadastrar_proprietario(
    nome: str = Form(...),
    telefone: str = Form(...),
    telegram_id: str = Form(...),
    nome_fazenda: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    conn = sqlite3.connect("fazendas.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO proprietarios (nome, telefone, telegram_id, nome_fazenda, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, telefone, telegram_id, nome_fazenda, latitude, longitude))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

# Rota para editar
@app.post("/admin/editar/{proprietario_id}")
async def editar_proprietario(
    proprietario_id: int,
    nome: str = Form(...),
    telefone: str = Form(...),
    telegram_id: str = Form(...),
    nome_fazenda: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    conn = sqlite3.connect("fazendas.db")
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE proprietarios 
        SET nome=?, telefone=?, telegram_id=?, nome_fazenda=?, latitude=?, longitude=?
        WHERE id=?
    ''', (nome, telefone, telegram_id, nome_fazenda, latitude, longitude, proprietario_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

# Rota para excluir
@app.get("/admin/excluir/{proprietario_id}")
async def excluir_proprietario(proprietario_id: int):
    conn = sqlite3.connect("fazendas.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proprietarios WHERE id=?", (proprietario_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

# Rota para enviar alerta via formulário
@app.post("/admin/enviar-alerta")
async def enviar_alerta_form(
    latitude: float = Form(...),
    longitude: float = Form(...),
    invasor: str = Form(...),
    raio_km: float = Form(20)
):
    # Reutiliza sua lógica existente
    from notificador import notificar_vizinhos
    from geolocalizacao import filtrar_vizinhos
    from database import listar_proprietarios
    
    proprietarios = listar_proprietarios()
    vizinhos = filtrar_vizinhos(proprietarios, latitude, longitude, raio_km)
    
    import asyncio
    await notificar_vizinhos(vizinhos, invasor, latitude, longitude)
    
    return RedirectResponse(url="/admin", status_code=303)

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

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
