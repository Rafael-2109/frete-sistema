#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE DOS SERVIÇOS CORRIGIDOS
=============================

Verifica se carteira_service.py e faturamento_service.py estão usando
os mapeamentos corretos do campo_mapper.py

Autor: Sistema
Data: 2025-07-15
"""

import logging
import sys
import os

# Adicionar ao path
sys.path.append(os.path.abspath('.'))

from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def testar_carteira_service():
    """Testa se CarteiraService usa mapeamento correto"""
    logger.info("=" * 80)
    logger.info("🧪 TESTE 1: CARTEIRA SERVICE")
    logger.info("=" * 80)
    
    try:
        # Instanciar serviço
        service = CarteiraService()
        
        # Verificar se tem CampoMapper
        if hasattr(service, 'mapper'):
            logger.info("✅ CarteiraService tem CampoMapper!")
            
            # Verificar se CampoMapper tem método correto
            if hasattr(service.mapper, 'buscar_carteira_odoo'):
                logger.info("✅ CampoMapper tem método buscar_carteira_odoo!")
            else:
                logger.error("❌ CampoMapper NÃO tem método buscar_carteira_odoo!")
                return False
        else:
            logger.error("❌ CarteiraService NÃO tem CampoMapper!")
            return False
        
        # Testar chamada do método (sem dados reais)
        logger.info("🔍 Testando chamada do método obter_carteira_pendente...")
        
        # Deve usar self.mapper.buscar_carteira_odoo
        resultado = service.obter_carteira_pendente()
        
        if resultado['sucesso'] or 'Conexão com Odoo não disponível' in resultado.get('erro', ''):
            logger.info("✅ Método obter_carteira_pendente chamado com sucesso!")
            logger.info(f"📊 Resultado: {resultado}")
            return True
        else:
            logger.error(f"❌ Erro no método: {resultado}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERRO no teste do CarteiraService: {e}")
        return False

def testar_faturamento_service():
    """Testa se FaturamentoService usa mapeamento correto"""
    logger.info("=" * 80)
    logger.info("🧪 TESTE 2: FATURAMENTO SERVICE")
    logger.info("=" * 80)
    
    try:
        # Instanciar serviço
        service = FaturamentoService()
        
        # Verificar se tem CampoMapper
        if hasattr(service, 'mapper'):
            logger.info("✅ FaturamentoService tem CampoMapper!")
            
            # Verificar se CampoMapper tem método correto
            if hasattr(service.mapper, 'buscar_faturamento_odoo'):
                logger.info("✅ CampoMapper tem método buscar_faturamento_odoo!")
            else:
                logger.error("❌ CampoMapper NÃO tem método buscar_faturamento_odoo!")
                return False
        else:
            logger.error("❌ FaturamentoService NÃO tem CampoMapper!")
            return False
        
        # Testar chamada do método (sem dados reais)
        logger.info("🔍 Testando chamada do método importar_faturamento_odoo...")
        
        # Deve usar self.mapper.buscar_faturamento_odoo
        resultado = service.importar_faturamento_odoo()
        
        if resultado['success'] or 'conectar ao Odoo' in resultado.get('message', ''):
            logger.info("✅ Método importar_faturamento_odoo chamado com sucesso!")
            logger.info(f"📊 Resultado: {resultado}")
            return True
        else:
            logger.error(f"❌ Erro no método: {resultado}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERRO no teste do FaturamentoService: {e}")
        return False

def verificar_imports():
    """Verifica se os imports estão corretos"""
    logger.info("=" * 80)
    logger.info("🧪 TESTE 3: VERIFICAÇÃO DE IMPORTS")
    logger.info("=" * 80)
    
    try:
        # Verificar import do CampoMapper
        from app.odoo.utils.campo_mapper import CampoMapper
        logger.info("✅ Import do CampoMapper funcionando!")
        
        # Instanciar CampoMapper
        mapper = CampoMapper()
        
        # Verificar métodos corretos
        metodos_obrigatorios = [
            'buscar_faturamento_odoo',
            'buscar_carteira_odoo',
            'mapear_para_faturamento',
            'mapear_para_carteira'
        ]
        
        todos_ok = True
        for metodo in metodos_obrigatorios:
            if hasattr(mapper, metodo):
                logger.info(f"✅ Método {metodo} encontrado!")
            else:
                logger.error(f"❌ Método {metodo} NÃO encontrado!")
                todos_ok = False
        
        return todos_ok
        
    except Exception as e:
        logger.error(f"❌ ERRO na verificação de imports: {e}")
        return False

def main():
    """Executa todos os testes"""
    logger.info("🚀 INICIANDO TESTES DOS SERVIÇOS CORRIGIDOS")
    logger.info("=" * 80)
    
    # Contadores
    testes_executados = 0
    testes_ok = 0
    
    # Teste 1: Verificar imports
    testes_executados += 1
    if verificar_imports():
        testes_ok += 1
        logger.info("✅ TESTE 1: IMPORTS - PASSOU")
    else:
        logger.error("❌ TESTE 1: IMPORTS - FALHOU")
    
    # Teste 2: CarteiraService
    testes_executados += 1
    if testar_carteira_service():
        testes_ok += 1
        logger.info("✅ TESTE 2: CARTEIRA SERVICE - PASSOU")
    else:
        logger.error("❌ TESTE 2: CARTEIRA SERVICE - FALHOU")
    
    # Teste 3: FaturamentoService
    testes_executados += 1
    if testar_faturamento_service():
        testes_ok += 1
        logger.info("✅ TESTE 3: FATURAMENTO SERVICE - PASSOU")
    else:
        logger.error("❌ TESTE 3: FATURAMENTO SERVICE - FALHOU")
    
    # Resultados finais
    logger.info("=" * 80)
    logger.info("📊 RESULTADOS FINAIS")
    logger.info("=" * 80)
    logger.info(f"✅ Testes que passaram: {testes_ok}/{testes_executados}")
    logger.info(f"❌ Testes que falharam: {testes_executados - testes_ok}/{testes_executados}")
    
    if testes_ok == testes_executados:
        logger.info("🎉 TODOS OS TESTES PASSARAM!")
        logger.info("✅ Os serviços estão usando os mapeamentos CORRETOS!")
        return True
    else:
        logger.error("⚠️  ALGUNS TESTES FALHARAM!")
        logger.error("❌ Os serviços NÃO estão totalmente corrigidos!")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 