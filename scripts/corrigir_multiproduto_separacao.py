#!/usr/bin/env python3
"""
Script para corrigir registros de Separacao com cod_produto='MULTIPRODUTO'
Substitui cada registro MULTIPRODUTO por múltiplos registros com produtos reais

Data: 2025-09-15
Autor: Sistema

USO:
    python scripts/corrigir_multiproduto_separacao.py

IMPORTANTE:
    - Fazer backup do banco antes de executar
    - Script preserva o separacao_lote_id original
    - Copia todas as informações de agendamento/protocolo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def corrigir_multiproduto():
    """
    Corrige registros MULTIPRODUTO criando Separacoes individuais
    """
    app = create_app()

    with app.app_context():
        try:
            # Buscar todos os registros com MULTIPRODUTO
            multiprodutos = Separacao.query.filter_by(
                cod_produto='MULTIPRODUTO'
            ).all()

            if not multiprodutos:
                logger.info("Nenhum registro MULTIPRODUTO encontrado. Nada a corrigir.")
                return

            logger.info(f"Encontrados {len(multiprodutos)} registros MULTIPRODUTO para corrigir")

            total_corrigidos = 0
            total_criados = 0
            erros = []

            for mp in multiprodutos:
                try:
                    logger.info(f"\nProcessando Separacao ID {mp.id}:")
                    logger.info(f"  - Lote: {mp.separacao_lote_id}")
                    logger.info(f"  - Pedido: {mp.num_pedido}")
                    logger.info(f"  - CNPJ: {mp.cnpj_cpf}")
                    logger.info(f"  - Protocolo: {mp.protocolo}")

                    # Buscar itens na CarteiraPrincipal
                    itens_carteira = CarteiraPrincipal.query.filter_by(
                        cnpj_cpf=mp.cnpj_cpf,
                        num_pedido=mp.num_pedido,
                        cod_uf=mp.cod_uf,
                        ativo=True
                    ).all()

                    if not itens_carteira:
                        logger.warning(f"  ⚠️ Nenhum item encontrado na CarteiraPrincipal para pedido {mp.num_pedido}")

                        # Tentar buscar sem o filtro de ativo
                        itens_carteira = CarteiraPrincipal.query.filter_by(
                            cnpj_cpf=mp.cnpj_cpf,
                            num_pedido=mp.num_pedido,
                            cod_uf=mp.cod_uf
                        ).all()

                        if itens_carteira:
                            logger.info(f"  ℹ️ Encontrados {len(itens_carteira)} itens inativos, usando mesmo assim")
                        else:
                            erros.append(f"Pedido {mp.num_pedido}: Sem itens na CarteiraPrincipal")
                            continue

                    logger.info(f"  ✓ Encontrados {len(itens_carteira)} produtos na CarteiraPrincipal")

                    # Lista para armazenar novos registros
                    novos_registros = []

                    for item in itens_carteira:
                        qtd_carteira = float(item.qtd_saldo_produto_pedido or 0)

                        # Verificar se já existe Separacao para este produto (exceto o MULTIPRODUTO atual)
                        qtd_ja_separada = db.session.query(
                            db.func.coalesce(db.func.sum(Separacao.qtd_saldo), 0)
                        ).filter(
                            Separacao.num_pedido == item.num_pedido,
                            Separacao.cod_produto == item.cod_produto,
                            Separacao.sincronizado_nf == False,
                            Separacao.id != mp.id  # Excluir o registro atual
                        ).scalar()

                        qtd = qtd_carteira - float(qtd_ja_separada)

                        if qtd <= 0:
                            logger.info(f"    - Produto {item.cod_produto}: Sem saldo disponível (qtd_carteira={qtd_carteira}, ja_separada={qtd_ja_separada})")
                            continue

                        preco = float(item.preco_produto_pedido or 0)
                        valor = qtd * preco

                        # Calcular peso e pallet
                        peso_calculado = 0
                        pallet_calculado = 0
                        try:
                            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(item.cod_produto, qtd)
                        except Exception as e:
                            logger.warning(f"    - Erro ao calcular peso/pallet para {item.cod_produto}: {e}")

                        # Criar nova Separacao com os mesmos dados do MULTIPRODUTO
                        nova_separacao = Separacao(
                            separacao_lote_id=mp.separacao_lote_id,  # PRESERVAR o lote original
                            num_pedido=mp.num_pedido,
                            data_pedido=mp.data_pedido,
                            cnpj_cpf=mp.cnpj_cpf,
                            raz_social_red=mp.raz_social_red,
                            nome_cidade=mp.nome_cidade,
                            cod_uf=mp.cod_uf,
                            cod_produto=item.cod_produto,  # Produto real
                            nome_produto=item.nome_produto,  # Nome real
                            qtd_saldo=qtd,
                            valor_saldo=valor,
                            peso=peso_calculado,
                            pallet=pallet_calculado,
                            rota=mp.rota,
                            sub_rota=mp.sub_rota,
                            roteirizacao=mp.roteirizacao,
                            expedicao=mp.expedicao,
                            agendamento=mp.agendamento,
                            agendamento_confirmado=mp.agendamento_confirmado,
                            protocolo=mp.protocolo,
                            pedido_cliente=mp.pedido_cliente,
                            tipo_envio=mp.tipo_envio,
                            status=mp.status,
                            sincronizado_nf=mp.sincronizado_nf,
                            nf_cd=mp.nf_cd,
                            numero_nf=mp.numero_nf,
                            data_sincronizacao=mp.data_sincronizacao,
                            zerado_por_sync=mp.zerado_por_sync,
                            data_zeragem=mp.data_zeragem,
                            data_embarque=mp.data_embarque,
                            cidade_normalizada=mp.cidade_normalizada,
                            uf_normalizada=mp.uf_normalizada,
                            codigo_ibge=mp.codigo_ibge,
                            cotacao_id=mp.cotacao_id,
                            observ_ped_1=f'{mp.observ_ped_1} [Corrigido de MULTIPRODUTO em {datetime.now().strftime("%d/%m/%Y %H:%M")}]'
                        )

                        novos_registros.append(nova_separacao)
                        logger.info(f"    ✓ Preparado produto {item.cod_produto}: qtd={qtd:.2f}, valor={valor:.2f}")

                    if novos_registros:
                        # Adicionar novos registros
                        for novo in novos_registros:
                            db.session.add(novo)

                        # Deletar o registro MULTIPRODUTO
                        db.session.delete(mp)

                        # Commit das mudanças
                        db.session.commit()

                        total_corrigidos += 1
                        total_criados += len(novos_registros)
                        logger.info(f"  ✅ SUCESSO: Criados {len(novos_registros)} registros, MULTIPRODUTO deletado")
                    else:
                        logger.warning(f"  ⚠️ Nenhum produto com saldo para criar. Mantendo MULTIPRODUTO.")
                        erros.append(f"Pedido {mp.num_pedido}: Nenhum produto com saldo disponível")

                except Exception as e:
                    db.session.rollback()
                    logger.error(f"  ❌ ERRO ao processar ID {mp.id}: {str(e)}")
                    erros.append(f"ID {mp.id}: {str(e)}")

            # Resumo final
            print("\n" + "="*70)
            print("RESUMO DA CORREÇÃO")
            print("="*70)
            print(f"Total de MULTIPRODUTO encontrados: {len(multiprodutos)}")
            print(f"Total corrigidos com sucesso: {total_corrigidos}")
            print(f"Total de registros criados: {total_criados}")
            print(f"Total de erros: {len(erros)}")

            if erros:
                print("\nERROS ENCONTRADOS:")
                for erro in erros:
                    print(f"  - {erro}")

            print("\n✅ Script concluído!")

        except Exception as e:
            logger.error(f"Erro geral no script: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("="*70)
    print("SCRIPT DE CORREÇÃO DE MULTIPRODUTO EM SEPARACAO")
    print("="*70)
    print("\nEste script irá:")
    print("1. Buscar todos os registros com cod_produto='MULTIPRODUTO'")
    print("2. Para cada um, buscar os produtos reais na CarteiraPrincipal")
    print("3. Criar Separacoes individuais mantendo o mesmo lote_id")
    print("4. Deletar o registro MULTIPRODUTO após criar os corretos")
    print("\n⚠️  IMPORTANTE: Faça backup do banco antes de continuar!")

    resposta = input("\nDeseja continuar? (s/n): ")

    if resposta.lower() == 's':
        print("\nIniciando correção...\n")
        corrigir_multiproduto()
    else:
        print("\nOperação cancelada.")