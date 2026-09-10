# Runtime multimodal local

O perfil opcional `ai` acrescenta Ollama e o adaptador multimodal à rede interna
do Compose. O adaptador não publica porta nem armazena anexos. Para PDF, ele
converte no máximo as três primeiras páginas em imagens antes da inferência.

1. Defina `OLLAMA_IMAGE` com um digest aprovado e `LOCAL_MULTIMODAL_MODEL` no
   `.env.cobalchini`.
2. Inicie os serviços: `docker compose --env-file .env.cobalchini -f
   compose.cobalchini.yml --profile ai up -d`.
3. Baixe o modelo em janela de manutenção: `docker compose --env-file
   .env.cobalchini -f compose.cobalchini.yml --profile ai --profile ai-bootstrap
   up multimodal-model-init`.
4. Mantenha `LOCAL_MULTIMODAL_ENDPOINT=http://multimodal:8081` apenas no
   ambiente Docker do HubContador.

O mesmo Ollama pode atender o chat local via
`LOCAL_LLM_ENDPOINT=http://ollama:11434`; o Hub usa a compatibilidade OpenAI
somente na rede interna.

O download do modelo consome armazenamento e rede locais e nunca ocorre durante
o deploy automático. O adaptador usa o endpoint `/api/chat` com imagens base64,
conforme a [documentação de visão do Ollama](https://docs.ollama.com/capabilities/vision).
