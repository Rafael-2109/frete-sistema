"""Routes administrativas (imprimir, resumo, atualizar status)."""
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.utils.lote_utils import gerar_lote_id
from app.utils.localizacao import LocalizacaoService
from app.utils.timezone import agora_utc_naive


def register_admin_routes(bp):

    @bp.route('/imprimir_separacao/<string:lote_id>') # type: ignore
    @login_required
    def imprimir_separacao(lote_id): # type: ignore
        """
        Imprime separacao para pedidos com pagamento antecipado.
        Nao requer embarque, usa transportadora fixa 'PAGAMENTO ANTECIPADO'.
        """
        try:
            itens_separacao = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).all()

            if not itens_separacao:
                flash('Separacao nao encontrada.', 'danger')
                return redirect(url_for('pedidos.lista_pedidos'))

            # Marcar como impressa
            for item in itens_separacao:
                item.separacao_impressa = True
                item.separacao_impressa_em = agora_utc_naive()
                item.separacao_impressa_por = current_user.nome if hasattr(current_user, 'nome') and current_user.nome else current_user.email

            db.session.commit()

            # Agregar dados para resumo
            resumo_separacao = {
                'lote_id': lote_id,
                'num_pedido': itens_separacao[0].num_pedido,
                'data_pedido': itens_separacao[0].data_pedido,
                'cliente': itens_separacao[0].raz_social_red,
                'cnpj_cpf': itens_separacao[0].cnpj_cpf,
                'cidade_destino': itens_separacao[0].nome_cidade,
                'uf_destino': itens_separacao[0].cod_uf,
                'total_produtos': len(itens_separacao),
                'peso_total': sum(item.peso or 0 for item in itens_separacao),
                'valor_total': sum(item.valor_saldo or 0 for item in itens_separacao),
                'pallet_total': sum(item.pallet or 0 for item in itens_separacao),
                'qtd_total': sum(item.qtd_saldo or 0 for item in itens_separacao),
            }

            return render_template(
                'pedidos/imprimir_separacao_antecipado.html',
                itens_separacao=itens_separacao,
                resumo_separacao=resumo_separacao,
                data_impressao=agora_utc_naive(),
                current_user=current_user
            )

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO IMPRIMIR SEPARACAO ANTECIPADO] {str(e)}")
            flash(f'Erro ao imprimir separacao: {str(e)}', 'danger')
            return redirect(url_for('pedidos.lista_pedidos'))



    @bp.route('/gerar_resumo', methods=['GET']) # type: ignore
    def gerar_resumo(): # type: ignore
        print("[DEBUG] 🔄 Iniciando geração de resumo com correção de separações...")
    
        # 1) Agrupar separacao
        resultados = (
            db.session.query(
                Separacao.num_pedido,
                Separacao.expedicao,
                Separacao.agendamento,
                Separacao.protocolo,
                func.min(Separacao.data_pedido).label('data_pedido'),
                func.min(Separacao.cnpj_cpf).label('cnpj_cpf'),
                func.min(Separacao.raz_social_red).label('raz_social_red'),
                func.min(Separacao.nome_cidade).label('nome_cidade'),
                func.min(Separacao.cod_uf).label('cod_uf'),
                func.sum(Separacao.valor_saldo).label('valor_saldo_total'),
                func.sum(Separacao.pallet).label('pallet_total'),
                func.sum(Separacao.peso).label('peso_total'),
                func.min(Separacao.rota).label('rota'),
                func.min(Separacao.sub_rota).label('sub_rota'),
                func.min(Separacao.observ_ped_1).label('observ_ped_1'),
                func.min(Separacao.roteirizacao).label('roteirizacao'),
            )
            .group_by(
                Separacao.num_pedido,
                Separacao.expedicao,
                Separacao.agendamento,
                Separacao.protocolo
            )
            .all()
        )

        # ✅ NOVO: Corrige separações órfãs ANTES de criar/atualizar pedidos
        separacoes_sem_lote = Separacao.query.filter(Separacao.separacao_lote_id.is_(None)).all()
        if separacoes_sem_lote:
            print(f"[DEBUG] 📦 Corrigindo {len(separacoes_sem_lote)} separações órfãs...")
        
            # Agrupa separações por pedido para gerar lotes únicos
            from collections import defaultdict
            separacoes_por_pedido = defaultdict(list)
            for sep in separacoes_sem_lote:
                if sep.num_pedido:
                    chave_pedido = f"{sep.num_pedido}_{sep.expedicao}_{sep.agendamento}_{sep.protocolo}"
                    separacoes_por_pedido[chave_pedido].append(sep)
        
            # Gera lote único para cada grupo de pedido
            for chave_pedido, separacoes in separacoes_por_pedido.items():
                novo_lote_id = gerar_lote_id()
                print(f"[DEBUG]   ✅ Criando lote {novo_lote_id} para {len(separacoes)} itens do pedido {separacoes[0].num_pedido}")
            
                for sep in separacoes:
                    sep.separacao_lote_id = novo_lote_id

        # 2) Para cada group, insere/atualiza em Pedido
        for row in resultados:
            pedido_existente = Pedido.query.filter_by(
                num_pedido=row.num_pedido,
                expedicao=row.expedicao,
                agendamento=row.agendamento,
                protocolo=row.protocolo
            ).first()
        
            # ✅ NOVO: Busca o lote de separação para este pedido
            separacao_exemplo = Separacao.query.filter_by(
                num_pedido=row.num_pedido,
                expedicao=row.expedicao,
                agendamento=row.agendamento,
                protocolo=row.protocolo
            ).first()
        
            lote_id = separacao_exemplo.separacao_lote_id if separacao_exemplo else None
        
            # IMPORTANTE: Após migração, Pedido é uma VIEW
            # Não podemos criar/atualizar registros em Pedido
            # A VIEW agrega automaticamente as Separacoes
        
            # O que podemos fazer é atualizar campos nas Separacoes se necessário
            if lote_id and not pedido_existente:
                # Se não existe pedido na VIEW, significa que as Separacoes precisam de ajustes
                separacoes_do_grupo = Separacao.query.filter_by(
                    num_pedido=row.num_pedido,
                    expedicao=row.expedicao,
                    agendamento=row.agendamento,
                    protocolo=row.protocolo
                ).all()
            
                # Normalizar dados nas Separacoes
                for sep in separacoes_do_grupo:
                    # Aplicar normalização diretamente nas Separacoes
                    if hasattr(sep, 'cidade_normalizada') and not sep.cidade_normalizada:
                        # Normalizar cidade/UF se disponível
                        try:
                            sep.cidade_normalizada = LocalizacaoService.normalizar_cidade(sep.nome_cidade)
                            sep.uf_normalizada = LocalizacaoService.normalizar_uf(sep.cod_uf)
                            sep.codigo_ibge = LocalizacaoService.obter_codigo_ibge(sep.nome_cidade, sep.cod_uf)
                        except ImportError:
                            # Se o serviço não existir, apenas pular a normalização
                            pass

        db.session.commit()
    
        # ✅ NOVO: Verifica resultado da correção
        separacoes_orfas_restantes = Separacao.query.filter(Separacao.separacao_lote_id.is_(None)).count()
        pedidos_com_separacao = Pedido.query.filter(Pedido.separacao_lote_id.isnot(None)).count()
    
        flash(f"Resumo gerado/atualizado com sucesso! {pedidos_com_separacao} pedidos com separação linkada.", "success")
    
        if separacoes_orfas_restantes == 0:
            flash("✅ Todas as separações foram corretamente linkadas aos pedidos!", "success")
        else:
            flash(f"⚠️ Ainda restam {separacoes_orfas_restantes} separações órfãs para análise.", "warning")

        return redirect(url_for('pedidos.lista_pedidos'))  # hipotético: rotas do blueprint de pedidos


    @bp.route('/atualizar_status', methods=['GET', 'POST']) # type: ignore
    @login_required
    def atualizar_status(): # type: ignore
        """
        Atualiza todos os status dos pedidos baseado na lógica status_calculado
        """
        try:
            pedidos = Pedido.query.all()
            atualizados = 0
        
            for pedido in pedidos:
                status_correto = pedido.status_calculado
                if pedido.status != status_correto:
                    # Atualizar status em Separacao
                    if pedido.separacao_lote_id:
                        Separacao.query.filter_by(
                            separacao_lote_id=pedido.separacao_lote_id
                        ).update({'status': status_correto})
                        atualizados += 1
        
            if atualizados > 0:
                db.session.commit()
                # Invalidar cache de contadores (status mudou)
                from app.pedidos.services.counter_service import PedidosCounterService
                PedidosCounterService.invalidar_cache()
                flash(f"✅ {atualizados} status de pedidos atualizados com sucesso!", "success")
            else:
                flash("✅ Todos os status já estão corretos!", "info")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao atualizar status: {str(e)}", "error")
    
        return redirect(url_for('pedidos.lista_pedidos'))
