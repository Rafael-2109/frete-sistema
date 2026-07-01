"""
Faturamento diario via Teams
=============================

Gera uma IMAGEM (PNG) do faturamento do MES CORRENTE e a envia, de forma
proativa, no Teams. Destino padrao: o GRUPO "Financeiro - Nacom Goya"
(DEFAULT_CONVERSATION_ID); com fallback para a conversa 1:1 do destinatario
(Marcus) quando o grupo nao esta definido (env CONVERSATION_ID vazia).

Acionado pelo scheduler de seg a sex as 6h (ver
`app/scheduler/sincronizacao_incremental_definitiva.py`).

Fonte/filtro (validado contra a planilha manual do Marcus, dif ~1% = NFs
canceladas/ajustadas apos a "foto" manual):
  - modelo: account.move.line
  - move_id.company_id IN [1, 4]      (FB=1, CD=4)
  - move_id.state = 'posted'          (nota lancada/autorizada -> exclui canceladas)
  - move_id.l10n_br_tipo_pedido = 'venda'  (somente vendas)
  - display_type = 'product'          (so linhas de produto)
  - soma price_total, agrupado por dia (campo `date`)

Entrega (Jeito A — sem tocar a Azure Function): imagem salva no S3 (presigned
URL) + mensagem markdown enviada via POST /api/notify (mesma ponte da entrega
proativa do bot). Se o Teams nao renderizar a imagem inline, a mensagem traz o
total em texto + link para abrir a imagem.
"""
import io
import logging
import os
from datetime import date, timedelta

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Empresas do relatorio (IDS_FIXOS.md): FB=1, CD=4
COMPANIES_FATURAMENTO = [1, 4]
# Destinatario 1:1 (fallback): Marcus Lima (usuarios.id=18). Override por env.
DEFAULT_USER_ID = int(os.environ.get("FATURAMENTO_DIARIO_TEAMS_USER_ID", "18"))

# Destino preferencial: GRUPO "Financeiro - Nacom Goya" no Teams (groupChat,
# conversation_id capturado em 25/06/2026 quando o Agente foi chamado no grupo).
# Quando definido, o envio vai para ESTE grupo em vez da conversa 1:1 do usuario.
# Para voltar ao 1:1, setar a env como string vazia.
DEFAULT_CONVERSATION_ID = os.environ.get(
    "FATURAMENTO_DIARIO_TEAMS_CONVERSATION_ID",
    "19:6fb2c48f46ba4776a3fd31d9182bd688@thread.v2",
)

MES_ABREV = ['', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN',
             'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

# TTL da presigned URL: 7 dias (maximo do SigV4). A imagem precisa continuar
# acessivel se o usuario abrir a mensagem horas/dias depois.
_URL_TTL = 7 * 24 * 3600


# ──────────────────────────────────────────────────────────────────
# 1) Dados — faturamento do mes por dia (Odoo)
# ──────────────────────────────────────────────────────────────────
def buscar_faturamento_mes(ano: int, mes: int) -> tuple[list[tuple[date, int]], int]:
    """Retorna ([(dia, valor_arredondado), ...], total_mes) do mes informado.

    Pagina o search_read por offset (sem teto fixo — nao trunca meses de alto
    volume) e agrega por dia em memoria. `date` vem em ISO 'YYYY-MM-DD', sem
    depender do locale do label de agrupamento do read_group (por isso aqui
    nao usamos read_group).
    """
    from app.odoo.utils.connection import get_odoo_connection

    import calendar
    ini = date(ano, mes, 1).isoformat()
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1]).isoformat()
    domain = [
        ('move_id.company_id', 'in', COMPANIES_FATURAMENTO),
        ('move_id.state', '=', 'posted'),
        ('move_id.l10n_br_tipo_pedido', '=', 'venda'),
        ('display_type', '=', 'product'),
        ('date', '>=', ini), ('date', '<=', fim),
    ]
    conn = get_odoo_connection()
    registros = []
    _PAGINA = 20000
    offset = 0
    while True:
        lote = conn.search_read(
            'account.move.line', domain, ['date', 'price_total'],
            limit=_PAGINA, offset=offset,
        )
        registros.extend(lote)
        if len(lote) < _PAGINA:
            break
        offset += _PAGINA

    agg: dict[str, float] = {}
    for r in registros:
        d = r.get('date')
        if not d:
            continue
        agg[d] = agg.get(d, 0.0) + (r.get('price_total') or 0.0)

    linhas = [(date.fromisoformat(d), int(round(v))) for d, v in agg.items()]
    linhas.sort(key=lambda x: x[0])
    total = sum(v for _, v in linhas)
    return linhas, total


# ──────────────────────────────────────────────────────────────────
# 2) Imagem (Pillow) — DejaVu Sans versionada (tem acentos PT-BR)
# ──────────────────────────────────────────────────────────────────
_FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')


def _fonte(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """DejaVu Sans (versionada no modulo) — tem acentos PT-BR e roda em qualquer SO.

    Fallback para a fonte embutida do Pillow (Aileron) so se o arquivo faltar —
    a embutida NAO tem acentos (á/ê/ã viram tofu), por isso a DejaVu e versionada.
    """
    nome = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    try:
        return ImageFont.truetype(os.path.join(_FONT_DIR, nome), size)
    except Exception:
        return ImageFont.load_default(size=size)


def _br(v: int) -> str:
    return 'R$ ' + f'{int(v):,}'.replace(',', '.')


def gerar_imagem_bytes(linhas: list[tuple[date, int]], total: int,
                       ano: int, mes: int, fechamento: bool = False) -> bytes:
    """Desenha a tabela (dias do mes + total) e devolve o PNG em bytes."""
    AZUL = (31, 78, 120)
    BRANCO = (255, 255, 255)
    PRETO = (40, 40, 40)
    CINZA = (120, 120, 120)
    ZEBRA = (242, 246, 252)
    AMARELO = (255, 230, 153)
    LINHA = (210, 210, 210)

    f_titulo = _fonte(28, bold=True)
    f_sub = _fonte(14)
    f_head = _fonte(17, bold=True)
    f_cel = _fonte(18)
    f_tot = _fonte(20, bold=True)

    W, pad, top = 560, 24, 18
    h_titulo, h_sub, h_head, h_lin, h_tot = 42, 28, 40, 34, 46
    n = len(linhas)
    H = top + h_titulo + h_sub + 8 + h_head + n * h_lin + h_tot + pad

    img = Image.new('RGB', (W, H), BRANCO)
    dr = ImageDraw.Draw(img)
    rotulo = f'{MES_ABREV[mes]}/{ano}'
    from app.utils.timezone import agora_utc_naive
    hoje = agora_utc_naive().strftime('%d/%m/%Y')

    # Titulo + subtitulo
    dr.text((pad, top), 'FATURAMENTO', font=f_titulo, fill=AZUL)
    subtitulo = ('CD + FB · somente vendas · FECHAMENTO do mês' if fechamento
                 else f'CD + FB · somente vendas · atualizado em {hoje}')
    dr.text((pad, top + h_titulo + 4), subtitulo, font=f_sub, fill=CINZA)

    x0, x1 = pad, W - pad
    col_val = x1 - 12
    y = top + h_titulo + h_sub + 8

    # Cabecalho
    dr.rectangle([x0, y, x1, y + h_head], fill=AZUL)
    dr.text((x0 + 14, y + 11), 'Data', font=f_head, fill=BRANCO)
    t = 'Faturamento (R$)'
    dr.text((col_val - dr.textlength(t, font=f_head), y + 11), t, font=f_head, fill=BRANCO)
    y += h_head

    # Dias
    for i, (d, v) in enumerate(linhas):
        if i % 2 == 1:
            dr.rectangle([x0, y, x1, y + h_lin], fill=ZEBRA)
        dr.text((x0 + 14, y + 7), d.strftime('%d/%m/%Y'), font=f_cel, fill=PRETO)
        s = _br(v)
        dr.text((col_val - dr.textlength(s, font=f_cel), y + 7), s, font=f_cel, fill=PRETO)
        dr.line([x0, y + h_lin, x1, y + h_lin], fill=LINHA, width=1)
        y += h_lin

    # Total do mes
    dr.rectangle([x0, y, x1, y + h_tot], fill=AMARELO)
    rotulo_tot = f'TOTAL DO MÊS ({rotulo})'
    dr.text((x0 + 14, y + 12), rotulo_tot, font=f_tot, fill=PRETO)
    s = _br(total)
    dr.text((col_val - dr.textlength(s, font=f_tot), y + 12), s, font=f_tot, fill=PRETO)

    dr.rectangle([x0, top + h_titulo + h_sub + 8, x1, y + h_tot], outline=AZUL, width=2)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# 3) Destinatario — conversation_reference da conversa/grupo no Teams
# ──────────────────────────────────────────────────────────────────
def _conversation_reference(conversation_id: str | None = None,
                            user_id: int | None = None):
    """Reference (mais recente) de uma conversa do Teams.

    Prioriza um `conversation_id` especifico (ex.: o grupo "Financeiro - Nacom
    Goya"). Sem ele, cai na conversa 1:1 (personal, 'a:%') mais recente do
    `user_id` e, por fim, em qualquer conversa do usuario.
    """
    from app.teams.models import TeamsTask

    base = TeamsTask.query.filter(TeamsTask.conversation_reference.isnot(None))
    if conversation_id:
        task = (base.filter(TeamsTask.conversation_id == conversation_id)
                    .order_by(TeamsTask.created_at.desc()).first())
        return task.conversation_reference if task else None

    base = base.filter(TeamsTask.user_id == user_id)
    task = (base.filter(TeamsTask.conversation_id.like('a:%'))
                .order_by(TeamsTask.created_at.desc()).first()
            or base.order_by(TeamsTask.created_at.desc()).first())
    return task.conversation_reference if task else None


# ──────────────────────────────────────────────────────────────────
# 3.5) Periodo — mes corrente vs FECHAMENTO do mes anterior na virada
# ──────────────────────────────────────────────────────────────────
def _primeiro_dia_util(ano: int, mes: int) -> date:
    """Primeiro dia UTIL (seg-sex) do mes."""
    d = date(ano, mes, 1)
    while d.weekday() >= 5:  # 5=sab, 6=dom
        d += timedelta(days=1)
    return d


def _resolver_periodo(hoje: date) -> tuple[int, int, bool]:
    """Decide qual mes o relatorio mostra.

    Na VIRADA DE MES (primeiro dia util do mes) -> mes ANTERIOR (fechamento),
    para o Marcus receber o fechamento do mes que terminou. Nos demais dias ->
    mes corrente. Retorna (ano, mes, fechamento).
    """
    if hoje == _primeiro_dia_util(hoje.year, hoje.month):
        anterior = date(hoje.year, hoje.month, 1) - timedelta(days=1)  # ultimo dia do mes anterior
        return anterior.year, anterior.month, True
    return hoje.year, hoje.month, False


# ──────────────────────────────────────────────────────────────────
# 4) Orquestracao — gera, sobe S3 e envia no Teams
# ──────────────────────────────────────────────────────────────────
def enviar_faturamento_diario_teams(conversation_id: str | None = None,
                                    user_id: int | None = None,
                                    dry_run: bool = False,
                                    ano: int | None = None, mes: int | None = None,
                                    fechamento: bool | None = None) -> dict:
    """Gera a imagem do mes corrente e envia no Teams (entrega proativa).

    Periodo automatico (ver `_resolver_periodo`): virada de mes -> fechamento do
    mes anterior; demais dias -> mes corrente. Para REENVIAR um mes especifico
    manualmente, passe `ano`, `mes` (e `fechamento=True` para rotular como fechado).

    Destino: por padrao o GRUPO "Financeiro - Nacom Goya"
    (DEFAULT_CONVERSATION_ID). Passe `conversation_id` para outra conversa, ou
    deixe o destino vazio (env "") para cair na conversa 1:1 do `user_id`.

    Args:
        conversation_id: conversa/grupo de destino. Default = grupo Financeiro.
        user_id: destinatario 1:1 (fallback quando nao ha conversation_id).
        dry_run: se True, gera tudo mas NAO posta no Teams (para teste manual).

    Returns:
        dict com {ok, motivo, total, url, dias, dry_run}.
    """
    from app.utils.timezone import agora_utc_naive

    conversation_id = conversation_id or (DEFAULT_CONVERSATION_ID or None)
    user_id = user_id or DEFAULT_USER_ID
    hoje = agora_utc_naive().date()
    if ano and mes:
        # override manual (ex.: reenviar o fechamento de um mes especifico)
        fechamento = bool(fechamento)
    else:
        ano, mes, fechamento = _resolver_periodo(hoje)

    # 1) dados + imagem (mes corrente; na virada de mes, fechamento do anterior)
    linhas, total = buscar_faturamento_mes(ano, mes)
    if not linhas:
        logger.warning(f"[FAT-DIARIO] Sem faturamento em {mes:02d}/{ano} — nada a enviar")
        return {"ok": False, "motivo": "sem_dados", "dias": 0}
    png = gerar_imagem_bytes(linhas, total, ano, mes, fechamento=fechamento)

    # 2) sobe no S3 (presigned URL)
    from app.utils.file_storage import get_file_storage
    fs = get_file_storage()
    buf = io.BytesIO(png)
    buf.name = f"faturamento_{ano}{mes:02d}_{hoje.isoformat()}.png"
    caminho = fs.save_file(buf, folder='faturamento_diario',
                           filename=f"faturamento_{ano}{mes:02d}_{hoje.isoformat()}.png")
    url = fs.get_presigned_url(caminho, expires_in=_URL_TTL) if caminho else None

    rotulo = f'{MES_ABREV[mes]}/{ano}'
    resultado = {
        "ok": False, "total": total, "dias": len(linhas),
        "url": url, "caminho": caminho, "dry_run": dry_run, "rotulo": rotulo,
    }

    if not url:
        logger.error(f"[FAT-DIARIO] Falha ao gerar URL da imagem (caminho={caminho})")
        resultado["motivo"] = "sem_url_s3"
        return resultado

    # 3) mensagem (imagem inline via markdown + total em texto como fallback)
    if fechamento:
        titulo_msg = f"📊 **Fechamento do mês — {rotulo}**"
        linha_total = f"Total faturado em {rotulo} (mês fechado): **{_br(total)}**"
    else:
        titulo_msg = f"📊 **Faturamento do mês — {rotulo}**"
        linha_total = f"Total do mês até {hoje.strftime('%d/%m/%Y')}: **{_br(total)}**"
    mensagem = (
        f"{titulo_msg}\n\n"
        f"{linha_total}\n\n"
        f"![Faturamento {rotulo}]({url})\n\n"
        f"_Se a imagem não aparecer, [clique aqui para abrir]({url})._"
    )

    if dry_run:
        resultado.update(ok=True, motivo="dry_run", mensagem=mensagem)
        return resultado

    # 4) destinatario + envio proativo (reusa a ponte da entrega do bot)
    reference = _conversation_reference(conversation_id=conversation_id, user_id=user_id)
    if not reference:
        alvo = f"conversation_id={conversation_id}" if conversation_id else f"user_id={user_id}"
        logger.error(f"[FAT-DIARIO] Sem conversation_reference para {alvo}")
        resultado["motivo"] = "sem_conversa_teams"
        return resultado

    from app.teams.proactive import _function_url, _post_notify
    base_url = _function_url()
    if not base_url:
        resultado["motivo"] = "sem_function_url"
        return resultado

    payload = {
        "tipo": "final",
        "task_id": f"fatdiario-{hoje.isoformat()}",
        "status": "completed",
        "resposta": mensagem,
        "resposta_card": None,
        "conversation_reference": reference,
    }
    api_key = os.environ.get("TEAMS_BOT_API_KEY", "")
    try:
        _post_notify(base_url, payload, api_key)
    except Exception as e:
        logger.error(f"[FAT-DIARIO] POST /api/notify falhou: {e}")
        resultado["motivo"] = f"post_falhou: {e}"
        return resultado

    destino = f"grupo {conversation_id}" if conversation_id else f"user_id={user_id}"
    logger.info(
        f"[FAT-DIARIO] Enviado para {destino}: {rotulo} "
        f"total={_br(total)} dias={len(linhas)}"
    )
    resultado.update(ok=True, motivo="enviado", destino=destino)
    return resultado
