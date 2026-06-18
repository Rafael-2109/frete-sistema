/**
 * BinPacker — Algoritmo 3D Maximal Rectangles + Bottom-Left-Back para empacotamento de motos.
 *
 * Regra NAO-NEGOCIAVEL — horizontalidade:
 * - Comprimento da moto SEMPRE horizontal (eixos X ou Z do bau, nunca Y).
 * - Largura e altura intercambiaveis (moto pode ser deitada de lado), mas NUNCA "de pe".
 * - 4 orientacoes validas por moto, testadas individualmente.
 *
 * Caixas NUNCA se interpenetram (sobreposicao fisica = 0). Cada moto ocupa seu
 * volume real; o espaco livre e subtraido pelo footprint real.
 *
 * Regras de apoio fisico (empilhamento) — UNICAS CONFIGURAVEIS via options:
 * - Moto no chao (Y=0): sempre valida.
 * - Moto empilhada (Y>0): deve ter apoio suficiente embaixo.
 *   - options.minSupport: % minimo da base com apoio real (default 0.50)
 *   - options.maxOverhang: balanco maximo nas extremidades em cm (default 15)
 *   - options.maxGap: vao maximo no centro, apoiado pelos 2 lados, em cm (default 50)
 *
 * Algoritmo: Maximal Rectangles + ordenacao por altura-deitada + Bottom-Left-Back Fill
 * + validacao de suporte. (Best Short Side Fit foi abandonado: espalhava as motos,
 *  criava topos irregulares e inviabilizava empilhar — ~47% de ocupacao e instavel.)
 *
 * Dois pontos de entrada:
 *   - pack(bay, motoList, options): 1 passada gulosa, instantanea.
 *   - packOptimized(bay, motoList, options, budget): Simulated Annealing sobre a ORDEM
 *     de insercao (avaliada por pack), determinístico, acomoda mais motos no mesmo bau.
 */
;(function () {
  'use strict';

  var MAX_ITEMS = 200;
  var MIN_DIM = 5;

  // Defaults de apoio (sobrescritos por options em pack()).
  var DEFAULTS = {
    minSupport: 0.50,  // fracao minima da base com apoio para empilhar (0.10-1.0)
    maxOverhang: 15,   // cm — balanco maximo nas extremidades
    maxGap: 50,        // cm — vao maximo no centro (apoiado dos 2 lados)
  };

  function normalizeOptions(o) {
    o = o || {};
    function num(v, def) { return (typeof v === 'number' && isFinite(v)) ? v : def; }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    return {
      minSupport: clamp(num(o.minSupport, DEFAULTS.minSupport), 0.10, 1.0),
      maxOverhang: clamp(num(o.maxOverhang, DEFAULTS.maxOverhang), 0, 100),
      maxGap: clamp(num(o.maxGap, DEFAULTS.maxGap), 0, 200),
    };
  }

  // Passada unica rapida (Bottom-Left com ordenacao por altura-deitada).
  function pack(bay, motoList, options) {
    var opt = normalizeOptions(options);
    var items = expandAndSort(motoList);
    if (items.length > MAX_ITEMS) items = items.slice(0, MAX_ITEMS);
    return packItems(bay, items, opt);
  }

  /**
   * Empacotamento OTIMIZADO: Simulated Annealing sobre a ORDEM de insercao, usando
   * packItems (Bottom-Left) como avaliador. So muda a ORDEM em que as motos entram —
   * mantem TODAS as regras fisicas (horizontalidade, apoio, sem interpenetracao).
   * Determinístico (PRNG com seed fixo): mesmos inputs -> mesmo layout, sem "pulos"
   * entre recalculos. Para assim que acomoda todas (early-stop) ou estoura o orcamento.
   *
   * Por que SA e nao um solver exato (ex.: OR-Tools/CP-SAT): container loading 3D com
   * apoio fisico e NP-dificil e mal modelado em CP (sem geometria nativa, nao escala
   * >100 itens). A metaheuristica parte da heuristica boa e acha o otimo em poucas
   * dezenas de avaliacoes (~ms), no browser, sem backend.
   */
  function packOptimized(bay, motoList, options, budget) {
    var opt = normalizeOptions(options);
    budget = budget || {};
    var maxIters = (typeof budget.maxIters === 'number') ? budget.maxIters : 160;
    var maxMs = (typeof budget.maxMs === 'number') ? budget.maxMs : 1500;

    var base = expandItems(motoList);
    if (base.length > MAX_ITEMS) base = base.slice(0, MAX_ITEMS);
    var total = base.length;

    // Solucao inicial = heuristica altura-deitada asc (melhor passada unica).
    var current = sortByLayingHeight(base.slice());
    var currentRes = packItems(bay, current, opt);
    var currentE = energy(currentRes);
    var bestRes = currentRes, bestE = currentE;
    if (bestRes.stats.posicionadas >= total) return bestRes; // ja cabe tudo

    var rng = makeRng(0x9e3779b9);
    var clock = (typeof performance !== 'undefined' && performance.now)
      ? function () { return performance.now(); }
      : function () { return Date.now(); };
    var t0 = clock();
    var T = 200000, cool = Math.pow(0.0005, 1 / Math.max(1, maxIters));

    for (var it = 0; it < maxIters; it++) {
      var cand = current.slice();
      var rej = currentRes.rejected;
      // Movimento dirigido: com 60% de chance, joga uma moto REJEITADA para perto
      // do inicio da fila (onde pega os melhores lugares). Acelera muito a convergencia
      // vs mover uma moto aleatoria. Senao, movimento aleatorio (diversifica).
      if (rej.length > 0 && rng() < 0.6) {
        var alvo = rej[Math.floor(rng() * rej.length)];
        var idx = cand.indexOf(alvo);
        if (idx >= 0) { cand.splice(idx, 1); cand.splice(Math.floor(rng() * Math.min(cand.length, 8)), 0, alvo); }
      } else {
        var from = Math.floor(rng() * cand.length);
        var to = Math.floor(rng() * cand.length);
        cand.splice(to, 0, cand.splice(from, 1)[0]);
      }

      var res = packItems(bay, cand, opt);
      var e = energy(res);
      if (e < currentE || rng() < Math.exp(-(e - currentE) / T)) {
        current = cand; currentE = e; currentRes = res;
        if (e < bestE) { bestE = e; bestRes = res; }
      }
      T *= cool;
      if (bestRes.stats.posicionadas >= total) break;         // acomodou tudo
      if ((it & 15) === 0 && clock() - t0 > maxMs) break;      // guarda de tempo
    }
    return bestRes;
  }

  /** Energia a minimizar: prioriza nº de motos; desempata por volume ocupado. */
  function energy(res) {
    return -(res.stats.posicionadas * 1e9 + res.stats.volumeOcupado);
  }

  /** PRNG deterministico (LCG) — resultado reproduzivel para os mesmos inputs. */
  function makeRng(seedVal) {
    var s = seedVal >>> 0;
    return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  }

  /** Placement guloso Bottom-Left de uma sequencia JA ordenada de itens. */
  function packItems(bay, items, opt) {
    var freeSpaces = [{ x: 0, y: 0, z: 0, w: bay.w, d: bay.d, h: bay.h }];
    var placed = [];
    var rejected = [];

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var best = findBestFit(item, getOrientations(item), freeSpaces, bay, placed, opt);

      if (best) {
        var p = {
          moto: item,
          x: best.x, y: best.y, z: best.z,
          w: best.ow, d: best.od, h: best.oh,
          orientacao: best.orientIdx,
          slabs: best.slabs,
        };
        placed.push(p);
        for (var sb = 0; sb < p.slabs.length; sb++) {
          freeSpaces = subtractBox(freeSpaces, p.slabs[sb]);
        }
      } else {
        rejected.push(item);
      }
    }

    var bayVol = bay.w * bay.d * bay.h;
    var usedVol = 0, totalPeso = 0;
    for (var j = 0; j < placed.length; j++) {
      usedVol += placed[j].w * placed[j].d * placed[j].h;
      totalPeso += placed[j].moto.peso_medio || 0;
    }

    return {
      placed: placed,
      rejected: rejected,
      bay: bay,
      stats: {
        total: items.length,
        posicionadas: placed.length,
        rejeitadas: rejected.length,
        volumeOcupado: usedVol,
        volumeTotal: bayVol,
        percentualOcupacao: bayVol > 0 ? Math.round((usedVol / bayVol) * 100) : 0,
        pesoTotal: Math.round(totalPeso * 100) / 100,
      },
    };
  }

  // Expande as quantidades em itens individuais (1 moto = 1 item), sem ordenar.
  function expandItems(motoList) {
    var items = [];
    for (var i = 0; i < motoList.length; i++) {
      var m = motoList[i];
      var qty = (m.qty == null) ? 1 : m.qty; // qty=0 => 0 itens (nao 1)
      for (var q = 0; q < qty; q++) {
        var it = {
          id: m.id, nome: m.nome,
          comprimento: m.comprimento, largura: m.largura, altura: m.altura,
          peso_medio: m.peso_medio || 0, color: m.color || '#4a90d9',
          volume: (m.comprimento || 0) * (m.largura || 0) * (m.altura || 0),
          tipo: m.tipo || 'moto',
        };
        if (m.tipo === 'pallet') {
          it.base_x = m.base_x; it.base_y = m.base_y;
          it.altura_estrado = m.altura_estrado;
          it.merc_x = m.merc_x; it.merc_y = m.merc_y;
          it.altura_merc = m.altura_merc; it.altura_total = m.altura_total;
          it.altura = m.altura_total; it.comprimento = m.base_x; it.largura = m.base_y;
          it.volume = m.base_x * m.base_y * m.altura_total;
          it.grupo = m.grupo;
        }
        items.push(it);
      }
    }
    return items;
  }

  /**
   * Ordena por altura-deitada (menor dimensao vertical possivel) ascendente:
   * motos mais baixas primeiro formam camadas planas, que servem de base para
   * empilhar denso. Desempate por volume desc (maiores antes na mesma faixa).
   */
  function sortByLayingHeight(items) {
    items.sort(function (a, b) {
      var ha = Math.min(a.largura, a.altura);
      var hb = Math.min(b.largura, b.altura);
      if (Math.abs(ha - hb) > 0.5) return ha - hb;
      return b.volume - a.volume;
    });
    return items;
  }

  function expandAndSort(motoList) {
    return sortByLayingHeight(expandItems(motoList));
  }

  /**
   * 4 orientacoes — comprimento (C) SEMPRE na horizontal (X ou Z), nunca na altura.
   * idx 0/2: deitada (altura A no eixo Y). idx 1/3: tombada de lado (largura L no Y).
   * Em nenhuma o comprimento vai para o eixo Y => moto nunca fica "de pe".
   */
  // Slabs de um pallet: estrado (canto) + coluna de mercadoria (centralizada).
  // A coluna pode exceder o estrado (folga); offset pode ser negativo.
  function palletSlabs(item, x, y, z) {
    var bx = item.base_x, by = item.base_y, est = item.altura_estrado;
    var mx = item.merc_x, my = item.merc_y, alt = item.altura_total;
    var ox = (bx - mx) / 2, oy = (by - my) / 2;
    return [
      { x: x, y: y, z: z, w: bx, d: by, h: est },
      { x: x + ox, y: y + est, z: z + oy, w: mx, d: my, h: alt - est },
    ];
  }

  function getOrientations(item) {
    if (item.tipo === 'pallet') {
      // pallet nao rotaciona: estrado sempre com a base no chao. oh = altura total
      // (a coluna excede lateralmente; o fit no freeSpace usa so o estrado).
      return [{ ow: item.base_x, od: item.base_y, oh: item.altura_total, idx: 0 }];
    }
    var C = item.comprimento, L = item.largura, A = item.altura;
    return [
      { ow: C, od: L, oh: A, idx: 0 }, // C(X) L(Z) A(Y) — deitada
      { ow: C, od: A, oh: L, idx: 1 }, // C(X) A(Z) L(Y) — tombada de lado
      { ow: L, od: C, oh: A, idx: 2 }, // L(X) C(Z) A(Y) — deitada
      { ow: A, od: C, oh: L, idx: 3 }, // A(X) C(Z) L(Y) — tombada de lado
    ];
  }

  // Slabs absolutos de um item numa dada orientacao/posicao.
  // Moto = 1 slab (footprint da orientacao). Pallet sobrescreve via palletSlabs.
  function itemSlabs(item, ori, x, y, z) {
    if (item.tipo === 'pallet') return palletSlabs(item, x, y, z);
    return [{ x: x, y: y, z: z, w: ori.ow, d: ori.od, h: ori.oh }];
  }

  // Dois conjuntos de slabs colidem se algum par se sobrepoe nos 3 eixos.
  function slabsColidem(a, b) {
    for (var i = 0; i < a.length; i++) {
      for (var j = 0; j < b.length; j++) {
        var s = a[i], t = b[j];
        if (s.x < t.x + t.w - 0.1 && s.x + s.w > t.x + 0.1 &&
            s.y < t.y + t.h - 0.1 && s.y + s.h > t.y + 0.1 &&
            s.z < t.z + t.d - 0.1 && s.z + s.d > t.z + 0.1) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Bottom-Left-Back Fill com validacao de apoio fisico.
   *
   * Entre todas as (posicao livre x orientacao) validas, escolhe a que minimiza
   * lexicograficamente (Y, Z, X) — a moto "cai" para o fundo-baixo-esquerda do bau.
   * Isso enche o chao primeiro e forma camadas planas (topos alinhados), o que
   * viabiliza empilhar denso. Empate de posicao: menor folga lateral (shortSide).
   *
   * Chao (Y=0): apoio total. Empilhada (Y>0): exige supportPct >= opt.minSupport.
   */
  function findBestFit(item, orientations, freeSpaces, bay, placed, opt) {
    var best = null;
    var bestY = Infinity, bestZ = Infinity, bestX = Infinity, bestShort = Infinity;

    for (var s = 0; s < freeSpaces.length; s++) {
      var sp = freeSpaces[s];

      for (var o = 0; o < orientations.length; o++) {
        var ori = orientations[o];

        // Pallet: o fit no freeSpace usa so a altura do estrado (a coluna excede
        // lateralmente e e validada por colisao); a altura TOTAL e checada no teto.
        var ehPallet = item.tipo === 'pallet';
        var fitH = ehPallet ? item.altura_estrado : ori.oh;
        var altReal = ehPallet ? item.altura_total : ori.oh;

        if (ori.ow > sp.w + 0.1 || ori.od > sp.d + 0.1 || fitH > sp.h + 0.1) continue;
        if (sp.x + ori.ow > bay.w + 0.1) continue;
        if (sp.z + ori.od > bay.d + 0.1) continue;
        if (sp.y + altReal > bay.h + 0.1) continue;

        // Caminho critico: a coluna de mercadoria nao pode atravessar colunas/
        // estrados ja posicionados (mas pode invadir o ar sobre o estrado vizinho).
        if (ehPallet) {
          var candSlabs = itemSlabs(item, ori, sp.x, sp.y, sp.z);
          var colideCol = false;
          for (var pc = 0; pc < placed.length; pc++) {
            if (slabsColidem(candSlabs, placed[pc].slabs)) { colideCol = true; break; }
          }
          if (colideCol) continue;
        }

        // Empilhamento: exige apoio minimo da base sobre caixas abaixo.
        if (sp.y > 0.1) {
          var supportPct = getSupportPercentage(sp.x, sp.y, sp.z, ori.ow, ori.od, placed, opt);
          if (supportPct < opt.minSupport * 100) continue;
        }

        // Bottom-Left-Back: prioriza Y, depois Z, depois X; desempate por encaixe justo.
        var shortSide = Math.min(sp.w - ori.ow, sp.d - ori.od);
        var melhor = false;
        if (sp.y < bestY - 0.1) {
          melhor = true;
        } else if (sp.y <= bestY + 0.1) {
          if (sp.z < bestZ - 0.1) {
            melhor = true;
          } else if (sp.z <= bestZ + 0.1) {
            if (sp.x < bestX - 0.1) {
              melhor = true;
            } else if (sp.x <= bestX + 0.1 && shortSide < bestShort - 0.1) {
              melhor = true;
            }
          }
        }

        if (melhor) {
          bestY = sp.y; bestZ = sp.z; bestX = sp.x; bestShort = shortSide;
          best = {
            x: sp.x, y: sp.y, z: sp.z,
            ow: ori.ow, od: ori.od, oh: ori.oh,
            orientIdx: ori.idx,
            slabs: itemSlabs(item, ori, sp.x, sp.y, sp.z),
          };
        }
      }
    }
    return best;
  }

  /**
   * Calcula % de apoio real para uma posicao empilhada.
   * Retorna 0-100. Tambem valida overhang e vao central (limites em opt).
   */
  function getSupportPercentage(px, py, pz, pw, pd, placed, opt) {
    var px2 = px + pw;
    var pz2 = pz + pd;
    var baseArea = pw * pd;
    var supports = [];

    for (var i = 0; i < placed.length; i++) {
      var b = placed[i];
      var topY = b.y + b.h;
      if (topY < py - 2 || topY > py + 2) continue;

      var ox1 = Math.max(px, b.x);
      var ox2 = Math.min(px2, b.x + b.w);
      var oz1 = Math.max(pz, b.z);
      var oz2 = Math.min(pz2, b.z + b.d);

      if (ox2 > ox1 + 0.1 && oz2 > oz1 + 0.1) {
        supports.push({ x1: ox1, x2: ox2, z1: oz1, z2: oz2 });
      }
    }

    if (supports.length === 0) return 0;

    // Verificar overhang e vao
    var supportsX = supports.map(function (s) { return [s.x1, s.x2]; });
    var supportsZ = supports.map(function (s) { return [s.z1, s.z2]; });
    if (!checkAxisSupport(supportsX, px, px2, opt)) return 0;
    if (!checkAxisSupport(supportsZ, pz, pz2, opt)) return 0;

    var supportArea = calcSupportArea(supports);
    return Math.round(supportArea / baseArea * 100);
  }

  // =====================================================================
  // Validacao de apoio fisico
  // =====================================================================

  /**
   * Calcula area total de apoio (uniao de retangulos 2D).
   * Usa sweep line no eixo X para area exata sem double-counting.
   */
  function calcSupportArea(rects) {
    if (rects.length === 0) return 0;
    if (rects.length === 1) {
      return (rects[0].x2 - rects[0].x1) * (rects[0].z2 - rects[0].z1);
    }

    // Coletar todos os X distintos (sweep line)
    var xCoords = [];
    for (var i = 0; i < rects.length; i++) {
      xCoords.push(rects[i].x1);
      xCoords.push(rects[i].x2);
    }
    xCoords.sort(function (a, b) { return a - b; });

    // Remover duplicados
    var xs = [xCoords[0]];
    for (var j = 1; j < xCoords.length; j++) {
      if (xCoords[j] > xs[xs.length - 1] + 0.01) xs.push(xCoords[j]);
    }

    var totalArea = 0;

    // Para cada faixa entre X consecutivos
    for (var k = 0; k < xs.length - 1; k++) {
      var sliceX1 = xs[k];
      var sliceX2 = xs[k + 1];
      var sliceW = sliceX2 - sliceX1;
      if (sliceW < 0.01) continue;

      // Coletar intervalos Z que cobrem esta faixa X
      var zIntervals = [];
      for (var r = 0; r < rects.length; r++) {
        if (rects[r].x1 <= sliceX1 + 0.01 && rects[r].x2 >= sliceX2 - 0.01) {
          zIntervals.push([rects[r].z1, rects[r].z2]);
        }
      }

      // Merge intervalos Z e calcular cobertura
      var merged = mergeIntervals(zIntervals);
      var zCoverage = 0;
      for (var m = 0; m < merged.length; m++) {
        zCoverage += merged[m][1] - merged[m][0];
      }

      totalArea += sliceW * zCoverage;
    }

    return totalArea;
  }

  /**
   * Verifica overhang e vao central num eixo (limites vindos de opt).
   */
  function checkAxisSupport(intervals, start, end, opt) {
    var merged = mergeIntervals(intervals);

    var minSupport = Infinity;
    var maxSupport = -Infinity;
    for (var i = 0; i < merged.length; i++) {
      if (merged[i][0] < minSupport) minSupport = merged[i][0];
      if (merged[i][1] > maxSupport) maxSupport = merged[i][1];
    }

    // Overhang nas extremidades
    if (minSupport - start > opt.maxOverhang) return false;
    if (end - maxSupport > opt.maxOverhang) return false;

    // Vao central
    if (merged.length > 1) {
      for (var g = 1; g < merged.length; g++) {
        var gap = merged[g][0] - merged[g - 1][1];
        if (gap > opt.maxGap) return false;
      }
    }

    return true;
  }

  /**
   * Merge intervalos sobrepostos.
   */
  function mergeIntervals(intervals) {
    if (intervals.length <= 1) return intervals.slice();

    var sorted = intervals.slice().sort(function (a, b) { return a[0] - b[0]; });
    var result = [sorted[0].slice()];

    for (var i = 1; i < sorted.length; i++) {
      var last = result[result.length - 1];
      if (sorted[i][0] <= last[1] + 0.1) {
        last[1] = Math.max(last[1], sorted[i][1]);
      } else {
        result.push(sorted[i].slice());
      }
    }
    return result;
  }

  // =====================================================================
  // Maximal Rectangles — subtractBox e pruneSpaces
  // =====================================================================

  function subtractBox(freeSpaces, box) {
    var bx2 = box.x + box.w, by2 = box.y + box.h, bz2 = box.z + box.d;
    var result = [];

    for (var i = 0; i < freeSpaces.length; i++) {
      var sp = freeSpaces[i];
      var sx2 = sp.x + sp.w, sy2 = sp.y + sp.h, sz2 = sp.z + sp.d;

      if (box.x >= sx2 || bx2 <= sp.x ||
          box.y >= sy2 || by2 <= sp.y ||
          box.z >= sz2 || bz2 <= sp.z) {
        result.push(sp);
        continue;
      }

      if (box.x > sp.x + MIN_DIM) {
        result.push({ x: sp.x, y: sp.y, z: sp.z, w: box.x - sp.x, d: sp.d, h: sp.h });
      }
      if (bx2 < sx2 - MIN_DIM) {
        result.push({ x: bx2, y: sp.y, z: sp.z, w: sx2 - bx2, d: sp.d, h: sp.h });
      }
      if (box.z > sp.z + MIN_DIM) {
        result.push({ x: sp.x, y: sp.y, z: sp.z, w: sp.w, d: box.z - sp.z, h: sp.h });
      }
      if (bz2 < sz2 - MIN_DIM) {
        result.push({ x: sp.x, y: sp.y, z: bz2, w: sp.w, d: sz2 - bz2, h: sp.h });
      }
      if (box.y > sp.y + MIN_DIM) {
        result.push({ x: sp.x, y: sp.y, z: sp.z, w: sp.w, d: sp.d, h: box.y - sp.y });
      }
      if (by2 < sy2 - MIN_DIM) {
        result.push({ x: sp.x, y: by2, z: sp.z, w: sp.w, d: sp.d, h: sy2 - by2 });
      }
    }

    return pruneSpaces(result);
  }

  function pruneSpaces(spaces) {
    var valid = [];
    for (var i = 0; i < spaces.length; i++) {
      var s = spaces[i];
      if (s.w >= MIN_DIM && s.d >= MIN_DIM && s.h >= MIN_DIM) {
        valid.push(s);
      }
    }

    if (valid.length <= 1) return valid;

    var keep = [];
    for (var a = 0; a < valid.length; a++) {
      var isContained = false;
      var sa = valid[a];

      for (var b = 0; b < valid.length; b++) {
        if (a === b) continue;
        var sb = valid[b];

        if (sa.x >= sb.x && sa.y >= sb.y && sa.z >= sb.z &&
            sa.x + sa.w <= sb.x + sb.w + 0.1 &&
            sa.y + sa.h <= sb.y + sb.h + 0.1 &&
            sa.z + sa.d <= sb.z + sb.d + 0.1) {
          isContained = true;
          break;
        }
      }

      if (!isContained) keep.push(sa);
    }

    if (keep.length > 300) {
      keep.sort(function (a, b) {
        return (b.w * b.d * b.h) - (a.w * a.d * a.h);
      });
      keep = keep.slice(0, 300);
    }

    return keep;
  }

  window.BinPacker = { pack: pack, packOptimized: packOptimized };
})();
