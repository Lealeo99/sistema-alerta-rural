from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import init_db, listar_proprietarios, adicionar_proprietario, atualizar_coordenadas
from geolocalizacao import filtrar_vizinhos
from notificador import notificar_vizinhos
import asyncio
import sqlite3
import os

app = FastAPI(title="Sistema de Alerta Rural", version="2.0.0")

# Configurar templates (pasta "templates" na raiz)
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/")
def root():
    return {"mensagem": "Sistema de Alerta Rural Online", "status": "ativo"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/proprietarios")
def listar():
    return listar_proprietarios()

@app.post("/proprietarios")
def cadastrar_json(
    nome: str,
    telegram_id: str,
    nome_fazenda: str,
    telefone: str = None,
    latitude: float = None,
    longitude: float = None
):
    from database import adicionar_proprietario
    id_prop = adicionar_proprietario(nome, telegram_id, nome_fazenda, telefone, latitude, longitude)
    return {"id": id_prop, "mensagem": "Proprietário cadastrado com sucesso"}

@app.post("/coordenadas")
def atualizar_coords(proprietario_id: int, latitude: float, longitude: float):
    atualizar_coordenadas(proprietario_id, latitude, longitude)
    return {"mensagem": "Coordenadas atualizadas"}

@app.post("/alerta")
async def alerta_json(latitude: float, longitude: float, invasor: str = "pessoa desconhecida", raio_km: float = 20):
    proprietarios = listar_proprietarios()
    vizinhos = filtrar_vizinhos(proprietarios, latitude, longitude, raio_km)
    
    if not vizinhos:
        return {"mensagem": "Nenhum vizinho encontrado no raio", "total_vizinhos": 0}
    
    resultados = await notificar_vizinhos(vizinhos, invasor, latitude, longitude)
    return {
        "mensagem": f"Alertas enviados para {len(vizinhos)} vizinhos",
        "total_vizinhos": len(vizinhos),
        "detalhes": resultados
    }

# ========== ROTAS ADMIN (COM CORREÇÕES) ==========

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Página administrativa com interface web"""
    try:
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
    except Exception as e:
        print(f"Erro no admin: {e}")
        return HTMLResponse(content=f"Erro ao carregar página: {e}", status_code=500)

@app.post("/admin/cadastrar")
async def cadastrar_proprietario_form(
    nome: str = Form(...),
    telefone: str = Form(...),
    telegram_id: str = Form(...),
    nome_fazenda: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    """Cadastra proprietário via formulário web"""
    try:
        conn = sqlite3.connect("fazendas.db")
        cursor = conn.cursor()
        
        # Verificar duplicatas
        cursor.execute('''
            SELECT id FROM proprietarios 
            WHERE telefone = ? OR telegram_id = ? OR (latitude = ? AND longitude = ?)
        ''', (telefone, telegram_id, latitude, longitude))
        
        existe = cursor.fetchone()
        if existe:
            conn.close()
            return HTMLResponse(content='''
                <script>
                    alert('❌ Cadastro duplicado! Telefone, Telegram ID ou coordenadas já existem.');
                    window.location.href = '/admin';
                </script>
            ''', status_code=200)
        
        cursor.execute('''
            INSERT INTO proprietarios (nome, telefone, telegram_id, nome_fazenda, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, telefone, telegram_id, nome_fazenda, latitude, longitude))
        conn.commit()
        conn.close()
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        print(f"Erro ao cadastrar: {e}")
        return HTMLResponse(content=f"Erro ao cadastrar: {e}", status_code=500)

@app.post("/admin/editar/{proprietario_id}")
async def editar_proprietario_form(
    proprietario_id: int,
    nome: str = Form(...),
    telefone: str = Form(...),
    telegram_id: str = Form(...),
    nome_fazenda: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    """Edita proprietário via formulário web"""
    try:
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
    except Exception as e:
        return HTMLResponse(content=f"Erro ao editar: {e}", status_code=500)

@app.get("/admin/excluir/{proprietario_id}")
async def excluir_proprietario_form(proprietario_id: int):
    """Exclui proprietário via formulário web"""
    try:
        conn = sqlite3.connect("fazendas.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proprietarios WHERE id=?", (proprietario_id,))
        conn.commit()
        conn.close()
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        return HTMLResponse(content=f"Erro ao excluir: {e}", status_code=500)

@app.post("/admin/enviar-alerta")
async def enviar_alerta_form(
    latitude: float = Form(...),
    longitude: float = Form(...),
    invasor: str = Form(...),
    raio_km: float = Form(20)
):
    """Envia alerta via formulário web"""
    try:
        proprietarios = listar_proprietarios()
        vizinhos = filtrar_vizinhos(proprietarios, latitude, longitude, raio_km)
        
        if vizinhos:
            await notificar_vizinhos(vizinhos, invasor, latitude, longitude)
        
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        print(f"Erro ao enviar alerta: {e}")
        return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)