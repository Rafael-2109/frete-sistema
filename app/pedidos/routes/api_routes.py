"""Routes de API (JSON endpoints) para pedidos."""
from flask import request, jsonify
from flask_login import login_required, current_user

from app import db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.utils.timezone import agora_utc_naive


def register_api_routes(bp):

    @bp.route('/api/info_separacao/<string:lote_id>', methods=['GET']) # type: ignore
    @login_required
    def info_separacao(lote_id): # type: ignore
        """
        API para buscar informações detalhadas de uma separação para exibir no modal
        Retorna todos os itens da separação com suas quantidades, valores, e status
        """
        try:
            # Buscar todos os itens da separação
            itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

            if not itens:
                return jsonify({
                    'success': False,
                    'message': f'Separação {lote_id} não encontrada.'
                }), 404

            # Buscar condição de pagamento da CarteiraPrincipal
            num_pedido = itens[0].num_pedido
            carteira_item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
            cond_pgto = carteira_item.cond_pgto_pedido if carteira_item else None

            # Verificar se pedido está separado (tem separacao_impressa)
            pedido_separado = any(item.separacao_impressa for item in itens)

            # Calcular totais
            qtd_total = sum(float(item.qtd_saldo or 0) for item in itens)
            valor_total = sum(float(item.valor_saldo or 0) for item in itens)
            peso_total = sum(float(item.peso or 0) for item in itens)
            pallet_total = sum(float(item.pallet or 0) for item in itens)

            # Preparar lista de itens
            itens_list = []
            for item in itens:
                itens_list.append({
                    'id': item.id,
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': float(item.qtd_saldo or 0),
                    'valor_saldo': float(item.valor_saldo or 0),
                    'peso': float(item.peso or 0),
                    'pallet': float(item.pallet or 0),
                    'falta_item': item.falta_item,
                    'obs_separacao': item.obs_separacao
                })

            return jsonify({
                'success': True,
                'lote_id': lote_id,
                'num_pedido': num_pedido,
                'cnpj_cpf': itens[0].cnpj_cpf,
                'raz_social_red': itens[0].raz_social_red,
                'cond_pgto': cond_pgto,
                'pedido_separado': pedido_separado,
                'falta_pagamento': itens[0].falta_pagamento,
                'obs_separacao': itens[0].obs_separacao or '',  # ✅ NOVO: Observação geral do lote
                'totais': {
                    'qtd': qtd_total,
                    'valor': valor_total,
                    'peso': peso_total,
                    'pallet': pallet_total
                },
                'itens': itens_list
            })

        except Exception as e:
            print(f"[ERRO INFO SEPARAÇÃO] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao buscar informações: {str(e)}'
            }), 500


    @bp.route('/api/toggle_falta_item/<int:item_id>', methods=['POST']) # type: ignore
    @login_required
    def toggle_falta_item(item_id): # type: ignore
        """
        API para alternar o status de falta_item de um item da separação
        """
        try:
            item = db.session.get(Separacao,item_id) if item_id else None

            if not item:
                return jsonify({
                    'success': False,
                    'message': f'Item {item_id} não encontrado.'
                }), 404

            # Alternar o status
            item.falta_item = not item.falta_item
            db.session.commit()

            # Invalidar cache de contadores (ag_item mudou)
            from app.pedidos.services.counter_service import PedidosCounterService
            PedidosCounterService.invalidar_cache()

            return jsonify({
                'success': True,
                'item_id': item_id,
                'falta_item': item.falta_item
            })

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO TOGGLE FALTA ITEM] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao atualizar item: {str(e)}'
            }), 500


    @bp.route('/api/toggle_pagamento/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def toggle_pagamento(lote_id): # type: ignore
        """
        API para marcar/desmarcar pagamento realizado para todos os itens de uma separação
        """
        try:
            itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

            if not itens:
                return jsonify({
                    'success': False,
                    'message': f'Separação {lote_id} não encontrada.'
                }), 404

            # Obter o novo valor do corpo da requisição
            data = request.get_json()
            falta_pagamento = data.get('falta_pagamento', False)

            # Atualizar todos os itens
            for item in itens:
                item.falta_pagamento = falta_pagamento

            db.session.commit()

            # Invalidar cache de contadores (ag_pagamento mudou)
            from app.pedidos.services.counter_service import PedidosCounterService
            PedidosCounterService.invalidar_cache()

            return jsonify({
                'success': True,
                'lote_id': lote_id,
                'falta_pagamento': falta_pagamento
            })

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO TOGGLE PAGAMENTO] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao atualizar pagamento: {str(e)}'
            }), 500


    @bp.route('/api/salvar_obs_separacao/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def salvar_obs_separacao(lote_id): # type: ignore
        """
        API para salvar observações da separação
        Atualiza todos os itens do lote com a mesma observação
        """
        # Guard: pedidos CarVia
        if str(lote_id).startswith('CARVIA-'):
            return jsonify({'success': False, 'message': 'Pedidos CarVia nao editaveis aqui.'}), 400

        try:
            data = request.get_json()
            obs_separacao = data.get('obs_separacao', '').strip()

            # Buscar todos os itens da separação
            itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

            if not itens:
                return jsonify({
                    'success': False,
                    'message': f'Separação {lote_id} não encontrada.'
                }), 404

            # Atualizar observação em todos os itens do lote
            for item in itens:
                item.obs_separacao = obs_separacao if obs_separacao else None

            db.session.commit()

            return jsonify({
                'success': True,
                'lote_id': lote_id,
                'obs_separacao': obs_separacao,
                'itens_atualizados': len(itens)
            })

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO SALVAR OBS SEPARAÇÃO] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao salvar observações: {str(e)}'
            }), 500



    @bp.route('/api/pedido/<string:num_pedido>/endereco-carteira', methods=['GET']) # type: ignore
    @login_required
    def api_endereco_carteira(num_pedido): # type: ignore
        """
        API para buscar dados de endereço da CarteiraPrincipal
        """
        try:
            from app.carteira.models import CarteiraPrincipal
        
            # Buscar primeiro item da carteira para este pedido
            # (pega apenas um registro pois os dados de endereço são iguais para todo o pedido)
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).first()
        
            if not item_carteira:
                return jsonify({
                    'success': False,
                    'error': f'Pedido {num_pedido} não encontrado na carteira'
                }), 404
        
            # Preparar dados do endereço
            dados = {
                # Dados do cliente
                'raz_social': item_carteira.raz_social,
                'raz_social_red': item_carteira.raz_social_red,
                'cnpj_cpf': item_carteira.cnpj_cpf,
                'municipio': item_carteira.municipio,
                'estado': item_carteira.estado,
                'incoterm': item_carteira.incoterm,
            
                # Dados do endereço de entrega
                'empresa_endereco_ent': item_carteira.empresa_endereco_ent,
                'cnpj_endereco_ent': item_carteira.cnpj_endereco_ent,
                'cep_endereco_ent': item_carteira.cep_endereco_ent,
                'nome_cidade': item_carteira.nome_cidade,
                'cod_uf': item_carteira.cod_uf,
                'bairro_endereco_ent': item_carteira.bairro_endereco_ent,
                'rua_endereco_ent': item_carteira.rua_endereco_ent,
                'endereco_ent': item_carteira.endereco_ent,
                'telefone_endereco_ent': item_carteira.telefone_endereco_ent,
            
                # Observações
                'observ_ped_1': item_carteira.observ_ped_1,
            
                # Dados adicionais úteis
                'pedido_cliente': item_carteira.pedido_cliente,
                'vendedor': item_carteira.vendedor,
                'equipe_vendas': item_carteira.equipe_vendas,
                'cliente_nec_agendamento': item_carteira.cliente_nec_agendamento
            }
        
            return jsonify({
                'success': True,
                'dados': dados
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    @bp.route('/api/pedido/<string:num_pedido>/endereco-receita', methods=['GET']) # type: ignore
    @login_required
    def api_endereco_receita(num_pedido): # type: ignore
        """
        API fallback para buscar dados de endereço via ReceitaWS quando não encontrar na CarteiraPrincipal
        Também retorna o separacao_lote_id para permitir atualização da cidade
        """
        import requests
        import re

        try:
            from app.separacao.models import Separacao

            # Buscar CNPJ e separacao_lote_id da primeira Separacao deste pedido
            separacao = Separacao.query.filter_by(num_pedido=num_pedido).first()

            if not separacao or not separacao.cnpj_cpf:
                return jsonify({
                    'success': False,
                    'error': f'Pedido {num_pedido} não encontrado ou sem CNPJ'
                }), 404

            # Limpar CNPJ (apenas números)
            cnpj_limpo = re.sub(r'\D', '', separacao.cnpj_cpf)

            if len(cnpj_limpo) != 14:
                return jsonify({
                    'success': False,
                    'error': f'CNPJ inválido: {separacao.cnpj_cpf}'
                }), 400

            # Buscar dados na ReceitaWS
            url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}'
            response = requests.get(url, timeout=10)

            # Tratamento específico para erro 429 (Too Many Requests)
            if response.status_code == 429:
                return jsonify({
                    'success': False,
                    'error': 'Limite de consultas à ReceitaWS atingido. Tente novamente após 60 segundos.',
                    'error_code': 429
                }), 429

            if response.status_code != 200:
                return jsonify({
                    'success': False,
                    'error': f'Erro ao consultar ReceitaWS: Status {response.status_code}'
                }), response.status_code

            dados_receita = response.json()

            # Verificar se retornou erro
            if dados_receita.get('status') == 'ERROR':
                return jsonify({
                    'success': False,
                    'error': dados_receita.get('message', 'Erro desconhecido na ReceitaWS')
                }), 400

            # Preparar dados no formato esperado pelo modal
            dados = {
                # Dados do cliente
                'raz_social': dados_receita.get('nome', '-'),
                'raz_social_red': dados_receita.get('fantasia', dados_receita.get('nome', '-')),
                'cnpj_cpf': dados_receita.get('cnpj', separacao.cnpj_cpf),
                'municipio': dados_receita.get('municipio', '-'),
                'estado': dados_receita.get('uf', '-'),
                'incoterm': separacao.roteirizacao or '-',

                # Dados do endereço de entrega (mesmo endereço do CNPJ)
                'empresa_endereco_ent': dados_receita.get('fantasia', dados_receita.get('nome', '-')),
                'cnpj_endereco_ent': dados_receita.get('cnpj', separacao.cnpj_cpf),
                'cep_endereco_ent': dados_receita.get('cep', '-').replace('.', ''),
                'nome_cidade': dados_receita.get('municipio', '-'),
                'cod_uf': dados_receita.get('uf', '-'),
                'bairro_endereco_ent': dados_receita.get('bairro', '-'),
                'rua_endereco_ent': dados_receita.get('logradouro', '-'),
                'endereco_ent': dados_receita.get('numero', '-'),
                'telefone_endereco_ent': dados_receita.get('telefone', '-'),

                # Observações
                'observ_ped_1': separacao.observ_ped_1 or 'Sem observações',

                # Dados adicionais
                'pedido_cliente': separacao.pedido_cliente or '-',
                'vendedor': '-',
                'equipe_vendas': '-',
                'cliente_nec_agendamento': False,

                # IMPORTANTE: Incluir separacao_lote_id para permitir atualização
                'separacao_lote_id': separacao.separacao_lote_id
            }

            return jsonify({
                'success': True,
                'dados': dados,
                'fonte': 'receita'  # Indica que veio da ReceitaWS
            })

        except requests.Timeout:
            return jsonify({
                'success': False,
                'error': 'Timeout ao consultar ReceitaWS. Tente novamente.'
            }), 504
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    @bp.route('/api/separacao/<string:lote_id>/atualizar-cidade', methods=['POST']) # type: ignore
    @login_required
    def api_atualizar_cidade_separacao(lote_id): # type: ignore
        """
        API para atualizar a cidade de TODAS as Separacoes de um lote
        """
        try:
            from app.separacao.models import Separacao

            dados = request.get_json()
            nova_cidade = dados.get('cidade')

            if not nova_cidade:
                return jsonify({
                    'success': False,
                    'error': 'Cidade não informada'
                }), 400

            # Buscar TODAS as separações deste lote
            separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

            if not separacoes:
                return jsonify({
                    'success': False,
                    'error': f'Nenhuma separação encontrada para o lote {lote_id}'
                }), 404

            # Atualizar cidade em TODAS
            for sep in separacoes:
                sep.nome_cidade = nova_cidade

            db.session.commit()

            return jsonify({
                'success': True,
                'atualizados': len(separacoes),
                'message': f'Cidade atualizada em {len(separacoes)} registro(s)'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    @bp.route('/sincronizar-items-faturamento/<lote_id>', methods=['POST']) # type: ignore
    @login_required
    def sincronizar_items_faturamento(lote_id): # type: ignore
        """
        Sincroniza items de Separacao com FaturamentoProduto

        Busca dados reais de qtd, valor, peso e pallets do faturamento
        e atualiza a Separacao com sincronizado_nf=True
        """
        try:
            from app.pedidos.services.sincronizar_items_service import SincronizadorItemsService

            # Executar sincronização
            service = SincronizadorItemsService()
            resultado = service.sincronizar_items_faturamento(
                separacao_lote_id=lote_id,
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            return jsonify(resultado)

        except Exception as e:
            import logging
            logging.error(f"Erro ao sincronizar items do lote {lote_id}: {e}")
            return jsonify({
                'success': False,
                'separacao_lote_id': lote_id,
                'erro': str(e)
            }), 500


    @bp.route('/validar_nf/<string:numero_nf>', methods=['GET']) # type: ignore
    @login_required
    def validar_nf(numero_nf): # type: ignore
        """
        Valida se NF existe em FaturamentoProduto e retorna status

        Query params:
        - lote_id: ID do lote (opcional, para log)

        Response:
        {
            "success": true,
            "existe": true/false,
            "status": "Lançado"|"Cancelado"|"Provisório"|null,
            "sincronizado_nf": true/false
        }
        """
        from app.faturamento.models import FaturamentoProduto

        try:
            lote_id = request.args.get('lote_id', 'N/A')

            # Buscar NF em FaturamentoProduto
            faturamento = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).first()

            if faturamento:
                # NF encontrada
                status = faturamento.status_nf or 'Lançado'
                sincronizado = (status != 'Cancelado')

                print(f"[VALIDAR NF] Lote: {lote_id} | NF: {numero_nf} | Status: {status} | Sincronizado: {sincronizado}")

                return jsonify({
                    'success': True,
                    'existe': True,
                    'status': status,
                    'sincronizado_nf': sincronizado,
                    'message': f'NF encontrada com status: {status}'
                })
            else:
                # NF não encontrada
                print(f"[VALIDAR NF] Lote: {lote_id} | NF: {numero_nf} | Não encontrada")

                return jsonify({
                    'success': True,
                    'existe': False,
                    'status': None,
                    'sincronizado_nf': False,
                    'message': 'NF não encontrada no faturamento'
                })

        except Exception as e:
            print(f"[ERRO VALIDAR NF] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao validar NF: {str(e)}'
            }), 500



    @bp.route('/gravar_nf/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def gravar_nf(lote_id): # type: ignore
        """
        Valida NF em FaturamentoProduto E grava em Separacao.numero_nf

        Payload:
        {
            "numero_nf": "12345"
        }

        Response:
        {
            "success": true,
            "existe": true/false,
            "status": "Lançado"|"Cancelado"|null,
            "sincronizado_nf": true/false,
            "itens_atualizados": 3,
            "message": "..."
        }
        """
        from app.faturamento.models import FaturamentoProduto

        try:
            data = request.get_json()
            numero_nf = data.get('numero_nf', '').strip()

            if not numero_nf:
                return jsonify({
                    'success': False,
                    'message': 'Número da NF não informado'
                }), 400

            # PASSO 1: Validar NF em FaturamentoProduto
            faturamento = FaturamentoProduto.query.filter_by(
                numero_nf=numero_nf
            ).first()

            existe_faturamento = False
            status_nf = None
            sincronizado = False

            if faturamento:
                existe_faturamento = True
                status_nf = faturamento.status_nf or 'Lançado'
                sincronizado = (status_nf != 'Cancelado')

            # PASSO 2: Gravar em Separacao (TODAS as linhas do lote)
            itens_separacao = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).all()

            if not itens_separacao:
                return jsonify({
                    'success': False,
                    'message': f'Nenhum item de separação encontrado para o lote {lote_id}'
                }), 404

            # Atualizar TODOS os itens do lote
            itens_atualizados = 0
            for item in itens_separacao:
                item.numero_nf = numero_nf
                item.sincronizado_nf = sincronizado  # Marca como sincronizado apenas se NF válida

                if sincronizado:
                    item.data_sincronizacao = agora_utc_naive()

                itens_atualizados += 1

            db.session.commit()

            # PASSO 3: Log e resposta
            print(f"[GRAVAR NF] Lote: {lote_id} | NF: {numero_nf} | Existe: {existe_faturamento} | Status: {status_nf} | Sincronizado: {sincronizado} | Itens: {itens_atualizados}")

            if existe_faturamento:
                if sincronizado:
                    mensagem = f'✅ NF {numero_nf} gravada e sincronizada com sucesso! (Status: {status_nf}) - {itens_atualizados} itens atualizados'
                else:
                    mensagem = f'⚠️ NF {numero_nf} está CANCELADA. Não foi marcada como sincronizada. - {itens_atualizados} itens atualizados'
            else:
                mensagem = f'⚠️ NF {numero_nf} NÃO encontrada no faturamento, mas foi gravada para referência. - {itens_atualizados} itens atualizados'

            return jsonify({
                'success': True,
                'existe': existe_faturamento,
                'status': status_nf,
                'sincronizado_nf': sincronizado,
                'itens_atualizados': itens_atualizados,
                'message': mensagem
            })

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO GRAVAR NF] Lote: {lote_id} | Erro: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao gravar NF: {str(e)}'
            }), 500



    @bp.route('/verificar_monitoramento', methods=['POST']) # type: ignore
    @login_required
    def verificar_monitoramento(): # type: ignore
        """
        Verifica status de nf_cd em EntregaMonitorada

        Payload:
        {
            "lote_id": "LOTE-123",
            "numero_nf": "12345" (optional)
        }

        Response:
        {
            "success": true,
            "encontrado": true/false,
            "nf_cd": true/false,
            "message": "..."
        }
        """
        from app.monitoramento.models import EntregaMonitorada

        try:
            data = request.get_json()
            lote_id = data.get('lote_id')
            numero_nf = data.get('numero_nf')

            if not lote_id and not numero_nf:
                return jsonify({
                    'success': False,
                    'message': 'Informe lote_id ou numero_nf'
                }), 400

            # Buscar EntregaMonitorada
            # Prioridade 1: Por separacao_lote_id
            entrega = None
            if lote_id:
                entrega = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=lote_id
                ).first()

            # Fallback: Por numero_nf
            if not entrega and numero_nf:
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=numero_nf
                ).first()

            if entrega:
                # Encontrado
                nf_cd = bool(entrega.nf_cd)

                print(f"[VERIFICAR MONITORAMENTO] Lote: {lote_id} | NF: {numero_nf} | nf_cd: {nf_cd}")

                return jsonify({
                    'success': True,
                    'encontrado': True,
                    'nf_cd': nf_cd,
                    'message': f'Entrega encontrada (nf_cd={nf_cd})'
                })
            else:
                # Não encontrado
                print(f"[VERIFICAR MONITORAMENTO] Lote: {lote_id} | NF: {numero_nf} | Não encontrado")

                return jsonify({
                    'success': True,
                    'encontrado': False,
                    'nf_cd': False,
                    'message': 'Entrega não encontrada no monitoramento'
                })

        except Exception as e:
            print(f"[ERRO VERIFICAR MONITORAMENTO] {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao verificar monitoramento: {str(e)}'
            }), 500
