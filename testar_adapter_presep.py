#!/usr/bin/env python3
"""
Script para testar o adapter PreSeparacaoItem → Separacao
Data: 2025-01-29

Testa se o adapter funciona corretamente para substituir PreSeparacaoItem
por Separacao com status='PREVISAO'
"""

import os
import sys
from datetime import datetime, date
import logging

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.carteira.models_adapter_presep import PreSeparacaoItem, PreSeparacaoItemAdapter
from app.separacao.models import Separacao
from app.utils.lote_utils import gerar_lote_id

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def testar_adapter():
    """
    Testa as funcionalidades do adapter
    """
    
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("=" * 60)
            logger.info("TESTANDO ADAPTER PreSeparacaoItem → Separacao")
            logger.info("=" * 60)
            
            # 1. Teste de criação
            logger.info("\n📝 TESTE 1: Criar nova pré-separação via adapter")
            
            lote_id = gerar_lote_id()
            logger.info(f"   Lote ID gerado: {lote_id}")
            
            # Criar usando o adapter
            pre_sep = PreSeparacaoItem()
            pre_sep.separacao_lote_id = lote_id
            pre_sep.num_pedido = "TEST-001"
            pre_sep.cod_produto = "PROD-001"
            pre_sep.nome_produto = "Produto Teste"
            pre_sep.cnpj_cliente = "12345678901234"
            pre_sep.qtd_original_carteira = 100
            pre_sep.qtd_selecionada_usuario = 50
            pre_sep.qtd_restante_calculada = 50
            pre_sep.valor_original_item = 500.00
            pre_sep.peso_original_item = 25.5
            pre_sep.data_expedicao_editada = date(2025, 2, 1)
            pre_sep.data_agendamento_editada = date(2025, 2, 2)
            pre_sep.protocolo_editado = "PROT-001"
            pre_sep.observacoes_usuario = "Teste de adapter"
            pre_sep.recomposto = False  # Não recomposto = status PREVISAO
            pre_sep.tipo_envio = "parcial"
            pre_sep.criado_por = "teste_adapter"
            
            # Salvar via adapter
            pre_sep.save()
            pre_sep_id = pre_sep.id
            
            logger.info(f"   ✅ Pré-separação criada com ID: {pre_sep_id}")
            
            # Verificar que foi salva como Separacao
            separacao = Separacao.query.get(pre_sep_id)
            assert separacao is not None, "Separacao não foi criada"
            assert separacao.status == 'PREVISAO', f"Status deveria ser PREVISAO, mas é {separacao.status}"
            assert separacao.num_pedido == "TEST-001", "num_pedido incorreto"
            assert separacao.qtd_saldo == 50, "qtd_saldo incorreto"
            
            logger.info("   ✅ Verificação: Separacao criada corretamente com status='PREVISAO'")
            
            # 2. Teste de busca
            logger.info("\n🔍 TESTE 2: Buscar pré-separações via adapter")
            
            # Buscar usando query adapter
            pre_seps = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            assert len(pre_seps) == 1, f"Deveria encontrar 1 item, encontrou {len(pre_seps)}"
            
            item = pre_seps[0]
            assert item.num_pedido == "TEST-001", "num_pedido incorreto na busca"
            assert item.qtd_selecionada_usuario == 50, "qtd_selecionada_usuario incorreto"
            assert item.status == 'CRIADO', f"Status deveria ser CRIADO, mas é {item.status}"
            
            logger.info(f"   ✅ Encontrado 1 item com status: {item.status}")
            
            # 3. Teste de atualização
            logger.info("\n✏️ TESTE 3: Atualizar pré-separação via adapter")
            
            item.qtd_selecionada_usuario = 75
            item.observacoes_usuario = "Quantidade atualizada"
            item.save()
            
            # Verificar atualização
            separacao_atualizada = Separacao.query.get(pre_sep_id)
            assert separacao_atualizada.qtd_saldo == 75, "qtd_saldo não foi atualizada"
            assert separacao_atualizada.observ_ped_1 == "Quantidade atualizada", "observações não foram atualizadas"
            
            logger.info("   ✅ Quantidade atualizada de 50 para 75")
            
            # 4. Teste de conversão para separação definitiva
            logger.info("\n🔄 TESTE 4: Converter para separação definitiva")
            
            item.recomposto = True  # Marcar como recomposto = mudar status
            item.save()
            
            # Verificar mudança de status
            separacao_convertida = Separacao.query.get(pre_sep_id)
            assert separacao_convertida.status == 'ABERTO', f"Status deveria ser ABERTO, mas é {separacao_convertida.status}"
            
            logger.info(f"   ✅ Status mudou de PREVISAO para {separacao_convertida.status}")
            
            # 5. Teste de busca por status
            logger.info("\n🔍 TESTE 5: Buscar por diferentes status")
            
            # Criar outra pré-separação
            pre_sep2 = PreSeparacaoItem()
            pre_sep2.separacao_lote_id = lote_id
            pre_sep2.num_pedido = "TEST-002"
            pre_sep2.cod_produto = "PROD-002"
            pre_sep2.nome_produto = "Produto Teste 2"
            pre_sep2.cnpj_cliente = "12345678901234"
            pre_sep2.qtd_selecionada_usuario = 30
            pre_sep2.data_expedicao_editada = date(2025, 2, 1)
            pre_sep2.recomposto = False  # Não recomposto
            pre_sep2.save()
            
            # Buscar não recompostas (status=PREVISAO)
            nao_recompostas = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote_id,
                recomposto=False
            ).all()
            
            assert len(nao_recompostas) == 1, f"Deveria encontrar 1 não recomposta, encontrou {len(nao_recompostas)}"
            assert nao_recompostas[0].num_pedido == "TEST-002", "Encontrou item errado"
            
            logger.info(f"   ✅ Encontrada 1 pré-separação não recomposta")
            
            # Buscar recompostas (status!=PREVISAO)
            recompostas = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote_id,
                recomposto=True
            ).all()
            
            assert len(recompostas) == 1, f"Deveria encontrar 1 recomposta, encontrou {len(recompostas)}"
            assert recompostas[0].num_pedido == "TEST-001", "Encontrou item errado"
            
            logger.info(f"   ✅ Encontrada 1 pré-separação recomposta")
            
            # 6. Teste de to_dict
            logger.info("\n📋 TESTE 6: Conversão para dicionário")
            
            dict_data = nao_recompostas[0].to_dict()
            assert dict_data['num_pedido'] == "TEST-002", "to_dict retornou dados incorretos"
            assert dict_data['qtd_selecionada_usuario'] == 30, "to_dict retornou quantidade incorreta"
            assert dict_data['status'] == 'CRIADO', "to_dict retornou status incorreto"
            
            logger.info("   ✅ to_dict() funcionando corretamente")
            
            # 7. Limpeza - remover dados de teste
            logger.info("\n🧹 TESTE 7: Limpeza de dados de teste")
            
            # Deletar todas as separações de teste
            Separacao.query.filter(
                Separacao.separacao_lote_id == lote_id
            ).delete()
            
            db.session.commit()
            
            # Verificar que foram deletadas
            restantes = Separacao.query.filter(
                Separacao.separacao_lote_id == lote_id
            ).count()
            
            assert restantes == 0, f"Ainda existem {restantes} registros de teste"
            
            logger.info("   ✅ Dados de teste removidos com sucesso")
            
            # Resumo final
            logger.info("\n" + "=" * 60)
            logger.info("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
            logger.info("=" * 60)
            logger.info("\n📊 RESUMO:")
            logger.info("   ✅ Criar pré-separação via adapter")
            logger.info("   ✅ Buscar pré-separações")
            logger.info("   ✅ Atualizar dados")
            logger.info("   ✅ Converter para separação definitiva")
            logger.info("   ✅ Filtrar por status")
            logger.info("   ✅ Converter para dicionário")
            logger.info("   ✅ Limpar dados de teste")
            logger.info("\n🎯 O adapter está funcionando corretamente!")
            logger.info("   Pode ser usado para substituir PreSeparacaoItem gradualmente.")
            
            return True
            
        except AssertionError as e:
            logger.error(f"❌ Teste falhou: {e}")
            db.session.rollback()
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro durante teste: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            db.session.close()


if __name__ == "__main__":
    sucesso = testar_adapter()
    sys.exit(0 if sucesso else 1)