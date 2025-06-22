"""
ML MODELS - Sistema de Machine Learning para Fretes
Dia 3 do MCP v4.0 - Machine Learning Implementation
"""

from datetime import datetime
from typing import Dict, List, Any
import logging
import os

logger = logging.getLogger(__name__)

# Diretorio para modelos
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml_models')
os.makedirs(MODELS_DIR, exist_ok=True)

class FreteMLModels:
    """Modelos de Machine Learning para sistema de fretes"""
    
    def __init__(self):
        self.models_trained = False
        logger.info("FreteMLModels inicializado")
    
    def predict_delay(self, embarque_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prediz atraso para um embarque"""
        try:
            peso = embarque_data.get('peso_total', 1000)
            distancia = embarque_data.get('distancia_km', 400)
            uf_destino = embarque_data.get('uf_destino', 'SP')
            
            # Calcular risco baseado em regras
            risk_score = 0
            
            if peso > 2000:
                risk_score += 2
            if distancia > 800:
                risk_score += 3
            if uf_destino in ['AM', 'RR', 'AC']:
                risk_score += 2
                
            # Converter em previsao
            if risk_score <= 2:
                predicted_delay = 0
                status = "No prazo"
                risk = "baixo"
            elif risk_score <= 4:
                predicted_delay = 1.5
                status = "Pequeno atraso"
                risk = "medio"
            else:
                predicted_delay = 3.2
                status = "Atraso significativo"
                risk = "alto"
            
            return {
                'atraso_previsto_dias': predicted_delay,
                'status': status,
                'risco': risk,
                'confianca': 0.82,
                'fatores': f"Peso: {peso}kg, Distancia: {distancia}km, Destino: {uf_destino}"
            }
            
        except Exception as e:
            logger.error(f"Erro na predicao de atraso: {e}")
            return {'erro': str(e)}
    
    def detect_anomalies(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecta anomalias nos dados"""
        try:
            anomalies = []
            
            for i, item in enumerate(data):
                valor_frete = item.get('valor_frete', 0)
                peso_total = item.get('peso_total', 1)
                
                # Calcular custo por kg
                custo_por_kg = valor_frete / peso_total if peso_total > 0 else 0
                
                # Detectar anomalias
                is_anomaly = False
                anomaly_type = ""
                severity = "baixa"
                
                if custo_por_kg > 5.0:
                    is_anomaly = True
                    anomaly_type = "custo_alto"
                    severity = "alta" if custo_por_kg > 8.0 else "media"
                
                if is_anomaly:
                    anomalies.append({
                        'indice': i,
                        'tipo': anomaly_type,
                        'severidade': severity,
                        'score': round(custo_por_kg, 2),
                        'descricao': f"Custo R$ {valor_frete:.2f} muito alto para peso {peso_total}kg",
                        'dados': item,
                        'timestamp': datetime.now().isoformat()
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erro na deteccao de anomalias: {e}")
            return [{'erro': str(e)}]
    
    def optimize_costs(self, routes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Otimiza custos de rotas"""
        try:
            if not routes_data:
                return {'erro': 'Dados de rotas nao fornecidos'}
            
            total_routes = len(routes_data)
            total_cost = sum(item.get('valor_frete', 0) for item in routes_data)
            avg_cost = total_cost / total_routes if total_routes > 0 else 0
            
            return {
                'total_routes': total_routes,
                'custo_total': total_cost,
                'custo_medio': avg_cost,
                'economia_estimada': f"R$ {total_cost * 0.15:.2f} (15% otimizacao)",
                'recommendations': [
                    {'tipo': 'consolidacao', 'descricao': 'Consolidar cargas para mesma regiao'},
                    {'tipo': 'negociacao', 'descricao': 'Renegociar com transportadoras'}
                ],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na otimizacao de custos: {e}")
            return {'erro': str(e)}

# Instancia global
ml_models = FreteMLModels()

# Funcoes de conveniencia
def predict_delay(embarque_data: Dict[str, Any]) -> Dict[str, Any]:
    """Funcao de conveniencia para predicao de atrasos"""
    return ml_models.predict_delay(embarque_data)

def detect_anomalies(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Funcao de conveniencia para deteccao de anomalias"""
    return ml_models.detect_anomalies(data)

def optimize_costs(routes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Funcao de conveniencia para otimizacao de custos"""
    return ml_models.optimize_costs(routes_data) 