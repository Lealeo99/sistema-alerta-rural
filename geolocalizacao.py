import math
import requests
from typing import List, Dict

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula distância em km usando fórmula de Haversine"""
    R = 6371  # Raio da Terra em km
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def buscar_coordenadas_incra(nome_fazenda: str) -> tuple:
    """
    Busca coordenadas no acervo do INCRA
    Nota: Isso é uma simulação. O INCRA não tem API pública,
    mas você pode usar dados do CAR ou GeoPortal da Embrapa
    """
    # SIMULAÇÃO: Em produção, você usaria web scraping ou API paga
    # Por enquanto, retorna None para ser preenchido manualmente
    
    print(f"🔍 Buscando coordenadas para: {nome_fazenda}")
    
    # TODO: Implementar busca real no:
    # - CAR (Cadastro Ambiental Rural): https://www.car.gov.br/
    # - GeoPortal Embrapa: https://geoinfo.cnps.embrapa.br/
    
    return None, None

def filtrar_vizinhos(proprietarios: List[Dict], lat_centro: float, lon_centro: float, raio_km: float = 20) -> List[Dict]:
    """Filtra proprietários dentro do raio"""
    vizinhos = []
    
    for prop in proprietarios:
        if prop['latitude'] is None or prop['longitude'] is None:
            continue
            
        distancia = calcular_distancia(lat_centro, lon_centro, prop['latitude'], prop['longitude'])
        
        if distancia <= raio_km:
            prop['distancia_km'] = round(distancia, 1)
            vizinhos.append(prop)
    
    # Ordena por distância
    vizinhos.sort(key=lambda x: x['distancia_km'])
    return vizinhos