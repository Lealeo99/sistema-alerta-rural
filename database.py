import sqlite3
from datetime import datetime

DB_NAME = "fazendas.db"

def init_db():
    """Cria tabela se não existir"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proprietarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            telegram_id TEXT UNIQUE NOT NULL,
            nome_fazenda TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado")

def adicionar_proprietario(nome, telegram_id, nome_fazenda, telefone=None, lat=None, lon=None):
    """Adiciona novo proprietário"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO proprietarios (nome, telefone, telegram_id, nome_fazenda, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, telefone, telegram_id, nome_fazenda, lat, lon))
    
    conn.commit()
    conn.close()
    return cursor.lastrowid

def listar_proprietarios():
    """Lista todos proprietários ativos"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, nome, telefone, telegram_id, nome_fazenda, latitude, longitude FROM proprietarios WHERE ativo=1')
    dados = cursor.fetchall()
    
    conn.close()
    
    return [
        {
            'id': row[0],
            'nome': row[1],
            'telefone': row[2],
            'telegram_id': row[3],
            'nome_fazenda': row[4],
            'latitude': row[5],
            'longitude': row[6]
        }
        for row in dados
    ]

def atualizar_coordenadas(proprietario_id, lat, lon):
    """Atualiza coordenadas manualmente"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE proprietarios SET latitude=?, longitude=? WHERE id=?', (lat, lon, proprietario_id))
    conn.commit()
    conn.close()