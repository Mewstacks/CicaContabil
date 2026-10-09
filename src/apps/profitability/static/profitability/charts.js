/* Gráficos do módulo Rentabilidade.
 *
 * Por D-286 eles reproduzem os do Lucrums; por D-283 e pela CSP `script-src 'self'`
 * a biblioteca da origem não pode ser carregada, então o desenho é feito aqui, em
 * SVG, sem dependência externa e sem script inline.
 *
 * Três regras que o gráfico da origem já seguia e que se perderiam num redesenho
 * distraído:
 *
 * 1. O dado vem de um atributo `data-series`, não de uma requisição: a página já
 *    o trouxe, e buscá-lo de novo abriria uma segunda fonte de verdade.
 * 2. O mesmo dado está numa tabela ao lado, que leitor de tela percorre e que
 *    sobrevive à impressão. O SVG é `aria-hidden` porque duplicá-lo em voz alta
 *    faria a pessoa ouvir a série duas vezes.
 * 3. Mês sem dado é desenhado como vazio, não omitido. Omitir faria a linha
 *    saltar de agosto para outubro como se setembro não tivesse existido.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  function el(name, attrs) {
    var node = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    return node;
  }

  function parseSeries(host) {
    try {
      var raw = JSON.parse(host.dataset.series || "[]");
      return Array.isArray(raw) ? raw : [];
    } catch (erro) {
      return [];
    }
  }

  function drawEvolucao(host) {
    var dados = parseSeries(host);
    if (!dados.length) {
      return;
    }

    var largura = 720;
    var altura = 240;
    var margem = { topo: 16, direita: 44, base: 28, esquerda: 52 };
    var area = {
      largura: largura - margem.esquerda - margem.direita,
      altura: altura - margem.topo - margem.base,
    };

    var maiorValor = dados.reduce(function (maior, ponto) {
      return Math.max(maior, ponto.mensalidade || 0, ponto.custo || 0);
    }, 0);
    // Escala com piso em 1 para uma carteira inteiramente zerada não dividir por
    // zero e desenhar barras de altura infinita.
    var escala = maiorValor > 0 ? area.altura / maiorValor : 0;
    var passo = area.largura / dados.length;
    var larguraBarra = Math.max(2, (passo - 6) / 2);

    var svg = el("svg", {
      viewBox: "0 0 " + largura + " " + altura,
      width: "100%",
      "aria-hidden": "true",
      focusable: "false",
      class: "profitability-chart-svg",
    });

    // Linha de base: sem ela as barras flutuam e a leitura perde o zero.
    svg.appendChild(
      el("line", {
        x1: margem.esquerda,
        y1: margem.topo + area.altura,
        x2: margem.esquerda + area.largura,
        y2: margem.topo + area.altura,
        class: "chart-axis",
      })
    );

    var segmentosMargem = [];
    var segmentoMargem = [];
    dados.forEach(function (ponto, indice) {
      var base = margem.esquerda + indice * passo + 3;
      var receita = (ponto.mensalidade || 0) * escala;
      var custo = (ponto.custo || 0) * escala;

      svg.appendChild(
        el("rect", {
          x: base,
          y: margem.topo + area.altura - receita,
          width: larguraBarra,
          height: Math.max(0, receita),
          class: "chart-bar is-revenue",
        })
      );
      svg.appendChild(
        el("rect", {
          x: base + larguraBarra + 2,
          y: margem.topo + area.altura - custo,
          width: larguraBarra,
          height: Math.max(0, custo),
          class: "chart-bar is-cost",
        })
      );

      // Sem honorário, zero não é margem: a linha precisa ter um intervalo
      // vazio, sem ligar os meses vizinhos por cima da lacuna.
      if (typeof ponto.margem === "number" && Number.isFinite(ponto.margem)) {
        var limitada = Math.max(-1, Math.min(1, ponto.margem));
        var y = margem.topo + area.altura / 2 - (limitada * area.altura) / 2;
        segmentoMargem.push([base + larguraBarra + 1, y]);
      } else if (segmentoMargem.length) {
        segmentosMargem.push(segmentoMargem);
        segmentoMargem = [];
      }

      if (indice % 2 === 0) {
        var rotulo = el("text", {
          x: base + larguraBarra + 1,
          y: altura - 8,
          "text-anchor": "middle",
          class: "chart-label",
        });
        rotulo.textContent = String(ponto.competencia || "").slice(2);
        svg.appendChild(rotulo);
      }
    });

    if (segmentoMargem.length) {
      segmentosMargem.push(segmentoMargem);
    }
    segmentosMargem.forEach(function (segmento) {
      if (segmento.length === 1) {
        svg.appendChild(
          el("circle", {
            cx: segmento[0][0],
            cy: segmento[0][1],
            r: 2.5,
            class: "chart-point",
          })
        );
        return;
      }
      svg.appendChild(
        el("polyline", {
          points: segmento
            .map(function (par) {
              return par[0] + "," + par[1];
            })
            .join(" "),
          class: "chart-line",
        })
      );
    });

    host.appendChild(svg);
  }

  /* Treemap por divisão em faixas (squarified simplificado).
   *
   * O gráfico anterior era de dispersão, uma bolha por cliente — e como o custo
   * subapurado empurra quase todos para margem alta, as bolhas se empilhavam numa
   * faixa estreita e nenhuma era legível. Retângulo não sobrepõe: densidade vira
   * área em vez de borrão.
   *
   * O nome é desenhado por cima do retângulo, e só quando cabe: um rótulo maior
   * que a própria área transborda para os vizinhos e faz a pessoa ler o nome de
   * um cliente sobre a área de outro.
   */
  function drawMapa(host) {
    var dados = parseSeries(host).filter(function (item) {
      return item && item.valor > 0;
    });
    if (!dados.length) {
      return;
    }
    dados.sort(function (a, b) {
      return b.valor - a.valor;
    });

    var largura = 720;
    var altura = 320;
    var total = dados.reduce(function (soma, item) {
      return soma + item.valor;
    }, 0);

    var svg = el("svg", {
      viewBox: "0 0 " + largura + " " + altura,
      width: "100%",
      "aria-hidden": "true",
      focusable: "false",
      class: "profitability-chart-svg",
    });

    var x = 0;
    var y = 0;
    var restanteLargura = largura;
    var restanteAltura = altura;
    var indice = 0;

    while (indice < dados.length) {
      var horizontal = restanteLargura >= restanteAltura;
      var disponivel = horizontal ? restanteAltura : restanteLargura;
      var restanteValor = dados.slice(indice).reduce(function (soma, item) {
        return soma + item.valor;
      }, 0);
      if (restanteValor <= 0) {
        break;
      }

      // Uma faixa por vez, com quantos itens couberem sem ficarem finos demais
      // para o nome: retângulo de menos de 14px de lado não recebe rótulo, e uma
      // faixa inteira deles vira uma listra ilegível.
      var faixa = [];
      var faixaValor = 0;
      while (indice < dados.length) {
        faixa.push(dados[indice]);
        faixaValor += dados[indice].valor;
        indice++;
        var espessura = (faixaValor / restanteValor) * (horizontal ? restanteLargura : restanteAltura);
        if (espessura >= 36 || indice >= dados.length) {
          break;
        }
      }

      var espessuraFaixa = (faixaValor / restanteValor) * (horizontal ? restanteLargura : restanteAltura);
      var deslocamento = 0;
      for (var i = 0; i < faixa.length; i++) {
        var item = faixa[i];
        var proporcao = faixaValor > 0 ? item.valor / faixaValor : 0;
        var comprimento = proporcao * disponivel;
        var rx = horizontal ? x : x + deslocamento;
        var ry = horizontal ? y + deslocamento : y;
        var rw = horizontal ? espessuraFaixa : comprimento;
        var rh = horizontal ? comprimento : espessuraFaixa;

        svg.appendChild(
          el("rect", {
            x: rx + 1,
            y: ry + 1,
            width: Math.max(0, rw - 2),
            height: Math.max(0, rh - 2),
            class: "chart-tile is-" + (item.faixa || "sem_dados"),
          })
        );
        if (rw > 70 && rh > 22) {
          var nome = el("text", {
            x: rx + 8,
            y: ry + 18,
            class: "chart-tile-label",
          });
          nome.textContent = String(item.nome || "");
          svg.appendChild(nome);
        }
        deslocamento += comprimento;
      }

      if (horizontal) {
        x += espessuraFaixa;
        restanteLargura -= espessuraFaixa;
      } else {
        y += espessuraFaixa;
        restanteAltura -= espessuraFaixa;
      }
      if (restanteLargura <= 1 || restanteAltura <= 1) {
        break;
      }
    }

    host.appendChild(svg);
    host.setAttribute(
      "data-total",
      String(total)
    );
  }

  function init() {
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-chart="evolucao"]'), drawEvolucao);
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-chart="mapa"]'), drawMapa);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
