"""
Service para Ordens de Produção
"""
from app import db
from app.manufatura.models import (
    OrdemProducao, ListaMateriais, RecursosProducao,
    RequisicaoCompras, LeadTimeFornecedor
)
from app.carteira.models import CarteiraPrincipal, CadastroPalletizacao, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.estoque.models import MovimentacaoEstoque
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, extract
from decimal import Decimal
import json


class OrdemProducaoService:
    
    def criar_ordem(self, dados):
        """Cria uma nova ordem de produção"""
        
        # Gerar número sequencial
        ultimo_numero = db.session.query(
            func.max(OrdemProducao.numero_ordem)
        ).scalar()
        
        if ultimo_numero:
            proximo = int(ultimo_numero.split('-')[-1]) + 1
        else:
            proximo = 1
        
        numero_ordem = f"OP-{datetime.now().year}-{proximo:06d}"
        
        # Explodir BOM se necessário
        materiais_necessarios = None
        if dados.get('explodir_bom', True):
            materiais_necessarios = self.explodir_bom(
                dados['cod_produto'],
                dados['qtd_planejada']
            )
        
        # Criar ordem
        ordem = OrdemProducao(
            numero_ordem=numero_ordem,
            origem_ordem=dados.get('origem_ordem', 'Manual'),
            status='Planejada',
            cod_produto=dados['cod_produto'],
            nome_produto=dados.get('nome_produto'),
            materiais_necessarios=materiais_necessarios,
            qtd_planejada=Decimal(str(dados['qtd_planejada'])),
            qtd_produzida=0,
            data_inicio_prevista=dados['data_inicio_prevista'],
            data_fim_prevista=dados['data_fim_prevista'],
            linha_producao=dados.get('linha_producao'),
            turno=dados.get('turno'),
            lote_producao=dados.get('lote_producao'),
            custo_previsto=dados.get('custo_previsto'),
            criado_por=dados.get('criado_por', 'Sistema')
        )
        
        db.session.add(ordem)
        
        # Se é MTO, vincular com pedido
        if dados.get('origem_ordem') == 'MTO' and dados.get('pedido_origem'):
            self._vincular_pedido_mto(ordem, dados['pedido_origem'])
        
        # Gerar necessidades de compra
        if materiais_necessarios:
            self._gerar_necessidades_compra(ordem, materiais_necessarios)
        
        db.session.commit()
        return ordem
    
    def explodir_bom(self, cod_produto, qtd_base):
        """Explode lista de materiais recursivamente"""
        
        materiais = {}
        self._explodir_bom_recursivo(cod_produto, Decimal(str(qtd_base)), materiais, nivel=0)
        
        # Calcular disponibilidade de cada material
        for cod_material in materiais:
            estoque_atual = self._calcular_estoque_material(cod_material)
            materiais[cod_material]['qtd_disponivel'] = float(estoque_atual)
            materiais[cod_material]['qtd_comprar'] = max(
                0,
                materiais[cod_material]['qtd_necessaria'] - float(estoque_atual)
            )
        
        return list(materiais.values())
    
    def _explodir_bom_recursivo(self, cod_produto, qtd_base, materiais, nivel=0, max_nivel=10):
        """Recursão para explodir BOM multi-nível"""
        
        if nivel >= max_nivel:
            return
        
        # Buscar componentes diretos
        componentes = ListaMateriais.query.filter_by(
            cod_produto_produzido=cod_produto,
            status='ativo'
        ).all()
        
        for comp in componentes:
            cod_comp = comp.cod_produto_componente
            qtd_necessaria = qtd_base * comp.qtd_utilizada
            
            if cod_comp in materiais:
                materiais[cod_comp]['qtd_necessaria'] += float(qtd_necessaria)
            else:
                # Verificar se é comprado ou produzido
                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=cod_comp
                ).first()
                
                materiais[cod_comp] = {
                    'cod_produto': cod_comp,
                    'nome_produto': comp.nome_produto_componente,
                    'qtd_necessaria': float(qtd_necessaria),
                    'qtd_disponivel': 0,
                    'qtd_comprar': 0,
                    'tipo': 'comprado' if cadastro and cadastro.produto_comprado else 'produzido'
                }
            
            # Se é produzido, explodir seus componentes
            if materiais[cod_comp]['tipo'] == 'produzido':
                self._explodir_bom_recursivo(
                    cod_comp, qtd_necessaria, materiais, nivel + 1, max_nivel
                )
    
    def _calcular_estoque_material(self, cod_produto):
        """Calcula estoque disponível do material"""
        
        resultado = db.session.query(
            func.sum(
                func.case(
                    [
                        (MovimentacaoEstoque.tipo_movimentacao.in_([
                            'ENTRADA_COMPRA', 'PRODUCAO', 'AJUSTE_POSITIVO'
                        ]), MovimentacaoEstoque.qtd_movimentacao),
                        (MovimentacaoEstoque.tipo_movimentacao.in_([
                            'SAIDA_VENDA', 'CONSUMO_BOM', 'AJUSTE_NEGATIVO'
                        ]), -MovimentacaoEstoque.qtd_movimentacao)
                    ],
                    else_=0
                )
            )
        ).filter(
            MovimentacaoEstoque.cod_produto == cod_produto
        ).scalar()
        
        return Decimal(str(resultado or 0))
    
    def _vincular_pedido_mto(self, ordem, pedido_origem):
        """Vincula ordem MTO com pedido origem usando separacao_lote_id"""
        
        # Sempre usar separacao_lote_id como vínculo principal
        if pedido_origem.get('separacao_lote_id'):
            ordem.separacao_lote_id = pedido_origem['separacao_lote_id']
            ordem.num_pedido_origem = pedido_origem.get('num_pedido')
            
            # Buscar dados do cliente
            if pedido_origem.get('tipo') == 'separacao':
                separacao = Separacao.query.filter_by(
                    separacao_lote_id=pedido_origem['separacao_lote_id']
                ).first()
                if separacao:
                    ordem.raz_social_red = separacao.raz_social_red
                    ordem.qtd_pedido_atual = separacao.qtd_saldo
            else:
                # Buscar em CarteiraPrincipal se necessário
                carteira = CarteiraPrincipal.query.filter_by(
                    separacao_lote_id=pedido_origem['separacao_lote_id']
                ).first()
                if carteira:
                    ordem.raz_social_red = carteira.raz_social_red
                    ordem.qtd_pedido_atual = carteira.qtd_saldo_produto_pedido
    
    def _gerar_necessidades_compra(self, ordem, materiais):
        """Gera necessidades de compra para materiais faltantes e ordens filhas para produtos produzidos"""
        
        for material in materiais:
            if material['tipo'] == 'comprado' and material['qtd_comprar'] > 0:
                # Material comprado - gerar necessidade de compra
                self._gerar_necessidade_compra(ordem, material)
                
            elif material['tipo'] == 'produzido' and material['qtd_comprar'] > 0:
                # Material produzido - criar ordem filha automaticamente
                self._criar_ordem_filha(ordem, material)
    
    def _gerar_necessidade_compra(self, ordem, material):
        """Gera necessidade de compra com cálculo de lead time"""
        
        # Buscar lead time do fornecedor
        lead_time = db.session.query(LeadTimeFornecedor.lead_time_previsto).filter_by(
            cod_produto=material['cod_produto']
        ).first()
        
        lead_time_dias = lead_time[0] if lead_time else 7  # Default 7 dias
        
        # Calcular data de necessidade considerando lead time
        data_necessidade = self._calcular_data_com_lead_time(
            ordem.data_inicio_prevista, 
            lead_time_dias
        )
        
        # Verificar se já existe necessidade pendente
        existe = RequisicaoCompras.query.filter_by(
            cod_produto=material['cod_produto'],
            status='Pendente',
            necessidade=True
        ).first()
        
        if not existe:
            requisicao = RequisicaoCompras(
                num_requisicao=f"NEC-{datetime.now().strftime('%Y%m%d')}-{material['cod_produto']}",
                data_requisicao_criacao=datetime.now().date(),
                cod_produto=material['cod_produto'],
                nome_produto=material['nome_produto'],
                qtd_produto_requisicao=Decimal(str(material['qtd_comprar'])),
                qtd_produto_sem_requisicao=Decimal(str(material['qtd_comprar'])),
                necessidade=True,
                data_necessidade=data_necessidade,
                lead_time_previsto=lead_time_dias,
                status='Pendente'
            )
            db.session.add(requisicao)
        else:
            # Atualizar quantidade necessária
            existe.qtd_produto_requisicao += Decimal(str(material['qtd_comprar']))
            existe.qtd_produto_sem_requisicao += Decimal(str(material['qtd_comprar']))
            
            # Atualizar data se mais urgente
            if data_necessidade < existe.data_necessidade:
                existe.data_necessidade = data_necessidade
    
    def _criar_ordem_filha(self, ordem_pai, material):
        """Cria ordem filha automaticamente para produto produzido"""
        
        # Verificar se já existe ordem filha
        existe_filha = OrdemProducao.query.filter_by(
            ordem_pai_id=ordem_pai.id,
            cod_produto=material['cod_produto']
        ).first()
        
        if not existe_filha:
            # Calcular data de necessidade (1 dia antes da ordem pai começar)
            data_fim_filha = ordem_pai.data_inicio_prevista - timedelta(days=1)
            
            # Buscar capacidade de produção
            recurso = RecursosProducao.query.filter_by(
                cod_produto=material['cod_produto']
            ).first()
            
            if recurso:
                # Calcular tempo necessário baseado na capacidade
                minutos_necessarios = (material['qtd_necessaria'] / recurso.capacidade_unidade_minuto) if recurso.capacidade_unidade_minuto else 480
                dias_necessarios = max(1, int(minutos_necessarios / 480))  # 480 min = 8 horas/dia
                data_inicio_filha = data_fim_filha - timedelta(days=dias_necessarios)
            else:
                data_inicio_filha = data_fim_filha - timedelta(days=1)
            
            # Criar ordem filha
            dados_filha = {
                'origem_ordem': 'Automática',
                'cod_produto': material['cod_produto'],
                'nome_produto': material['nome_produto'],
                'qtd_planejada': material['qtd_necessaria'],
                'data_inicio_prevista': data_inicio_filha,
                'data_fim_prevista': data_fim_filha,
                'ordem_pai_id': ordem_pai.id,
                'tipo_ordem': 'filha',
                'nivel_bom': ordem_pai.nivel_bom + 1,
                'explodir_bom': True  # Explodir BOM da ordem filha também
            }
            
            self.criar_ordem(dados_filha)
    
    def _calcular_data_com_lead_time(self, data_entrega, lead_time_dias):
        """Calcula data considerando apenas dias úteis"""
        
        data_atual = data_entrega
        dias_uteis = 0
        
        while dias_uteis < lead_time_dias:
            data_atual = data_atual - timedelta(days=1)
            # Pular fins de semana (5=sábado, 6=domingo)
            if data_atual.weekday() < 5:
                dias_uteis += 1
        
        return data_atual
    
    def gerar_ordens_mto_automaticas(self):
        """Gera ordens MTO automaticamente para pedidos com lead_time_mto"""
        
        # Buscar pedidos em Separacao que precisam de ordem MTO
        pedidos_mto = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.num_pedido,
            Separacao.cod_produto,
            Separacao.nome_produto,
            Separacao.qtd_saldo,
            Separacao.expedicao,
            CadastroPalletizacao.lead_time_mto,
            CadastroPalletizacao.disparo_producao
        ).join(
            CadastroPalletizacao,
            Separacao.cod_produto == CadastroPalletizacao.cod_produto
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Pedido.status != 'FATURADO',
            CadastroPalletizacao.disparo_producao == 'MTO',
            CadastroPalletizacao.lead_time_mto.isnot(None),
            Separacao.expedicao.isnot(None)
        ).all()
        
        ordens_criadas = []
        
        for pedido in pedidos_mto:
            # Verificar se já existe ordem para este pedido
            existe_ordem = self._verificar_ordem_existente_mto(
                pedido.separacao_lote_id,
                pedido.cod_produto
            )
            
            if not existe_ordem:
                # Calcular data início baseado no lead time
                data_inicio = self._calcular_data_inicio_mto(
                    pedido.expedicao,
                    pedido.lead_time_mto
                )
                
                # Criar ordem MTO
                dados_ordem = {
                    'origem_ordem': 'MTO',
                    'cod_produto': pedido.cod_produto,
                    'nome_produto': pedido.nome_produto,
                    'qtd_planejada': pedido.qtd_saldo,
                    'data_inicio_prevista': data_inicio,
                    'data_fim_prevista': pedido.expedicao,
                    'pedido_origem': {
                        'tipo': 'separacao',
                        'separacao_lote_id': pedido.separacao_lote_id,
                        'num_pedido': pedido.num_pedido
                    }
                }
                
                ordem = self.criar_ordem(dados_ordem)
                ordens_criadas.append(ordem)
        
        return ordens_criadas
    
    def _verificar_ordem_existente_mto(self, separacao_lote_id, cod_produto):
        """Verifica se já existe ordem MTO para o pedido"""
        
        # Buscar diretamente pelo separacao_lote_id
        ordem_existe = OrdemProducao.query.filter(
            OrdemProducao.origem_ordem == 'MTO',
            OrdemProducao.separacao_lote_id == separacao_lote_id,
            OrdemProducao.cod_produto == cod_produto,
            OrdemProducao.status != 'Cancelada'
        ).first()
        
        return ordem_existe is not None
    
    def _calcular_data_inicio_mto(self, data_expedicao, lead_time_dias):
        """Calcula data de início considerando dias úteis"""
        
        from app.utils.data_util import calcular_dias_uteis_retroativo
        
        # Por enquanto, cálculo simples
        return data_expedicao - timedelta(days=lead_time_dias)
    
    def sequenciar_ordens(self, linha_producao, data_inicio, data_fim):
        """Sequencia ordens de produção para uma linha"""
        
        # Buscar ordens do período
        ordens = OrdemProducao.query.filter(
            OrdemProducao.linha_producao == linha_producao,
            OrdemProducao.status.in_(['Planejada', 'Liberada']),
            or_(
                and_(
                    OrdemProducao.data_inicio_prevista >= data_inicio,
                    OrdemProducao.data_inicio_prevista <= data_fim
                ),
                and_(
                    OrdemProducao.data_fim_prevista >= data_inicio,
                    OrdemProducao.data_fim_prevista <= data_fim
                )
            )
        ).order_by(
            OrdemProducao.data_inicio_prevista
        ).all()
        
        # Buscar capacidade da linha
        recursos = RecursosProducao.query.filter_by(
            linha_producao=linha_producao,
            disponivel=True
        ).all()
        
        sequenciamento = []
        tempo_acumulado = 0
        
        for ordem in ordens:
            # Calcular tempo de produção
            recurso = next(
                (r for r in recursos if r.cod_produto == ordem.cod_produto),
                None
            )
            
            if recurso:
                tempo_producao = float(ordem.qtd_planejada) / float(recurso.capacidade_unidade_minuto)
                tempo_setup = recurso.tempo_setup or 0
                tempo_total = tempo_producao + tempo_setup
                
                sequenciamento.append({
                    'ordem': ordem.numero_ordem,
                    'produto': ordem.cod_produto,
                    'qtd': float(ordem.qtd_planejada),
                    'tempo_setup': tempo_setup,
                    'tempo_producao': tempo_producao,
                    'tempo_total': tempo_total,
                    'inicio': tempo_acumulado,
                    'fim': tempo_acumulado + tempo_total,
                    'prioridade': 'ALTA' if ordem.origem_ordem == 'MTO' else 'NORMAL'
                })
                
                tempo_acumulado += tempo_total
        
        return sequenciamento
    
    def atualizar_status_ordem(self, ordem_id, novo_status, usuario='Sistema'):
        """Atualiza status da ordem de produção"""
        
        ordem = OrdemProducao.query.get_or_404(ordem_id)
        
        # Validar transição de status
        transicoes_validas = {
            'Planejada': ['Liberada', 'Cancelada'],
            'Liberada': ['Em Produção', 'Cancelada'],
            'Em Produção': ['Concluída', 'Cancelada'],
            'Concluída': [],
            'Cancelada': []
        }
        
        if novo_status not in transicoes_validas.get(ordem.status, []):
            raise ValueError(f"Transição inválida: {ordem.status} -> {novo_status}")
        
        ordem.status = novo_status
        ordem.atualizado_em = datetime.now()
        
        # Registrar datas reais
        if novo_status == 'Em Produção' and not ordem.data_inicio_real:
            ordem.data_inicio_real = datetime.now().date()
        elif novo_status == 'Concluída' and not ordem.data_fim_real:
            ordem.data_fim_real = datetime.now().date()
        
        db.session.commit()
        return ordem
    
    def validar_quantidade_mto(self, ordem_id):
        """Valida se a quantidade do pedido MTO mudou"""
        
        ordem = OrdemProducao.query.get_or_404(ordem_id)
        
        if ordem.origem_ordem != 'MTO' or not ordem.separacao_lote_id:
            return {
                'valido': True,
                'mensagem': 'Ordem não é MTO ou não tem vínculo'
            }
        
        # Buscar quantidade atual do pedido
        # Prioridade: Separacao > PreSeparacaoItem
        separacao = Separacao.query.filter_by(
            separacao_lote_id=ordem.separacao_lote_id,
            cod_produto=ordem.cod_produto
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Pedido.status != 'FATURADO'
        ).first()
        
        if separacao:
            qtd_atual = separacao.qtd_saldo
            fonte = 'Separacao'
        else:
            # Buscar em PreSeparacaoItem
            pre_separacao = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=ordem.separacao_lote_id,
                cod_produto=ordem.cod_produto
            ).filter(
                ~PreSeparacaoItem.separacao_lote_id.in_(
                    db.session.query(Separacao.separacao_lote_id).distinct()
                )
            ).first()
            
            if pre_separacao:
                qtd_atual = pre_separacao.qtd_selecionada_usuario
                fonte = 'PreSeparacaoItem'
            else:
                return {
                    'valido': False,
                    'mensagem': 'Pedido não encontrado',
                    'qtd_ordem': float(ordem.qtd_pedido_atual) if ordem.qtd_pedido_atual else 0,
                    'qtd_atual': 0,
                    'fonte': 'Não encontrado'
                }
        
        # Comparar quantidades
        qtd_mudou = False
        if ordem.qtd_pedido_atual != qtd_atual:
            qtd_mudou = True
            # Atualizar quantidade na ordem
            ordem.qtd_pedido_atual = qtd_atual
            db.session.commit()
        
        return {
            'valido': not qtd_mudou,
            'mensagem': 'Quantidade alterada' if qtd_mudou else 'Quantidade OK',
            'qtd_ordem': float(ordem.qtd_planejada),
            'qtd_pedido_vinculo': float(ordem.qtd_pedido_atual) if ordem.qtd_pedido_atual else 0,
            'qtd_pedido_atual': float(qtd_atual),
            'fonte': fonte,
            'atualizado': qtd_mudou
        }