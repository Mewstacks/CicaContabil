"""Versioned legal drafts. Publication requires commercial and legal review."""

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from apps.platform.availability import copilot_is_available
from apps.platform.legal_versions import LEGAL_VERSION
from apps.platform.models import PlatformConfiguration

DOCUMENTS = {
    "termos": {
        "title": "Termos de Uso",
        "sections": [
            (
                "Fornecedora e objeto",
                "A CICA — Central de Inteligência Contábil Avançada é fornecida pela Mewstack "
                "Desenvolvimento de Sistemas Ltda., CNPJ 68.340.160/0001-13. A plataforma reúne "
                "ferramentas para a operação de escritórios contábeis. O acesso é concedido "
                "conforme módulos, usuários autorizados e limites da contratação.",
            ),
            (
                "Cadastro e acesso",
                "O responsável pelo cadastro deve estar autorizado a representar o escritório, "
                "informar dados corretos e manter seus acessos protegidos. A confirmação do "
                "e-mail é necessária. O teste dura 14 dias e não exige cartão nem segundo fator "
                "obrigatório. Após o teste ou contratação, o segundo fator será exigido. Contas "
                "administrativas da plataforma possuem proteção adicional.",
            ),
            (
                "Teste e contratação",
                "O teste possui limites de uso, inclusive de inteligência artificial, informados "
                "antes da ativação. Atingir uma franquia interrompe as operações "
                "correspondentes, sem gerar cobrança automática. O encerramento do teste não "
                "representa contratação automática. Preços, módulos, franquias, excedentes "
                "autorizados, descontos e periodicidade constam da oferta aceita pelo "
                "contratante.",
            ),
            (
                "Pagamentos e cancelamento",
                "A contratação paga depende da aceitação da oferta comercial. O processamento "
                "da cobrança é tratado diretamente pela Mewstack, fora da CICA. A plataforma "
                "não recebe dados de cartão, não inicia cobranças e não realiza renovação "
                "automática. Cancelamento, efeitos sobre o acesso, exportação e eventual "
                "restituição devem ser apresentados antes da contratação, observada a legislação "
                "aplicável. Não se presume renúncia a direitos legalmente assegurados.",
            ),
            (
                "Inteligência artificial",
                "A inferência padrão ocorre em infraestrutura administrada pela Mewstack. Um "
                "provedor externo pode ser acionado exclusivamente como fallback, conforme "
                "configuração, limites e informações de privacidade apresentados ao escritório. "
                "Respostas podem conter erros e devem ser conferidas nas fontes. A IA não "
                "substitui o julgamento nem a responsabilidade técnica do profissional contábil.",
            ),
            (
                "Integrações e aprovação",
                "O escritório deve possuir autorização para conectar seus sistemas e tratar os "
                "dados enviados. Os conectores de bancos externos operam em somente leitura. "
                "Ações sensíveis dentro da CICA exigem aprovação humana e registro de auditoria. "
                "A disponibilidade de terceiros, certificados, permissões e atualização das "
                "fontes pode afetar resultados e prazos.",
            ),
            (
                "Uso permitido e responsabilidades",
                "É vedado contornar controles de acesso, compartilhar credenciais indevidamente, "
                "introduzir código malicioso ou acessar informações de outros clientes. A "
                "Mewstack deve manter os controles acordados e tratar incidentes; o escritório "
                "deve revisar suas entregas, gerenciar seus usuários e comunicar suspeitas de "
                "acesso indevido. Responsabilidades serão apuradas conforme a legislação "
                "aplicável, sem exclusão genérica de responsabilidade da fornecedora.",
            ),
            (
                "Dados e encerramento",
                "Os dados do escritório não se tornam propriedade da Mewstack. O tratamento é "
                "descrito na Política de Privacidade e no anexo contratual. Os prazos de "
                "retenção, exportação e eliminação deverão constar da oferta final, incluindo "
                "obrigações legais e ciclos de backup. Atualizações materiais dos termos serão "
                "versionadas e comunicadas.",
            ),
        ],
    },
    "privacidade": {
        "title": "Política de Privacidade",
        "sections": [
            (
                "Quem trata os dados",
                "A Mewstack administra os dados necessários ao cadastro, relacionamento "
                "comercial, segurança e cobrança da CICA. Nos dados de clientes processados "
                "segundo instruções do escritório, sua atuação como operadora e a atuação do "
                "escritório como controlador dependem da atividade concreta e são detalhadas no "
                "anexo de tratamento.",
            ),
            (
                "Dados e finalidades",
                "Podem ser tratados nome, e-mail, dados cadastrais do CNPJ, informações "
                "contratuais, registros de acesso e auditoria, documentos enviados e dados "
                "autorizados das integrações. As finalidades incluem fornecer a plataforma, "
                "autenticar usuários, prestar suporte, executar contratos, prevenir fraude e "
                "cumprir obrigações legais. Dados de sócios não são necessários ao preenchimento "
                "automático do cadastro.",
            ),
            (
                "Bases de tratamento",
                "Cada finalidade deve ser vinculada à base legal aplicável, incluindo execução "
                "de contrato, obrigação legal e, quando cabível, legítimo interesse ou "
                "consentimento. Dados pessoais sensíveis exigem avaliação específica. "
                "Consentimento para marketing é separado da aceitação contratual e pode ser "
                "revogado.",
            ),
            (
                "Infraestrutura e compartilhamento",
                "A IA padrão é executada em servidores administrados pela Mewstack. Dados "
                "necessários à resposta podem ser enviados ao provedor externo quando o fallback "
                "autorizado for acionado. Serviços de pagamentos, e-mail, hospedagem e "
                "monitoramento também podem processar informações necessárias à sua função. A "
                "relação final de fornecedores, localização e mecanismos de transferência "
                "internacional deve ser informada antes da publicação desta política.",
            ),
            (
                "Proteção e retenção",
                "A plataforma utiliza controles de acesso por organização, criptografia de "
                "campos confidenciais e registros de auditoria. Nenhuma medida elimina "
                "integralmente os riscos. Dados serão conservados conforme finalidade, contrato "
                "e obrigações legais; os prazos específicos e ciclos de eliminação em backups "
                "serão publicados após validação operacional.",
            ),
            (
                "Direitos e contato",
                "O titular pode solicitar confirmação de tratamento, acesso, correção e outros "
                "direitos previstos na LGPD. A Mewstack verificará a identidade de forma "
                "proporcional e encaminhará ao escritório as solicitações relativas a "
                "tratamentos sob sua decisão. Solicitações e incidentes devem ser tratados pelos "
                "canais de privacidade identificados nesta página.",
            ),
            (
                "Cookies",
                "A aplicação utiliza cookies necessários à sessão, segurança e preferências. "
                "Cookies opcionais de análise ou publicidade somente poderão ser ativados com "
                "informação e mecanismo de escolha aplicáveis. Alterações desta política serão "
                "identificadas por versão.",
            ),
        ],
    },
    "tratamento-de-dados": {
        "title": "Anexo de tratamento de dados",
        "sections": [
            (
                "Instruções e finalidade",
                "A Mewstack tratará dados sob responsabilidade do escritório apenas para prestar "
                "os serviços contratados e conforme instruções documentadas e lícitas. O "
                "escritório responde por estabelecer as finalidades e autorizações necessárias "
                "ao envio dos dados de seus clientes.",
            ),
            (
                "Confidencialidade e acesso",
                "O acesso será limitado às pessoas e serviços que necessitem dos dados para suas "
                "funções. Suporte com acesso a dados do escritório deve observar autorização, "
                "escopo e auditoria. Credenciais não devem ser compartilhadas por canais "
                "desprotegidos.",
            ),
            (
                "Suboperadores e transferências",
                "A contratação de fornecedores envolvidos no tratamento deve observar obrigações "
                "compatíveis de proteção, transparência e segurança. Transferências "
                "internacionais devem adotar mecanismo válido conforme a LGPD e regulamentação "
                "aplicável. Fornecedores e regiões efetivos devem integrar a versão final deste "
                "anexo.",
            ),
            (
                "Incidentes e direitos",
                "A Mewstack colaborará com o escritório na apuração de incidentes e atendimento "
                "aos direitos dos titulares, fornecendo as informações necessárias ao "
                "cumprimento das obrigações aplicáveis. Comunicação e preservação de evidências "
                "devem seguir o procedimento operacional de incidentes.",
            ),
            (
                "Devolução, eliminação e evidências",
                "Ao encerrar a prestação, devolução ou eliminação seguirá a instrução válida do "
                "escritório e os prazos contratados, ressalvadas obrigações legais. Registros de "
                "segurança, backups e documentos fiscais possuem finalidades e retenções "
                "próprias, que devem ser discriminadas. A Mewstack fornecerá evidências "
                "proporcionais dos controles acordados.",
            ),
        ],
    },
}


def legal_document(request: HttpRequest, document: str) -> HttpResponse:
    if document not in DOCUMENTS:
        raise Http404
    document_data = DOCUMENTS[document].copy()
    if not copilot_is_available():
        document_data["sections"] = [
            section
            for section in document_data["sections"]
            if section[0] != "Inteligência artificial"
        ]
        document_data["sections"] = [
            (
                title,
                text.replace(
                    (
                        "O teste possui limites de uso, inclusive de inteligência artificial, "
                        "informados antes da ativação. Atingir uma franquia interrompe as "
                        "operações correspondentes, sem gerar cobrança automática. "
                    ),
                    (
                        "Os limites aplicáveis aos módulos disponíveis são informados antes da "
                        "ativação. "
                    ),
                ).replace(
                    (
                        "A IA padrão é executada em servidores administrados pela Mewstack. "
                        "Dados necessários à resposta podem ser enviados ao provedor externo "
                        "quando o fallback autorizado for acionado. "
                    ),
                    (
                        "Os dados são processados apenas pelos serviços necessários aos módulos "
                        "disponíveis. "
                    ),
                ),
            )
            for title, text in document_data["sections"]
        ]
    return render(
        request,
        "hub/legal.html",
        {
            "document": document_data,
            "version": LEGAL_VERSION,
            "provider": PlatformConfiguration.objects.filter(key="default").first(),
        },
    )
