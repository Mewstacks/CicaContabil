"""Formulários do módulo Rentabilidade."""

from __future__ import annotations

from django import forms

from apps.profitability.models import ProfitabilityConfig


class ProfitabilityConfigForm(forms.ModelForm):  # type: ignore[type-arg]
    """Os parâmetros que entram no custo anual e, por tabela, no custo de todo cliente.

    A fonte de receita e o evento de mensalidade ficam de fora enquanto Q-39
    estiver aberta: oferecer a escolha antes de saber que fonte existe convidaria o
    escritório a armar um contrato que não tem dado do outro lado.
    """

    class Meta:
        model = ProfitabilityConfig
        fields = (
            "margem_alvo_padrao",
            "margem_atencao",
            "minutos_minimos_custo",
            "encargos_percentual",
            "indice_produtividade",
            "dias_uteis_ano",
            "feriados_dias_ano",
            "horas_dia",
            "limiar_divergencia_horas",
            "limiar_divergencia_colaborador",
        )
        labels = {
            "margem_alvo_padrao": "Margem-alvo padrão",
            "margem_atencao": "Limite da faixa de atenção",
            "minutos_minimos_custo": "Minutos mínimos para apurar custo",
            "encargos_percentual": "Encargos sobre salários e 13º",
            "indice_produtividade": "Índice de produtividade",
            "dias_uteis_ano": "Dias úteis no ano",
            "feriados_dias_ano": "Feriados em dias úteis",
            "horas_dia": "Horas por dia",
            "limiar_divergencia_horas": "Divergência de horas por cliente (h)",
            "limiar_divergencia_colaborador": "Divergência de horas por colaborador (h)",
        }
        help_texts = {
            "margem_alvo_padrao": "Fração, não percentual: 0,2000 é 20%.",
            "margem_atencao": "Abaixo desta margem o cliente entra em atenção.",
            "minutos_minimos_custo": (
                "Abaixo deste piso a competência do cliente fica sem custo e sem margem. "
                "Em 0, qualquer minuto vale."
            ),
            "encargos_percentual": "Fração: 0,3500 é 35%.",
            "indice_produtividade": "Quanto do tempo vira trabalho para cliente.",
        }

    def clean_indice_produtividade(self) -> object:
        valor = self.cleaned_data["indice_produtividade"]
        if valor <= 0:
            # Índice zero zera as horas produtivas, e o valor-hora produtivo vira
            # zero para toda a folha — o custo de todo cliente sumiria de uma vez.
            raise forms.ValidationError("O índice precisa ser maior que zero.")
        return valor

    def clean(self) -> dict[str, object]:
        dados = super().clean() or {}
        uteis = dados.get("dias_uteis_ano")
        feriados = dados.get("feriados_dias_ano")
        if uteis is not None and feriados is not None and feriados >= uteis:
            raise forms.ValidationError(
                "Os feriados não podem consumir o ano inteiro: sem dia útil não há "
                "hora para dividir o custo, e o custo por hora de todos zeraria."
            )
        return dados
