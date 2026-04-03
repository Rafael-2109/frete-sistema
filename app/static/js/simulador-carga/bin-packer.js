/**
 * BinPacker — Algoritmo 3D Maximal Rectangles + Best Fit para empacotamento de motos.
 *
 * Regras de orientacao:
 * - Comprimento da moto SEMPRE horizontal (eixos X ou Z do bau, nunca Y)
 * - Largura e altura intercambiaveis (moto pode ser deitada)
 * - 4 orientacoes validas por moto, testadas individualmente
 *
 * Regras de apoio fisico (empilhamento):
 * - Moto no chao (Y=0): sempre valida
 * - Moto empilhada (Y>0): deve ter apoio suficiente embaixo
 *   - Max 10cm de balanco (overhang) em cada extremidade
 *   - Max 40cm de vao livre no centro (apoiado pelos 2 lados)
 *
 * Algoritmo: Maximal Rectangles + FFD + Best Short Side Fit + validacao de suporte.
 */
;(function () {
  'use strict';

  var MAX_ITEMS = 200;
  var MIN_DIM = 5;

  // Regras de apoio fisico
  var MAX_OVERHANG_EDGE = 10;   // cm — balanco maximo nas extremidades
  var MAX_GAP_CENTER = 40;      // cm — vao maximo no centro (apoiado dos 2 lados)

  function pack(bay, motoList) {
    var items = expandAndSort(motoList);
    if (items.length > MAX_ITEMS) items = items.slice(0, MAX_ITEMS);

    var freeSpaces = [{ x: 0, y: 0, z: 0, w: bay.w, d: bay.d, h: bay.h }];
    var placed = [];
    var rejected = [];

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var orientations = getOrientations(item);
      var best = findBestFit(orientations, freeSpaces, bay, placed);

      if (best) {
        var p = {
          moto: item,
          x: best.x, y: best.y, z: best.z,
          w: best.ow, d: best.od, h: best.oh,
          orientacao: best.orientIdx,
        };
        placed.push(p);
        freeSpaces = subtractBox(freeSpaces, p);
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

  function expandAndSort(motoList) {
    var items = [];
    for (var i = 0; i < motoList.length; i++) {
      var m = motoList[i];
      for (var q = 0; q < (m.qty || 1); q++) {
        items.push({
          id: m.id, nome: m.nome,
          comprimento: m.comprimento, largura: m.largura, altura: m.altura,
          peso_medio: m.peso_medio || 0, color: m.color || '#4a90d9',
          volume: m.comprimento * m.largura * m.altura,
        });
      }
    }
    items.sort(function (a, b) { return b.volume - a.volume; });
    return items;
  }

  function getOrientations(item) {
    var C = item.comprimento, L = item.largura, A = item.altura;
    return [
      { ow: C, od: L, oh: A, idx: 0 },
      { ow: C, od: A, oh: L, idx: 1 },
      { ow: L, od: C, oh: A, idx: 2 },
      { ow: A, od: C, oh: L, idx: 3 },
    ];
  }

  /**
   * Best Short Side Fit com priorizacao de apoio fisico.
   *
   * Para Y=0 (chao): Best Short Side Fit puro.
   * Para Y>0 (empilhada): prioriza APOIO TOTAL antes de encaixe justo.
   *   1. Maior % de apoio (100% > 80% > 60%)
   *   2. Menor short side (encaixe justo)
   *   3. Menor long side
   *   4. Menor Y, Z, X
   */
  function findBestFit(orientations, freeSpaces, bay, placed) {
    var best = null;
    var bestSupport = -1;     // % apoio (0-100), so usado para Y>0
    var bestShortSide = Infinity;
    var bestLongSide = Infinity;
    var bestY = Infinity;

    for (var s = 0; s < freeSpaces.length; s++) {
      var sp = freeSpaces[s];

      for (var o = 0; o < orientations.length; o++) {
        var ori = orientations[o];

        if (ori.ow > sp.w + 0.1 || ori.od > sp.d + 0.1 || ori.oh > sp.h + 0.1) continue;
        if (sp.x + ori.ow > bay.w + 0.1) continue;
        if (sp.z + ori.od > bay.d + 0.1) continue;
        if (sp.y + ori.oh > bay.h + 0.1) continue;

        // Calcular apoio para empilhamento
        var supportPct = 100; // chao = apoio total
        if (sp.y > 0.1) {
          supportPct = getSupportPercentage(sp.x, sp.y, sp.z, ori.ow, ori.od, placed);
          if (supportPct < MIN_SUPPORT_RATIO * 100) continue; // rejeitar se < 60%
        }

        var residuoW = sp.w - ori.ow;
        var residuoD = sp.d - ori.od;
        var shortSide = Math.min(residuoW, residuoD);
        var longSide = Math.max(residuoW, residuoD);

        var isBetter = false;

        if (sp.y > 0.1 && best && best.y > 0.1) {
          // Ambos empilhados: priorizar APOIO primeiro
          if (supportPct > bestSupport + 1) {
            isBetter = true;
          } else if (Math.abs(supportPct - bestSupport) <= 1) {
            // Apoio similar: desempatar por fit
            isBetter = compareFit(shortSide, longSide, sp, bestShortSide, bestLongSide, bestY, best);
          }
        } else if (sp.y < 0.1 && best && best.y > 0.1) {
          // Chao vs empilhado: chao sempre melhor
          isBetter = true;
        } else if (sp.y > 0.1 && best && best.y < 0.1) {
          // Empilhado vs chao: chao sempre melhor
          isBetter = false;
        } else {
          // Ambos no chao ou primeiro candidato
          isBetter = compareFit(shortSide, longSide, sp, bestShortSide, bestLongSide, bestY, best);
        }

        if (isBetter) {
          bestSupport = supportPct;
          bestShortSide = shortSide;
          bestLongSide = longSide;
          bestY = sp.y;
          best = {
            x: sp.x, y: sp.y, z: sp.z,
            ow: ori.ow, od: ori.od, oh: ori.oh,
            orientIdx: ori.idx,
          };
        }
      }
    }
    return best;
  }

  /** Compara fit entre dois candidatos (short side, long side, posicao). */
  function compareFit(shortSide, longSide, sp, bestShortSide, bestLongSide, bestY, best) {
    if (shortSide < bestShortSide - 0.1) return true;
    if (Math.abs(shortSide - bestShortSide) > 0.1) return false;

    if (longSide < bestLongSide - 0.1) return true;
    if (Math.abs(longSide - bestLongSide) > 0.1) return false;

    if (sp.y < bestY - 0.1) return true;
    if (Math.abs(sp.y - bestY) > 0.1) return false;

    if (!best) return true;
    if (sp.z < best.z - 0.1) return true;
    if (Math.abs(sp.z - best.z) > 0.1) return false;

    return sp.x < best.x;
  }

  /**
   * Calcula % de apoio real para uma posicao empilhada.
   * Retorna 0-100. Tambem valida overhang e vao central.
   */
  function getSupportPercentage(px, py, pz, pw, pd, placed) {
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
    if (!checkAxisSupport(supportsX, px, px2)) return 0;
    if (!checkAxisSupport(supportsZ, pz, pz2)) return 0;

    var supportArea = calcSupportArea(supports);
    return Math.round(supportArea / baseArea * 100);
  }

  // =====================================================================
  // Validacao de apoio fisico
  // =====================================================================

  var MIN_SUPPORT_RATIO = 0.60; // 60% da base deve ter apoio real

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
   * Verifica overhang e vao central num eixo.
   */
  function checkAxisSupport(intervals, start, end) {
    var merged = mergeIntervals(intervals);

    var minSupport = Infinity;
    var maxSupport = -Infinity;
    for (var i = 0; i < merged.length; i++) {
      if (merged[i][0] < minSupport) minSupport = merged[i][0];
      if (merged[i][1] > maxSupport) maxSupport = merged[i][1];
    }

    // Overhang nas extremidades
    if (minSupport - start > MAX_OVERHANG_EDGE) return false;
    if (end - maxSupport > MAX_OVERHANG_EDGE) return false;

    // Vao central
    if (merged.length > 1) {
      for (var g = 1; g < merged.length; g++) {
        var gap = merged[g][0] - merged[g - 1][1];
        if (gap > MAX_GAP_CENTER) return false;
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

  window.BinPacker = { pack: pack };
})();
