# Deploy no Coolify

O app é **stateless**: legislação, CCTs e modelos de peça já vivem no PostgreSQL com pgvector.
O container só precisa das variáveis de ambiente — nada de volume, nada de ingestão no deploy.

## 1. Variáveis de ambiente

No painel do Coolify, em *Environment Variables*:

| Variável | Obrigatória | Valor |
|---|---|---|
| `OPENAI_API_KEY` | sim | chave da OpenAI |
| `POSTGRES_URL` | sim | banco do ClauseCraft — coleções `legislacao` e `pecas_modelo` (porta 5455) |
| `CCT_POSTGRES_URL` | sim | banco das convenções, do Agente 1.0 — **somente leitura** (porta 5435) |
| `APP_SENHA` | **recomendada** | senha de acesso ao app |
| `LLM_MODEL` | não | `openai/gpt-4o` (padrão) |
| `EMBEDDING_MODEL` | não | `text-embedding-3-small` (padrão) |
| `COLLECTION_NAME` | não | `legislacao` (padrão) |
| `COLLECTION_PECAS` | não | `pecas_modelo` (padrão) |
| `MCP_JUSCRAPER_URL` | não | `https://juscraper.nexusdevhub.com/mcp` (padrão) |
| `TAVILY_API_KEY` | não | habilita a jurisprudência trabalhista |

Sem `APP_SENHA` o app sobe **aberto**: qualquer pessoa com a URL gera peças na sua conta da OpenAI.

## 2. Configuração do serviço

- **Build Pack:** Dockerfile (ou Docker Compose, usando o `docker-compose.yml` do repositório)
- **Porta:** `8501`
- **Health check:** `/_stcore/health`
- **Recursos:** reserve pelo menos 1 GB de RAM — CrewAI e LangChain são pesados na importação

## 3. Banco de dados

Se o Coolify roda no mesmo servidor do PostgreSQL, prefira o host interno na `POSTGRES_URL`
em vez do IP público: o tráfego não sai da máquina e a porta 5455 não precisa ficar exposta.

São **dois bancos**, de propósito:

| Banco | Conteúdo | Acesso |
|---|---|---|
| `POSTGRES_URL` (5455) | `legislacao` (1.259 artigos) e `pecas_modelo` (133 capítulos) | leitura e escrita |
| `CCT_POSTGRES_URL` (5435) | `cct_documentos` e `cct_chunks` — 37 convenções, 3.060 cláusulas | **somente leitura** |

A base de convenções é mantida pelo pipeline do Agente 1.0 e cobre desde 2019, com as regionais
de asseio. O ClauseCraft consome sem escrever: dois ingestores com schemas diferentes gravando na
mesma tabela seria fonte garantida de divergência. Para acrescentar uma CCT, use a ingestão daquele
projeto — o ClauseCraft passa a enxergar na hora.

## 4. Arquitetura de configuração

Nada de `.env` no servidor: todas as variáveis vêm do painel do Coolify. O `load_dotenv()` do
`config.py` só tem efeito na máquina de desenvolvimento — sem o arquivo, ele é inócuo e o
`os.getenv` lê direto do ambiente do container.

O app **confere as variáveis obrigatórias na subida** e, se faltar alguma, mostra na tela qual é,
em vez de quebrar no meio de uma análise. Não há caminho de máquina de desenvolvedor codificado:
`PASTA_PECAS`, que só serve ao preparo local dos modelos, agora exige definição explícita.

## 5. O que fica de fora da imagem

Imagem e repositório carregam só código e os arquivos que o runtime usa: os JSONs da legislação e os
dois `.docx` de timbre. Ficam de fora, tanto do Git quanto da imagem:

- `dados/ccts/` — 16 MB de PDFs de convenção, usados só na ingestão local;
- `dados/pecas_modelo.json` — corpus derivado das peças do escritório: anonimizado, mas ainda assim
  material de cliente, e já presente no banco;
- `.env`, `.pylibs/`, `vectordb/` e `exemplos/`.

Para ingerir uma CCT nova, rode na sua máquina — o container passa a enxergar pelo banco:

O `ingerir_ccts.py` deste repositório está travado justamente para impedir escrita acidental na
base compartilhada.

## 6. Depois de subir

1. Abra a URL e confirme que a trava de senha aparece.
2. Rode um caso de teste; a barra lateral deve mostrar o modelo e a coleção em uso.
3. Se a base não responder, o app avisa na tela em vez de quebrar no meio da análise.
