/* Gráficos do módulo Rentabilidade.
 *
 * Por D-113 eles reproduzem os do Lucrums; por D-110 e pela CSP `script-src 'self'`
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

    var pontosMargem = [];
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

      // A margem é fração; -1 a 1 cobre prejuízo total até margem plena.
      var limitada = Math.max(-1, Math.min(1, ponto.margem || 0));
      var y = margem.topo + area.altura / 2 - (limitada * area.altura) / 2;
      pontosMargem.push([base + larguraBarra + 1, y]);

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

    svg.appendChild(
      el("polyline", {
        points: pontosMargem
          .map(function (par) {
            return par[0] + "," + par[1];
          })
          .join(" "),
        class: "chart-line",
      })
    );

    host.appendChild(svg);
  }

  function init() {
    var hosts = document.querySelectorAll('[data-chart="evolucao"]');
    Array.prototype.forEach.call(hosts, drawEvolucao);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
