"""CotacaoRapidaService — cotacao de frete CarVia por MODELO de moto (efemera).

Wrapper sobre `CarviaTabelaService.cotar_carvia` para a tela "Cotacao Rapida":

- recebe itens `[{modelo_id, quantidade}]` e AGRUPA por categoria, porque
  `cotar_carvia` precifica por `categoria_id` (preco fixo por unidade em
  `CarviaPrecoCategoriaMoto`), nao por modelo;
- re-expande o valor por MODELO — cada modelo herda o `valor_unitario` da sua
  categoria naquela tabela (valor por modelo = unitario x qtd; total da opcao =
  soma, que coincide com o `valor_frete` do motor);
- AVISA (decisao do usuario: "avisar e pular") as tabelas da rota que nao tem
  preco por categoria de moto e os modelos sem categoria/sem preco;
- monta o historico das ultimas N cotacoes de moto da tabela (uf_destino + nome).

NAO persiste nada — a cotacao rapida e efemera. `uf_origem` fixo SP.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.carvia.models import CarviaCotacaoRapidaPublica

from app import db

logger = logging.getLogger(__name__)

UF_ORIGEM_PADRAO = 'SP'
HISTORICO_LIMITE = 5


class CotacaoRapidaService:
    """Orquestra a Cotacao Rapida de moto (efemera) reusando o motor CarVia."""

    # ------------------------------------------------------------------ #
    # Catalogo (form + injecao no prompt LLM)
    # ------------------------------------------------------------------ #
    def listar_modelos(self) -> List[Dict]:
        """Modelos ativos com a categoria (para o <select> do form e o prompt)."""
        from sqlalchemy.orm import joinedload
        from app.carvia.models import CarviaModeloMoto

        modelos = (
            CarviaModeloMoto.query
            .options(joinedload(CarviaModeloMoto.categoria))
            .filter_by(ativo=True)
            .order_by(CarviaModeloMoto.nome.asc())
            .all()
        )
        return [
            {
                'id': m.id,
                'nome': m.nome,
                'categoria_id': m.categoria_moto_id,
                'categoria_nome': m.categoria.nome if m.categoria else None,
            }
            for m in modelos
        ]

    # ------------------------------------------------------------------ #
    # Cotacao
    # ------------------------------------------------------------------ #
    def cotar(
        self,
        itens: List[Dict],
        uf_destino: str,
        cidade_destino: Optional[str] = None,
        cnpj_cliente: Optional[str] = None,
        codigo_ibge: Optional[str] = None,
    ) -> Dict:
        """Cota a lista de motos para o destino e devolve opcoes + historico.

        Args:
            itens: `[{'modelo_id': int, 'quantidade': int}, ...]`
            uf_destino: UF do destino (2 chars).
            cidade_destino: nome da cidade (filtra `CarviaCidadeAtendida`).
            cnpj_cliente: opcional, resolve tabela de grupo de cliente.

        Returns:
            dict com `opcoes`, `historicos`, `avisos`, `modelos_sem_categoria`,
            `itens` (resumo) e `regiao`.
        """
        avisos: List[str] = []
        uf_destino = (uf_destino or '').strip().upper()

        # 0. CEP -> IBGE -> Cidade Atendida: o IBGE e a chave canonica de
        # CarviaCidadeAtendida. Resolve a cidade PELO IBGE (o nome do ViaCEP pode
        # divergir do cadastrado por hifen/acento/grafia — ex. BIRITIBA-MIRIM vs
        # BIRITIBA MIRIM), garantindo o match em buscar_cidade_unificada. Tambem
        # preenche a UF quando so o CEP/IBGE veio.
        if codigo_ibge:
            cidade_canon = self._cidade_por_ibge(codigo_ibge)
            if cidade_canon:
                cidade_destino = cidade_canon.nome
                uf_destino = (cidade_canon.uf or uf_destino).upper()

        if not uf_destino:
            return self._vazio(avisos + ['UF de destino obrigatoria.'])

        # 1. Resolver itens -> modelos -> agrupar por categoria
        itens_validos, modelos_sem_categoria, categorias_qtd = self._resolver_itens(itens)

        if not itens_validos:
            return self._vazio(
                avisos + ['Nenhum modelo de moto valido informado.'],
                modelos_sem_categoria=modelos_sem_categoria,
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
            )

        if modelos_sem_categoria:
            avisos.append(
                'Modelos sem categoria cadastrada (nao entram no calculo por '
                'moto): ' + ', '.join(modelos_sem_categoria)
            )

        if not categorias_qtd:
            return self._vazio(
                avisos + ['Nenhum modelo com categoria — nada a cotar.'],
                modelos_sem_categoria=modelos_sem_categoria,
                itens=itens_validos,
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
            )

        categorias_moto = [
            {'categoria_id': cid, 'quantidade': qtd}
            for cid, qtd in categorias_qtd.items()
        ]

        # 2. Motor CarVia (preco por categoria; peso=0 -> nunca cai no calculo por peso)
        from app.carvia.services.pricing.carvia_tabela_service import CarviaTabelaService
        svc = CarviaTabelaService()

        grupo_id = svc.resolver_grupo_por_cnpj(cnpj_cliente) if cnpj_cliente else None

        tabelas = svc.buscar_tabelas_carvia(
            uf_origem=UF_ORIGEM_PADRAO,
            uf_destino=uf_destino,
            grupo_cliente_id=grupo_id,
            cidade_destino=cidade_destino,
        )

        # Cidade informada mas SEM vinculo em CarviaCidadeAtendida: em vez de
        # zerar (footgun de "preencher campo opcional zera o resultado"), cai
        # para as tabelas da UF com aviso explicito.
        cidade_usada = cidade_destino
        if not tabelas and cidade_destino:
            tabelas_uf = svc.buscar_tabelas_carvia(
                uf_origem=UF_ORIGEM_PADRAO,
                uf_destino=uf_destino,
                grupo_cliente_id=grupo_id,
                cidade_destino=None,
            )
            if tabelas_uf:
                avisos.append(
                    f'Cidade "{cidade_destino}" nao esta em Cidades Atendidas '
                    f'(origem {UF_ORIGEM_PADRAO}); cotando por UF {uf_destino} '
                    f'(sem prazo por cidade).'
                )
                tabelas = tabelas_uf
                cidade_usada = None

        if not tabelas:
            destino = f"{cidade_destino}/{uf_destino}" if cidade_destino else uf_destino
            return self._vazio(
                avisos + [
                    f'Nenhuma tabela de frete CarVia atende {destino} '
                    f'(origem {UF_ORIGEM_PADRAO}). Verifique o cadastro de '
                    f'Cidades Atendidas.'
                ],
                modelos_sem_categoria=modelos_sem_categoria,
                itens=itens_validos,
                uf_destino=uf_destino,
                cidade_destino=cidade_destino,
            )

        opcoes_motor = svc.cotar_carvia(
            peso=0,
            valor_mercadoria=0,
            uf_origem=UF_ORIGEM_PADRAO,
            uf_destino=uf_destino,
            cidade_destino=cidade_usada,
            cnpj_cliente=cnpj_cliente,
            categorias_moto=categorias_moto,
        )

        # 3. Avisar tabelas puladas (sem preco por categoria de moto)
        ids_cotados = {op['tabela_carvia_id'] for op in opcoes_motor}
        for t in tabelas:
            if t.id not in ids_cotados:
                avisos.append(
                    f'Tabela "{t.nome_tabela}" ({t.tipo_carga}) sem preco por '
                    f'categoria de moto cadastrado — nao cotada.'
                )

        # 4. Re-expandir cada opcao por MODELO
        opcoes = [self._expandir_por_modelo(op, itens_validos) for op in opcoes_motor]

        # 5. Historico por nome_tabela distinto exibido
        historicos = {}
        for nome_tabela in {op['tabela_nome'] for op in opcoes}:
            historicos[nome_tabela] = self.historico_por_tabela(nome_tabela, uf_destino)

        return {
            'ok': True,
            'opcoes': opcoes,
            'historicos': historicos,
            'avisos': avisos,
            'modelos_sem_categoria': modelos_sem_categoria,
            'itens': itens_validos,
            'regiao': {'uf_destino': uf_destino, 'cidade_destino': cidade_destino},
        }

    # ------------------------------------------------------------------ #
    # Historico
    # ------------------------------------------------------------------ #
    def historico_por_tabela(
        self, nome_tabela: str, uf_destino: str, limit: int = HISTORICO_LIMITE
    ) -> List[Dict]:
        """Ultimas N cotacoes de MOTO para a tabela (uf_destino + nome_tabela).

        Exclui CANCELADO/RECUSADO (preco rejeitado nao serve de referencia).
        valor_por_moto = valor da cotacao / total de motos (cotacoes manuais sem
        `tabela_carvia_id` ficam de fora — INNER JOIN). Destinatario = endereco
        de destino (razao social + cidade), com fallback no cliente contratante.
        """
        from app.carvia.models import CarviaCotacao, CarviaTabelaFrete

        cotacoes = (
            db.session.query(CarviaCotacao)
            .join(
                CarviaTabelaFrete,
                CarviaCotacao.tabela_carvia_id == CarviaTabelaFrete.id,
            )
            .filter(
                CarviaTabelaFrete.nome_tabela == nome_tabela,
                CarviaTabelaFrete.uf_destino == uf_destino.upper(),
                CarviaCotacao.tipo_material == 'MOTO',
                CarviaCotacao.status.notin_(['CANCELADO', 'RECUSADO']),
            )
            .order_by(CarviaCotacao.data_cotacao.desc())
            .limit(limit)
            .all()
        )

        out = []
        for c in cotacoes:
            qtd = c.qtd_total_motos or 0
            # `is not None` (nao `or`): Decimal('0.00') e falsy mas e valor valido.
            valor = next(
                (v for v in (c.valor_final_aprovado, c.valor_descontado,
                             c.valor_manual, c.valor_tabela) if v is not None),
                None,
            )
            valor_f = float(valor) if valor is not None else None
            valor_por_moto = (valor_f / qtd) if (valor_f is not None and qtd) else None
            out.append({
                'numero_cotacao': c.numero_cotacao,
                'data': c.data_cotacao,
                'qtd_motos': qtd,
                'valor_total': valor_f,
                'valor_por_moto': round(valor_por_moto, 2) if valor_por_moto is not None else None,
                'destinatario': self._destinatario(c),
                'status': c.status,
            })
        return out

    # ------------------------------------------------------------------ #
    # Persistencia da tela PUBLICA (sem login)
    # ------------------------------------------------------------------ #
    def registrar_cotacao_publica(self, resultado, *, solicitante_nome,
                                  cnpj_cliente=None, codigo_ibge=None,
                                  ip=None, user_agent=None) -> "CarviaCotacaoRapidaPublica":
        """Grava 1 snapshot da cotacao feita na tela publica. Retorna o registro.

        Chamar so quando `resultado['opcoes']`. NAO faz commit por si — o caller
        decide (a rota faz commit). Deriva valor_total_min/qtd_total_motos.
        """
        from app.carvia.models import CarviaCotacaoRapidaPublica

        opcoes = resultado.get('opcoes') or []
        itens = resultado.get('itens') or []
        regiao = resultado.get('regiao') or {}

        valores = [o.get('valor_total') for o in opcoes if o.get('valor_total') is not None]
        valor_total_min = min(valores) if valores else None
        qtd_total_motos = sum(int(i.get('quantidade') or 0) for i in itens) if itens else None

        registro = CarviaCotacaoRapidaPublica(
            solicitante_nome=(solicitante_nome or '').strip()[:160],
            cnpj_cliente=(cnpj_cliente or None),
            uf_destino=(regiao.get('uf_destino') or '')[:2],
            cidade_destino=(regiao.get('cidade_destino') or None),
            codigo_ibge=(str(codigo_ibge)[:7] if codigo_ibge else None),
            itens=itens,
            opcoes=opcoes,
            valor_total_min=valor_total_min,
            qtd_total_motos=qtd_total_motos,
            ip_solicitante=((ip or '')[:45] or None),
            user_agent=((user_agent or '')[:255] or None),
        )
        db.session.add(registro)
        db.session.flush()
        return registro

    def listar_cotacoes_publicas(self, limit: int = 20) -> List[Dict]:
        """Ultimas N cotacoes da tela publica (mais recentes primeiro)."""
        from app.carvia.models import CarviaCotacaoRapidaPublica

        regs = (
            CarviaCotacaoRapidaPublica.query
            .order_by(CarviaCotacaoRapidaPublica.criado_em.desc(),
                      CarviaCotacaoRapidaPublica.id.desc())
            .limit(limit)
            .all()
        )
        out = []
        for r in regs:
            destino = f"{r.cidade_destino}/{r.uf_destino}" if r.cidade_destino else r.uf_destino
            out.append({
                'id': r.id,
                'criado_em': r.criado_em,
                'solicitante_nome': r.solicitante_nome,
                'cnpj_cliente': r.cnpj_cliente,
                'destino': destino,
                'uf_destino': r.uf_destino,
                'cidade_destino': r.cidade_destino,
                'qtd_total_motos': r.qtd_total_motos,
                'valor_total_min': float(r.valor_total_min) if r.valor_total_min is not None else None,
                'opcoes': r.opcoes or [],
            })
        return out

    @staticmethod
    def _cidade_por_ibge(codigo_ibge):
        """Cidade canonica (DB local) pelo codigo IBGE — chave robusta vinda do CEP."""
        from app.localidades.models import Cidade
        return Cidade.query.filter_by(codigo_ibge=str(codigo_ibge)).first()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolver_itens(self, itens):
        """itens crus -> (itens_validos, modelos_sem_categoria, categorias_qtd)."""
        from app.carvia.models import CarviaModeloMoto

        # Consolida quantidades por modelo_id (mesmo modelo repetido soma).
        qtd_por_modelo = defaultdict(int)
        for item in itens or []:
            try:
                mid = int(item.get('modelo_id'))
                qtd = int(item.get('quantidade', 0))
            except (TypeError, ValueError):
                continue
            if mid and qtd > 0:
                qtd_por_modelo[mid] += qtd

        if not qtd_por_modelo:
            return [], [], {}

        modelos = (
            CarviaModeloMoto.query
            .filter(CarviaModeloMoto.id.in_(list(qtd_por_modelo.keys())))
            .all()
        )
        modelos_map = {m.id: m for m in modelos}

        itens_validos = []
        modelos_sem_categoria = []
        categorias_qtd = defaultdict(int)

        for mid, qtd in qtd_por_modelo.items():
            modelo = modelos_map.get(mid)
            if not modelo:
                continue
            cat_nome = modelo.categoria.nome if modelo.categoria_moto_id and modelo.categoria else None
            itens_validos.append({
                'modelo_id': modelo.id,
                'modelo_nome': modelo.nome,
                'categoria_id': modelo.categoria_moto_id,
                'categoria_nome': cat_nome,
                'quantidade': qtd,
            })
            if modelo.categoria_moto_id:
                categorias_qtd[modelo.categoria_moto_id] += qtd
            else:
                modelos_sem_categoria.append(modelo.nome)

        return itens_validos, modelos_sem_categoria, dict(categorias_qtd)

    @staticmethod
    def _expandir_por_modelo(opcao, itens_validos):
        """Re-expande uma opcao (preco por categoria) em linhas por MODELO."""
        breakdown = (opcao.get('detalhes') or {}).get('breakdown') or []
        valor_por_categoria = {b['categoria_id']: b['valor_unitario'] for b in breakdown}

        modelos_linha = []
        modelos_sem_preco = []
        total = 0.0

        for item in itens_validos:
            cat_id = item['categoria_id']
            qtd = item['quantidade']
            if cat_id in valor_por_categoria:
                vu = float(valor_por_categoria[cat_id])
                vt = vu * qtd
                total += vt
                modelos_linha.append({
                    'modelo_nome': item['modelo_nome'],
                    'categoria_nome': item['categoria_nome'],
                    'quantidade': qtd,
                    'valor_unitario': round(vu, 2),
                    'valor_total': round(vt, 2),
                    'sem_preco': False,
                })
            else:
                # categoria do modelo nao tem preco NESTA tabela
                modelos_linha.append({
                    'modelo_nome': item['modelo_nome'],
                    'categoria_nome': item['categoria_nome'],
                    'quantidade': qtd,
                    'valor_unitario': None,
                    'valor_total': None,
                    'sem_preco': True,
                })
                if item['categoria_id'] is not None:
                    modelos_sem_preco.append(item['modelo_nome'])

        return {
            'tabela_carvia_id': opcao['tabela_carvia_id'],
            'tabela_nome': opcao['tabela_nome'],
            'tipo_carga': opcao['tipo_carga'],
            'modalidade': opcao['modalidade'],
            'grupo_cliente': opcao.get('grupo_cliente'),
            'lead_time': opcao.get('lead_time'),
            'valor_total': round(total, 2),
            'modelos': modelos_linha,
            'modelos_sem_preco': modelos_sem_preco,
        }

    @staticmethod
    def _destinatario(cotacao):
        """Nome + cidade/UF do destino da cotacao (fallback no cliente)."""
        endereco = cotacao.endereco_destino
        nome = None
        if endereco is not None:
            nome = getattr(endereco, 'razao_social', None)
        if not nome and cotacao.cliente is not None:
            nome = getattr(cotacao.cliente, 'nome_comercial', None)

        cidade = cotacao.entrega_cidade or (
            getattr(endereco, 'fisico_cidade', None) if endereco is not None else None
        )
        uf = cotacao.entrega_uf or (
            getattr(endereco, 'fisico_uf', None) if endereco is not None else None
        )

        return {
            'nome': nome or '—',
            'cidade': cidade,
            'uf': uf,
        }

    @staticmethod
    def _vazio(avisos, modelos_sem_categoria=None, itens=None,
               uf_destino=None, cidade_destino=None):
        return {
            'ok': False,
            'opcoes': [],
            'historicos': {},
            'avisos': avisos,
            'modelos_sem_categoria': modelos_sem_categoria or [],
            'itens': itens or [],
            'regiao': {'uf_destino': uf_destino, 'cidade_destino': cidade_destino},
        }
