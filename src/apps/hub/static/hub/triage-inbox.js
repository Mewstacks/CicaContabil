/* Triagem, Pendências: atalhos de teclado, seleção em lote, trecho do texto para regra. */
(function () {
  "use strict";
  var root = document.querySelector("[data-inbox]");
  if (!root) return;

  function typing(target) {
    if (!target) return false;
    var tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  // Atalhos: a aprova, r vai ao motivo da rejeição, j próximo, k anterior.
  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey || event.metaKey || event.altKey || typing(event.target)) return;
    var key = event.key.toLowerCase();
    if (key === "r") {
      var reason = root.querySelector("[data-reject-reason]");
      if (reason) {
        event.preventDefault();
        reason.focus();
      }
      return;
    }
    var control = root.querySelector('[data-shortcut="' + key + '"]');
    if (control && !control.disabled) {
      event.preventDefault();
      control.click();
    }
  });

  // Enviar uma vez: o botão fica ocupado e desligado até a página responder.
  root.querySelectorAll("form[data-submit-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      form.querySelectorAll('button[type="submit"]').forEach(function (button) {
        button.setAttribute("aria-busy", "true");
        window.setTimeout(function () {
          button.disabled = true;
        }, 0);
      });
    });
  });

  // Lote: marcar todos e ligar os botões só com seleção.
  var picks = Array.prototype.slice.call(root.querySelectorAll("[data-pick]"));
  var all = root.querySelector("[data-select-all]");
  var buttons = root.querySelectorAll("[data-batch-button]");
  function refresh() {
    var count = picks.filter(function (pick) {
      return pick.checked;
    }).length;
    buttons.forEach(function (button) {
      button.disabled = count === 0;
    });
    if (all) {
      all.checked = count > 0 && count === picks.length;
      all.indeterminate = count > 0 && count < picks.length;
    }
  }
  picks.forEach(function (pick) {
    pick.addEventListener("change", refresh);
  });
  if (all) {
    all.addEventListener("change", function () {
      picks.forEach(function (pick) {
        pick.checked = all.checked;
      });
      refresh();
    });
  }

  // Regra de campo: o trecho selecionado no texto lido vira o valor da regra.
  var text = root.querySelector("[data-text]");
  var input = root.querySelector("[data-selected-input]");
  var output = root.querySelector("[data-selected-output]");
  var ruleButton = root.querySelector("[data-rule-button]");
  if (text && input && output && ruleButton) {
    var update = function () {
      var selection = window.getSelection();
      var value = selection ? selection.toString().replace(/\s+/g, " ").trim() : "";
      var inside = selection && selection.rangeCount && text.contains(selection.anchorNode);
      if (!inside || value.length < 4 || value.length > 200) {
        input.value = "";
        ruleButton.disabled = true;
        output.textContent = "Selecione um trecho";
        return;
      }
      input.value = value;
      ruleButton.disabled = false;
      output.textContent = value;
    };
    text.addEventListener("mouseup", update);
    text.addEventListener("keyup", update);
  }
})();
