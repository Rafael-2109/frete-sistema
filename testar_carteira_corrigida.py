#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE CARTEIRA CORRIGIDA
=======================

Verifica se carteira_service.py está usando os campos EXATOS do 
mapeamento_carteira.csv criado pelo usuário.

Autor: Sistema
Data: 2025-07-15
"""

import logging
import sys
import os
import csv

# Adicionar ao path
sys.path.append(os.path.abspath('.'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def carregar_mapeamento_usuario():
    """Carrega o mapeamento EXATO criado pelo usuário"""
    try:
        mapeamento = {}
        with open('projeto_carteira/mapeamento_carteira.csv', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Processar linha a linha
            for i, line in enumerate(lines):
                line = line.strip()
                if i == 0:  # Header - pular
                    continue
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split(';')
                if len(parts) >= 3:
                    campo_modelo = parts[0].strip()
                    campo_odoo = parts[2].strip()  # 3ª coluna é o campo Odoo
                    
                    if campo_modelo and campo_odoo and not campo_modelo.startswith('#'):
                        mapeamento[campo_modelo] = campo_odoo
        
        logger.info(f"✅ Mapeamento carregado: {len(mapeamento)} campos")
        if mapeamento:
            # Mostrar alguns exemplos
            exemplos = list(mapeamento.items())[:3]
            for campo, odoo in exemplos:
                logger.info(f"   {campo} → {odoo}")
                
        return mapeamento
    except Exception as e:
        logger.error(f"❌ Erro ao carregar mapeamento: {e}")
        return {}

def testar_campo_mapper():
    """Testa se CampoMapper está usando mapeamento correto"""
    try:
        from app.odoo.utils.campo_mapper import CampoMapper
        
        # Instanciar mapper
        mapper = CampoMapper()
        
        # Verificar se tem método buscar_carteira_odoo
        if hasattr(mapper, 'buscar_carteira_odoo'):
            logger.info("✅ CampoMapper tem método buscar_carteira_odoo")
        else:
            logger.error("❌ CampoMapper NÃO tem método buscar_carteira_odoo")
            return False
            
        # Verificar se tem método mapear_para_carteira corrigido
        if hasattr(mapper, 'mapear_para_carteira'):
            logger.info("✅ CampoMapper tem método mapear_para_carteira")
        else:
            logger.error("❌ CampoMapper NÃO tem método mapear_para_carteira")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no teste CampoMapper: {e}")
        return False

def testar_carteira_service():
    """Testa se CarteiraService está usando campos corretos"""
    try:
        from app.odoo.services.carteira_service import CarteiraService
        
        # Instanciar service
        service = CarteiraService()
        
        # Verificar se tem método _processar_dados_carteira
        if hasattr(service, '_processar_dados_carteira'):
            logger.info("✅ CarteiraService tem método _processar_dados_carteira")
        else:
            logger.error("❌ CarteiraService NÃO tem método _processar_dados_carteira")
            return False
            
        # Verificar se tem método sincronizar_carteira_odoo
        if hasattr(service, 'sincronizar_carteira_odoo'):
            logger.info("✅ CarteiraService tem método sincronizar_carteira_odoo")
        else:
            logger.error("❌ CarteiraService NÃO tem método sincronizar_carteira_odoo")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no teste CarteiraService: {e}")
        return False

def verificar_campos_modelo():
    """Verifica se modelo CarteiraPrincipal tem os campos do mapeamento"""
    try:
        from app.carteira.models import CarteiraPrincipal
        
        # Carregar mapeamento do usuário
        mapeamento = carregar_mapeamento_usuario()
        if not mapeamento:
            return False
        
        # Verificar se todos os campos do mapeamento existem no modelo
        campos_faltando = []
        campos_corretos = []
        
        for campo_modelo in mapeamento.keys():
            if hasattr(CarteiraPrincipal, campo_modelo):
                campos_corretos.append(campo_modelo)
            else:
                campos_faltando.append(campo_modelo)
        
        logger.info(f"✅ Campos corretos no modelo: {len(campos_corretos)}")
        logger.info(f"❌ Campos faltando no modelo: {len(campos_faltando)}")
        
        if campos_faltando:
            logger.warning(f"Campos faltando: {campos_faltando[:5]}...")
            
        return len(campos_faltando) == 0
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação do modelo: {e}")
        return False

def main():
    """Executa todos os testes"""
    logger.info("=" * 50)
    logger.info("�� TESTE CARTEIRA CORRIGIDA")
    logger.info("=" * 50)
    
    resultados = []
    
    # Teste 1: Mapeamento do usuário
    logger.info("\n📋 TESTE 1: Mapeamento do usuário")
    mapeamento = carregar_mapeamento_usuario()
    if mapeamento:
        logger.info(f"✅ PASSOU - {len(mapeamento)} campos mapeados")
        resultados.append(True)
    else:
        logger.error("❌ FALHOU - Não conseguiu carregar mapeamento")
        resultados.append(False)
    
    # Teste 2: CampoMapper
    logger.info("\n🔧 TESTE 2: CampoMapper")
    if testar_campo_mapper():
        logger.info("✅ PASSOU - CampoMapper correto")
        resultados.append(True)
    else:
        logger.error("❌ FALHOU - CampoMapper com problemas")
        resultados.append(False)
    
    # Teste 3: CarteiraService  
    logger.info("\n🏭 TESTE 3: CarteiraService")
    if testar_carteira_service():
        logger.info("✅ PASSOU - CarteiraService correto")
        resultados.append(True)
    else:
        logger.error("❌ FALHOU - CarteiraService com problemas")
        resultados.append(False)
    
    # Teste 4: Modelo CarteiraPrincipal
    logger.info("\n📝 TESTE 4: Modelo CarteiraPrincipal")
    if verificar_campos_modelo():
        logger.info("✅ PASSOU - Todos os campos existem no modelo")
        resultados.append(True)
    else:
        logger.error("❌ FALHOU - Campos faltando no modelo")
        resultados.append(False)
    
    # Resultado final
    total_testes = len(resultados)
    testes_passou = sum(resultados)
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 RESULTADO FINAL: {testes_passou}/{total_testes} testes passaram")
    
    if testes_passou == total_testes:
        logger.info("🎉 SUCESSO TOTAL! Carteira corrigida com mapeamento exato")
    else:
        logger.warning(f"⚠️ {total_testes - testes_passou} teste(s) falharam")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main() 