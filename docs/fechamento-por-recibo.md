# Fechamento por Recibo (módulo `closing`)

Porte do módulo `apps/fechamento` do HubFedrizzi para o CICA como função **global**: qualquer escritório
pode ter, mas o módulo nasce **desligado** (`NOT_SELF_SERVICE_MODULE_CODES`) e só liga por decisão
(console da plataforma ou `provision_office`).

## Fluxo

1. **Enviar** (`/app/fechamento/`): PDF, XML ou TXT, até 10 MB, um registro por conteúdo (SHA-256).
2. **Ler** (`apps/closing/engine.py`): texto do PDF em modo layout (colunas ficam juntas), âncoras
   insensíveis a acento/caixa/quebra de linha, variantes `A || B`, N-ésimo valor, soma de N valores,
   coluna de cabeçalho quebrado, identidade do contribuinte por XML do eSocial/REINF, CNPJ alfanumérico.
   Escaneado: OCR local do Triagem (`TRIAGE_OCR_ENABLED`, política e orçamento do escritório).
3. **Identificar o layout**: todos os identificadores (`marker`, `marker_2`…) precisam aparecer; o mais
   específico vence; empate ou nenhum → **quarentena** com o motivo.
4. **Identificar a empresa** só dentro do escritório: CNPJ, raiz, IE ou IM. Zero ou mais de uma → quarentena.
5. **Conferir** (`services.confer`): valor do documento × referência.
   - `Guia da Central`: `hub.FiscalGuide` da empresa, tipo e competência (uma só; mais de uma → não chuta).
   - `Outro documento`: documento par lido (ex.: EFD ICMS × guia estadual; ISS × DMS).
   - Tolerância por layout (padrão R$ 0,99: centavos variam entre recibo e guia).
   - Zero (se o layout permitir) baixa sem guia; `Só leitura` baixa pela leitura.
6. **Baixar no checklist** (`checklist.py`): `OperationalActivity` do mesmo escritório, empresa,
   `ActivityTemplate.code` (`activity_code` do layout) e competência. Evidência `source` (ou `document`
   quando o item exige confirmação humana); as regras de conclusão do item continuam valendo.
7. **Gate humano**: divergência e falta de referência **não baixam**. Divergência impede o item
   (`blocked`). Uma pessoa aceita (baixa com evidência `human`, motivo obrigatório) ou rejeita.
   Tudo auditado (`closing.*`).

Documento aceito depois pode ser a referência que outro esperava: `reevaluate_waiting` refaz a
conferência na hora; `manage.py closing_reevaluate` cobre a guia que chega depois.

## Telas

`/app/fechamento/` (documentos, filtros, envio), `documentos/<id>/` (leitura, conferência, decisão),
`layouts/` e `layouts/<id>/` (campos, amostra com diagnóstico por campo, ativação com pendências).
Mesmo esqueleto, componentes e tokens da Triagem/Contraprova.

## Entitlement

`ProductModule.Code.CLOSING = "closing"` ("Fechamento por Recibo"). Migrações `hub.0092` (choices) e
`hub.0093` (linha desligada para escritórios que já têm linhas de módulo, como `0077`). O
`provision_office` liga todos os códigos e cria o `Entitlement`: **rodar de novo para
`fedrizzi-contabilidade` liga o módulo**.

## Comandos

```powershell
python manage.py import_closing_layouts --office fedrizzi-contabilidade --file layouts.json [--dry-run]
python manage.py closing_reevaluate [--office fedrizzi-contabilidade]
python manage.py provision_office --name "Fedrizzi Contabilidade" --slug fedrizzi-contabilidade
```

`import_closing_layouts` traz layouts como **rascunho** (ativar na tela depois de ver a amostra).

### Exportar os layouts do HubFedrizzi

No `manage.py shell` do HubFedrizzi:

```python
import json
from apps.fechamento.models import MapeamentoRecibo
dados = {"layouts": [{
    "sigla": m.obrigacao_sigla, "nome": m.nome, "amostra_texto": m.amostra_texto,
    "campos": [{"variavel": c.variavel, "localizador": c.localizador, "ocorrencia": c.ocorrencia,
                "somar": c.somar, "anulado": c.anulado, "custom": c.custom} for c in m.campos.all()],
} for m in MapeamentoRecibo.objects.all()]}
open("layouts.json", "w", encoding="utf-8").write(json.dumps(dados, ensure_ascii=False))
```

Depois de importar, preencher em cada layout o **Item do checklist** (`ActivityTemplate.code` do escritório).

## Fora desta versão

Drive fiscal e arquivo de clientes, fila Redis/pasta única de entrada, Serpro próprio (a referência da
guia vem de `hub.FiscalGuide`/Integra da plataforma), envio ao cliente, e-mail de divergência,
reavaliação em lote por ativação de layout, descarte em massa, DARF com várias receitas, sugestão de
marcadores por IA. Dados históricos (recibos já lidos) são da conversão do importador legado.
