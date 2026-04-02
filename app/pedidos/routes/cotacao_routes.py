"""Routes de cotacao manual e embarque FOB."""
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required

from app import db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.transportadoras.models import Transportadora
from app.veiculos.models import Veiculo
from app.embarques.models import Embarque, EmbarqueItem
from app.utils.localizacao import LocalizacaoService
from app.utils.embarque_numero import obter_proximo_numero_embarque
from app.utils.tabela_frete_manager import TabelaFreteManager
from app.utils.timezone import agora_utc_naive


def register_cotacao_routes(bp):

    @bp.route('/cotacao_manual', methods=['GET', 'POST']) # type: ignore
    @login_required
    def cotacao_manual(): # type: ignore
        """
        Processa a cotação manual dos pedidos selecionados
        """
        if request.method == 'POST':
            # Tenta primeiro por separacao_lote_ids (novo padrão)
            lista_ids_str = request.form.getlist("separacao_lote_ids")
        
            if not lista_ids_str:
                lista_ids_str = request.form.getlist("pedido_ids")
        
            if not lista_ids_str:
                flash("Nenhum pedido selecionado!", "warning")
                return redirect(url_for("pedidos.lista_pedidos"))

            # Detecta se são separacao_lote_ids (strings alfanuméricas) ou IDs numéricos
            # separacao_lote_id pode ter formatos: LOTE-xxx, LOTE_xxx, CLAUDE-xxx, etc.
            primeiro_id = lista_ids_str[0] if lista_ids_str else ''
            eh_separacao_lote_id = primeiro_id and not primeiro_id.isdigit()

            if eh_separacao_lote_id:
                # São separacao_lote_ids (strings) - usar diretamente
                lista_ids = lista_ids_str
            else:
                # São IDs numéricos - converter para int
                lista_ids = [int(x) for x in lista_ids_str if x.isdigit()]

            # Armazena no session para usar nas rotas subsequentes
            session["cotacao_manual_pedidos"] = lista_ids

            # Busca pedidos pelo tipo de ID recebido
            if eh_separacao_lote_id:
                # Busca por separacao_lote_id (formato: LOTE-xxx, CLAUDE-xxx, etc.)
                pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
            else:
                # Se são IDs numéricos, converter para string e buscar por num_pedido
                pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()
        
            if not pedidos:
                flash("Nenhum pedido encontrado!", "warning")
                return redirect(url_for("pedidos.lista_pedidos"))

            # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
            # A normalização já deve estar presente na VIEW ou será feita em memória se necessário
            # NOTA: Pedido é uma VIEW, dados de normalização já devem vir da Separacao
            # Se precisar normalizar, fazer diretamente na Separacao usando separacao_lote_id

            # Carrega transportadoras e veículos para os formulários
            transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
            veiculos = Veiculo.query.order_by(Veiculo.nome).all()

            return render_template(
                'pedidos/cotacao_manual.html',
                pedidos=pedidos,
                transportadoras=transportadoras,
                veiculos=veiculos
            )
    
        # Se GET, redireciona para lista de pedidos
        return redirect(url_for('pedidos.lista_pedidos'))


    @bp.route('/processar_cotacao_manual', methods=['POST']) # type: ignore
    @login_required
    def processar_cotacao_manual(): # type: ignore
        """
        Processa os dados da cotação manual e cria o embarque
        """
        try:
            # Recupera pedidos da sessão
            lista_ids = session.get("cotacao_manual_pedidos", [])
            if not lista_ids:
                flash("Sessão expirada. Selecione os pedidos novamente.", "warning")
                return redirect(url_for("pedidos.lista_pedidos"))

            # Dados do formulário
            transportadora_id = request.form.get('transportadora_id')
            modalidade = request.form.get('modalidade')
            valor_frete = request.form.get('valor_frete')

            # Validações básicas
            if not transportadora_id or not modalidade or not valor_frete:
                flash("Todos os campos são obrigatórios!", "error")
                return redirect(url_for("pedidos.cotacao_manual"))

            try:
                transportadora_id = int(transportadora_id)
                valor_frete = float(valor_frete.replace(',', '.'))
            except ValueError:
                flash("Valores inválidos fornecidos!", "error")
                return redirect(url_for("pedidos.cotacao_manual"))

            # Carrega pedidos e transportadora

            # Detecta se são separacao_lote_ids (strings alfanuméricas) ou IDs numéricos
            primeiro_id = lista_ids[0] if lista_ids else ''
            eh_separacao_lote_id = primeiro_id and isinstance(primeiro_id, str) and not primeiro_id.isdigit()

            if eh_separacao_lote_id:
                # São separacao_lote_ids (formato: LOTE-xxx, CLAUDE-xxx, etc.)
                pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
            else:
                # Se são IDs numéricos, buscar por num_pedido
                pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()
            transportadora = db.session.get(Transportadora,transportadora_id) if transportadora_id else None

            if not pedidos or not transportadora:
                flash("Dados não encontrados!", "error")
                return redirect(url_for("pedidos.cotacao_manual"))

            # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
            # A normalização já deve estar presente na VIEW ou será feita em memória se necessário

            # Importa as classes necessárias
            from app.embarques.models import Embarque, EmbarqueItem
            from app.cotacao.models import Cotacao, CotacaoItem
            from app.utils.embarque_numero import obter_proximo_numero_embarque

            # Calcula totais dos pedidos
            peso_total = sum(p.peso_total or 0 for p in pedidos)
            valor_total = sum(p.valor_saldo_total or 0 for p in pedidos)
            pallet_total = sum(p.pallet_total or 0 for p in pedidos)

            # Separar pedidos Nacom de CarVia (CarVia nao tem Separacao nem CotacaoItem)
            pedidos_nacom = [p for p in pedidos if not (p.separacao_lote_id or '').startswith('CARVIA-')]
            pedidos_carvia = [p for p in pedidos if (p.separacao_lote_id or '').startswith('CARVIA-')]

            # Cria a cotação manual (para itens Nacom — ou para manter dados da tabela de frete)
            from app.utils.tabela_frete_manager import TabelaFreteManager

            dados_cotacao = TabelaFreteManager.preparar_cotacao_manual(valor_frete, modalidade, icms_incluso=True)

            cotacao = None
            if pedidos_nacom:
                # Nacom presente: criar Cotacao normalmente
                cotacao = Cotacao(
                    usuario_id=1,
                    transportadora_id=transportadora_id,
                    status='Fechado',
                    data_criacao=agora_utc_naive(),
                    data_fechamento=agora_utc_naive(),
                    tipo_carga='DIRETA',
                    valor_total=valor_total,
                    peso_total=peso_total,
                    **dados_cotacao
                )
                db.session.add(cotacao)
                db.session.flush()

            # Cria itens da cotação (apenas Nacom — CarVia nao precisa)
            for pedido in pedidos_nacom:
                cotacao_item = CotacaoItem(
                    cotacao_id=cotacao.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    pedido_id_old=pedido.id if hasattr(pedido, 'id') else 0,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    peso=pedido.peso_total or 0,
                    valor=pedido.valor_saldo_total or 0,
                    **dados_cotacao
                )
                db.session.add(cotacao_item)

            # Cria o embarque
            embarque = Embarque(
                numero=obter_proximo_numero_embarque(),
                transportadora_id=transportadora_id,
                status='ativo',
                tipo_cotacao='Manual',
                valor_total=valor_total,
                pallet_total=pallet_total,
                peso_total=peso_total,
                tipo_carga='DIRETA',
                cotacao_id=cotacao.id if cotacao else None,
                transportadora_optante=False,
                criado_por='Sistema'
            )
            # Atribui campos da tabela usando TabelaFreteManager
            TabelaFreteManager.atribuir_campos_objeto(embarque, dados_cotacao)
            embarque.icms_destino = 0
            db.session.add(embarque)
            db.session.flush()  # Para obter o ID do embarque

            # Cria itens do embarque — Nacom (fluxo existente)
            dados_vazio = TabelaFreteManager.preparar_cotacao_vazia()
            for pedido in pedidos_nacom:
                nome_cidade_correto, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)

                embarque_item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    protocolo_agendamento=str(pedido.protocolo) if pedido.protocolo else '',
                    data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                    peso=pedido.peso_total or 0,
                    valor=pedido.valor_saldo_total or 0,
                    pallets=pedido.pallet_total,
                    uf_destino=uf_correto,
                    cidade_destino=nome_cidade_correto,
                    cotacao_id=cotacao.id if cotacao else None,
                    volumes=None
                )
                TabelaFreteManager.atribuir_campos_objeto(embarque_item, dados_vazio)
                embarque_item.icms_destino = None
                db.session.add(embarque_item)

            # Cria itens do embarque — CarVia (provisorios)
            for pedido in pedidos_carvia:
                # CarVia usa cidade/UF do Pedido (VIEW) diretamente
                uf_cv = (pedido.cod_uf or '').strip()
                cidade_cv = (pedido.nome_cidade or '').strip()

                # Extrair carvia_cotacao_id do prefixo
                lote_id = pedido.separacao_lote_id or ''
                carvia_cot_id = None
                try:
                    if lote_id.startswith('CARVIA-PED-'):
                        # Pedido CarVia — buscar cotacao_id via CarviaPedido
                        ped_id = int(lote_id.replace('CARVIA-PED-', ''))
                        from app.carvia.models import CarviaPedido as _CP
                        _ped = db.session.get(_CP, ped_id)
                        carvia_cot_id = _ped.cotacao_id if _ped else None
                    elif lote_id.startswith('CARVIA-'):
                        carvia_cot_id = int(lote_id.replace('CARVIA-', ''))
                except (ValueError, TypeError):
                    pass

                # Calcular volumes e peso cubado das motos da cotacao
                carvia_volumes = None
                carvia_peso_cubado = None
                if carvia_cot_id:
                    try:
                        from app.carvia.models import CarviaCotacaoMoto
                        agg = db.session.query(
                            db.func.coalesce(db.func.sum(CarviaCotacaoMoto.quantidade), 0),
                            db.func.coalesce(db.func.sum(CarviaCotacaoMoto.peso_cubado_total), 0),
                        ).filter_by(cotacao_id=carvia_cot_id).first()
                        carvia_volumes = int(agg[0]) or None #type: ignore # noqa: E741
                        carvia_peso_cubado = float(agg[1]) or None # type: ignore # noqa: E741
                    except Exception:
                        pass

                embarque_item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    nota_fiscal=pedido.nf or None,
                    protocolo_agendamento='',
                    data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                    peso=pedido.peso_total or 0,
                    peso_cubado=carvia_peso_cubado,
                    valor=pedido.valor_saldo_total or 0,
                    pallets=0,
                    uf_destino=uf_cv,
                    cidade_destino=cidade_cv,
                    volumes=carvia_volumes,
                    provisorio=not pedido.nf,
                    carvia_cotacao_id=carvia_cot_id,
                )
                # DIRETA: dados da tabela ficam no Embarque (campos vazio no item)
                TabelaFreteManager.atribuir_campos_objeto(embarque_item, dados_vazio)
                embarque_item.icms_destino = None
                db.session.add(embarque_item)

            # Commit antes de atualizar separações (Embarque e itens já criados)
            db.session.commit()

            # Atualiza separacoes — apenas Nacom (CarVia nao tem Separacao)
            for pedido in pedidos_nacom:
                if pedido.separacao_lote_id:
                    Separacao.atualizar_cotacao(
                        separacao_lote_id=pedido.separacao_lote_id,
                        cotacao_id=cotacao.id,
                        nf_cd=False
                    )

            # Limpa a sessão
            if "cotacao_manual_pedidos" in session:
                del session["cotacao_manual_pedidos"]

            flash(f"Cotação manual criada com sucesso! Embarque #{embarque.numero} gerado.", "success")
            return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao processar cotação manual: {str(e)}", "error")
            return redirect(url_for("pedidos.cotacao_manual"))


    @bp.route('/embarque_fob', methods=['POST']) # type: ignore
    @login_required
    def embarque_fob(): # type: ignore
        """
        Processa a criação de embarque FOB
        Valida se todos os pedidos selecionados têm rota "FOB"
        """
        try:
            # Tenta primeiro por separacao_lote_ids (novo padrão)
            lista_ids_str = request.form.getlist("separacao_lote_ids")
        
            # Fallback para pedido_ids (retrocompatibilidade)
            if not lista_ids_str:
                lista_ids_str = request.form.getlist("pedido_ids")
        
            if not lista_ids_str:
                flash("Nenhum pedido selecionado!", "warning")
                return redirect(url_for("pedidos.lista_pedidos"))

            # Detecta se são separacao_lote_ids (strings alfanuméricas) ou IDs numéricos
            primeiro_id = lista_ids_str[0] if lista_ids_str else ''
            eh_separacao_lote_id = primeiro_id and not primeiro_id.isdigit()

            if eh_separacao_lote_id:
                # São separacao_lote_ids (strings) - usar diretamente
                lista_ids = lista_ids_str
            else:
                # São IDs numéricos - converter para int
                lista_ids = [int(x) for x in lista_ids_str if x.isdigit()]

            # Carrega os pedidos do banco
            from app.separacao.models import Separacao

            # Busca pedidos pelo tipo de ID recebido
            if eh_separacao_lote_id:
                # Busca por separacao_lote_id (formato: LOTE-xxx, CLAUDE-xxx, etc.)
                pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
            else:
                # Se são IDs numéricos, converter para string e buscar por num_pedido
                pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()

            if not pedidos:
                flash("Nenhum pedido encontrado!", "warning")
                return redirect(url_for("pedidos.lista_pedidos"))

            # ✅ VALIDAÇÃO: Verifica se todos os pedidos são FOB
            pedidos_nao_fob = []
            for pedido in pedidos:
                if not pedido.rota or pedido.rota.upper().strip() != 'FOB':
                    pedidos_nao_fob.append(f"Pedido {pedido.num_pedido} (rota: {pedido.rota or 'N/A'})")

            if pedidos_nao_fob:
                flash(f"Os seguintes pedidos não são FOB: {', '.join(pedidos_nao_fob)}. Apenas pedidos com rota 'FOB' podem usar este embarque.", "error")
                return redirect(url_for("pedidos.lista_pedidos"))

            # ✅ TODOS SÃO FOB: Procede com criação do embarque

            # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
            # A normalização já deve estar presente na VIEW ou será feita em memória se necessário

            # Busca ou cria a transportadora "FOB - COLETA"
            from app.transportadoras.models import Transportadora
            transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
        
            if not transportadora_fob:
                # Cria a transportadora FOB - COLETA se não existir
                transportadora_fob = Transportadora(
                    razao_social="FOB - COLETA",
                    cnpj="00000000000000",  # CNPJ fictício
                    cidade="FOB",
                    uf="SP",
                    optante=False,
                    condicao_pgto="FOB"
                )
                db.session.add(transportadora_fob)
                db.session.flush()  # Para obter o ID

            # Importa as classes necessárias

            # Calcula totais dos pedidos
            peso_total = sum(p.peso_total or 0 for p in pedidos)
            valor_total = sum(p.valor_saldo_total or 0 for p in pedidos)
            pallet_total = sum(p.pallet_total or 0 for p in pedidos)

            # ✅ CRIA O EMBARQUE FOB (sem cotação, sem tabela)
            embarque = Embarque(
                numero=obter_proximo_numero_embarque(),
                transportadora_id=transportadora_fob.id,
                status='ativo',
                tipo_cotacao='FOB',  # Tipo especial para FOB
                valor_total=valor_total,
                pallet_total=pallet_total,
                peso_total=peso_total,
                tipo_carga='FOB',  # Tipo especial para FOB
                cotacao_id=None,  # ✅ SEM COTAÇÃO
                modalidade=None,  # ✅ SEM MODALIDADE
                # ✅ SEM DADOS DE TABELA (todos None/0)
                tabela_nome_tabela=None,
                tabela_frete_minimo_valor=None,
                tabela_valor_kg=None,
                tabela_percentual_valor=None,
                tabela_frete_minimo_peso=None,
                tabela_icms=None,
                tabela_percentual_gris=None,
                tabela_pedagio_por_100kg=None,
                tabela_valor_tas=None,
                tabela_percentual_adv=None,
                tabela_percentual_rca=None,
                tabela_valor_despacho=None,
                tabela_valor_cte=None,
                tabela_icms_incluso=None,
                icms_destino=None,
                transportadora_optante=None,
                criado_por='Sistema'
            )
            db.session.add(embarque)
            db.session.flush()  # Para obter o ID do embarque

            # Cria itens do embarque
            for pedido in pedidos:
                # ✅ Resolve cidade/UF real de entrega (corrige RED que gravava Guarulhos)
                nome_cidade_correto, uf_correto = LocalizacaoService.obter_cidade_destino_embarque(pedido)
            
                # Prepara dados vazios para EmbarqueItem (FOB não usa tabela)
                dados_vazio = TabelaFreteManager.preparar_cotacao_vazia()
            
                embarque_item = EmbarqueItem(
                    embarque_id=embarque.id,
                    separacao_lote_id=pedido.separacao_lote_id,
                    cnpj_cliente=pedido.cnpj_cpf,
                    cliente=pedido.raz_social_red,
                    pedido=pedido.num_pedido,
                    nota_fiscal=pedido.nf,
                    protocolo_agendamento=str(pedido.protocolo) if pedido.protocolo else '',
                    data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                    peso=pedido.peso_total or 0,
                    valor=pedido.valor_saldo_total or 0,
                    pallets=pedido.pallet_total,  # ✅ Adiciona pallets reais do pedido
                    uf_destino=uf_correto,
                    cidade_destino=nome_cidade_correto,
                    cotacao_id=None,  # SEM COTAÇÃO para FOB
                    volumes=None  # Deixa volumes em branco para preenchimento manual
                    # ✅ SEM DADOS DE TABELA (FOB não usa tabelas)
                )
                # Atribui campos vazios usando TabelaFreteManager
                TabelaFreteManager.atribuir_campos_objeto(embarque_item, dados_vazio)
                embarque_item.icms_destino = None
                db.session.add(embarque_item)

            # ✅ CORRIGIDO: Criar cotação FOB SEMPRE (fora do loop)
            # FOB precisa de cotacao_id para que status_calculado retorne "COTADO"
            from app.cotacao.models import Cotacao
            dados_fob = TabelaFreteManager.preparar_cotacao_fob()

            cotacao_fob = Cotacao(
                usuario_id=1,  # Sistema
                transportadora_id=transportadora_fob.id,
                status='Fechado',
                data_criacao=agora_utc_naive(),
                data_fechamento=agora_utc_naive(),
                tipo_carga='FOB',
                valor_total=valor_total,
                peso_total=peso_total,
                **dados_fob  # Desempacota todos os campos FOB
            )
            db.session.add(cotacao_fob)
            db.session.flush()

            # Atualiza o embarque com a cotação FOB
            embarque.cotacao_id = cotacao_fob.id

            # Commit embarque e cotação antes de atualizar separações
            db.session.commit()

            # ✅ CORRIGIDO: Atualizar separações DIRETAMENTE (mais seguro que via VIEW)
            lote_ids = [p.separacao_lote_id for p in pedidos if p.separacao_lote_id]

            if lote_ids:
                # Busca separações diretamente na tabela
                separacoes = Separacao.query.filter(
                    Separacao.separacao_lote_id.in_(lote_ids)
                ).all()

                # Atualiza cada separação via ORM (dispara event listeners)
                for sep in separacoes:
                    sep.cotacao_id = cotacao_fob.id
                    sep.nf_cd = False

                db.session.commit()
                # Status será calculado automaticamente como COTADO pelo status_calculado

            flash(f"Embarque FOB #{embarque.numero} criado com sucesso! Transportadora: FOB - COLETA", "success")
            return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar embarque FOB: {str(e)}", "error")
            return redirect(url_for("pedidos.lista_pedidos"))
