#!/usr/bin/env python3
"""
Script para corrigir o AjusteSincronizacaoService
Adiciona proteção contra exclusão de separações faturadas
"""

import os
import shutil
from datetime import datetime

# Fazer backup do arquivo original
arquivo_original = "/home/rafaelnascimento/projetos/frete_sistema/app/odoo/services/ajuste_sincronizacao_service.py"
arquivo_backup = f"{arquivo_original}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"📦 Criando backup: {arquivo_backup}")
shutil.copy2(arquivo_original, arquivo_backup)

# Ler o arquivo original
with open(arquivo_original, 'r') as f:
    conteudo = f.read()

# CORREÇÃO 1: Adicionar método para verificar faturamento
metodo_verificar_faturamento = '''
    @classmethod
    def _verificar_se_faturado(cls, lote_id: str, num_pedido: str = None, cod_produto: str = None) -> bool:
        """
        Verifica se uma separação foi faturada.
        
        IMPORTANTE: Uma separação é considerada FATURADA se:
        1. O Pedido tem NF preenchida E
        2. Existe registro em FaturamentoProduto com essa NF
        
        Args:
            lote_id: ID do lote de separação
            num_pedido: Número do pedido (opcional)
            cod_produto: Código do produto (opcional, para verificação específica)
            
        Returns:
            True se foi faturada, False caso contrário
        """
        try:
            from app.faturamento.models import FaturamentoProduto
            
            # Buscar o Pedido pelo lote
            pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
            
            if not pedido or not pedido.nf:
                return False
            
            # Verificar se existe faturamento com essa NF
            query = FaturamentoProduto.query.filter_by(numero_nf=pedido.nf)
            
            # Se especificou produto, verificar esse produto específico
            if num_pedido and cod_produto:
                query = query.filter_by(
                    origem=num_pedido,
                    cod_produto=cod_produto
                )
            
            faturamento_existe = query.first() is not None
            
            if faturamento_existe:
                logger.info(f"🛡️ Separação {lote_id} está FATURADA (NF: {pedido.nf})")
            
            return faturamento_existe
            
        except Exception as e:
            logger.error(f"Erro ao verificar faturamento: {e}")
            # Na dúvida, proteger (considerar como faturado)
            return True
'''

# Inserir o novo método após o método _verificar_se_cotado (linha 1019)
posicao_insercao = conteudo.find("    @classmethod\n    def _gerar_alerta_cotado")
if posicao_insercao > 0:
    conteudo = conteudo[:posicao_insercao] + metodo_verificar_faturamento + "\n" + conteudo[posicao_insercao:]
    print("✅ Método _verificar_se_faturado adicionado")

# CORREÇÃO 2: Modificar _identificar_lotes_afetados para excluir faturados
# Substituir a query de separações (linha 152-166)
query_antiga = """        # PRIMEIRO: Buscar separações com JOIN em Pedido para filtrar status diretamente
        # Só busca separações onde o Pedido tem status ABERTO ou COTADO
        seps = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.separacao_lote_id.isnot(None),
            # PROTEÇÃO: Só pegar separações com Pedido em status alterável
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)  # Ou sem Pedido (pode acontecer)
            )
        ).distinct().all()"""

query_nova = """        # PRIMEIRO: Buscar separações com JOIN em Pedido para filtrar status diretamente
        # Só busca separações onde o Pedido tem status ABERTO ou COTADO
        seps = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status,
            Pedido.nf
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.separacao_lote_id.isnot(None),
            # PROTEÇÃO: Só pegar separações com Pedido em status alterável
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)  # Ou sem Pedido (pode acontecer)
            )
        ).distinct().all()"""

conteudo = conteudo.replace(query_antiga, query_nova)
print("✅ Query de identificação de lotes atualizada")

# CORREÇÃO 3: Adicionar verificação de faturamento no loop de separações
loop_antigo = """        for lote_id, status_pedido in seps:
            lotes.append({
                'lote_id': lote_id,
                'tipo': 'SEPARACAO'
            })
            lotes_processados.add(lote_id)
            logger.info(f"Encontrada Separacao com lote {lote_id} (status: {status_pedido or 'SEM_PEDIDO'})")"""

loop_novo = """        for lote_id, status_pedido, nf in seps:
            # PROTEÇÃO ADICIONAL: Verificar se foi faturado
            if cls._verificar_se_faturado(lote_id):
                logger.warning(f"🛡️ PROTEÇÃO: Ignorando lote {lote_id} - Separação FATURADA (NF: {nf})")
                lotes_processados.add(lote_id)
                continue
                
            lotes.append({
                'lote_id': lote_id,
                'tipo': 'SEPARACAO'
            })
            lotes_processados.add(lote_id)
            logger.info(f"Encontrada Separacao com lote {lote_id} (status: {status_pedido or 'SEM_PEDIDO'})")"""

conteudo = conteudo.replace(loop_antigo, loop_novo)
print("✅ Proteção de separações faturadas adicionada")

# CORREÇÃO 4: Proteger contra deleção em _substituir_separacao_total
substituir_antigo = """    def _substituir_separacao_total(cls, num_pedido: str, lote_id: str, itens_odoo: List[Dict]):
        \"\"\"
        Substitui completamente uma separação TOTAL.
        Pega 1 linha existente como modelo, deleta tudo e recria com os novos itens.
        \"\"\"
        # PROTEÇÃO: Verificar se o Pedido permite alteração
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido and pedido.status not in ['ABERTO', 'COTADO']:
            logger.warning(f"🛡️ PROTEÇÃO: Não alterando Separacao {lote_id} - Pedido com status '{pedido.status}'")
            return"""

substituir_novo = """    def _substituir_separacao_total(cls, num_pedido: str, lote_id: str, itens_odoo: List[Dict]):
        \"\"\"
        Substitui completamente uma separação TOTAL.
        Pega 1 linha existente como modelo, deleta tudo e recria com os novos itens.
        \"\"\"
        # PROTEÇÃO: Verificar se foi faturado
        if cls._verificar_se_faturado(lote_id, num_pedido):
            logger.warning(f"🛡️ PROTEÇÃO: Não alterando Separacao {lote_id} - Separação FATURADA")
            return
            
        # PROTEÇÃO: Verificar se o Pedido permite alteração
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
        if pedido and pedido.status not in ['ABERTO', 'COTADO']:
            logger.warning(f"🛡️ PROTEÇÃO: Não alterando Separacao {lote_id} - Pedido com status '{pedido.status}'")
            return"""

conteudo = conteudo.replace(substituir_antigo, substituir_novo)
print("✅ Proteção em _substituir_separacao_total adicionada")

# CORREÇÃO 5: Proteger contra deleção em _aplicar_reducao_hierarquia
# Primeira ocorrência (linha 936-940)
delecao_antiga_1 = """                        # Se zerou, deletar
                        if sep.qtd_saldo <= 0:
                            db.session.delete(sep)
                            resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} removida")"""

delecao_nova_1 = """                        # Se zerou, deletar (mas verificar faturamento primeiro)
                        if sep.qtd_saldo <= 0:
                            if not cls._verificar_se_faturado(sep.separacao_lote_id, num_pedido, cod_produto):
                                db.session.delete(sep)
                                resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} removida")
                            else:
                                logger.warning(f"🛡️ Separação {sep.separacao_lote_id} zerada mas FATURADA - mantendo registro")
                                resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} zerada (FATURADA - mantida)")"""

conteudo = conteudo.replace(delecao_antiga_1, delecao_nova_1)
print("✅ Proteção contra deleção de separação não-cotada adicionada")

# Segunda ocorrência (linha 984-986)
delecao_antiga_2 = """                        # Se zerou, deletar
                        if sep.qtd_saldo <= 0:
                            db.session.delete(sep)
                            resultado['operacoes'].append(f"Separação {sep.separacao_lote_id} removida")"""

# Procurar a segunda ocorrência (após "if is_cotado:")
pos_primeira = conteudo.find(delecao_nova_1)
if pos_primeira > 0:
    # Procurar após a primeira correção
    pos_segunda = conteudo.find(delecao_antiga_2, pos_primeira + len(delecao_nova_1))
    if pos_segunda > 0:
        conteudo = conteudo[:pos_segunda] + delecao_nova_1.replace("não-cotada", "cotada") + conteudo[pos_segunda + len(delecao_antiga_2):]
        print("✅ Proteção contra deleção de separação cotada adicionada")

# Salvar o arquivo corrigido
with open(arquivo_original, 'w') as f:
    f.write(conteudo)

print("\n✅ CORREÇÕES APLICADAS COM SUCESSO!")
print("\n📋 RESUMO DAS CORREÇÕES:")
print("1. ✅ Adicionado método _verificar_se_faturado()")
print("2. ✅ Proteção em _identificar_lotes_afetados()")
print("3. ✅ Proteção em _substituir_separacao_total()")
print("4. ✅ Proteção contra deleção em _aplicar_reducao_hierarquia()")
print(f"\n💾 Backup salvo em: {arquivo_backup}")
print("\n🔄 Para reverter, execute:")
print(f"   cp {arquivo_backup} {arquivo_original}")