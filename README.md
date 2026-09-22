# ClauseCraft BR — Assistente Jurídico com IA (legislação brasileira)

Assistente jurídico multiagente que lê o relato do cliente em linguagem comum, tipifica os fatos
no **Código Penal brasileiro**, pesquisa **jurisprudência nacional** (STF, STJ e tribunais) e redige
a peça correspondente conforme a praxe forense brasileira.

> Este projeto foi adaptado de uma versão originalmente indiana (Indian Penal Code, FIR,
> indiankanoon.org). Toda a base legal, as fontes de pesquisa, os modelos de peça e os prompts
> foram substituídos por seus equivalentes brasileiros.

---

## ⚙️ Como funciona

Um roteador classifica o relato e escolhe a trilha; cada trilha tem quatro agentes.

**Trilha penal**

| Etapa | Agente | O que faz |
|---|---|---|
| 1 | **Triagem** | Organiza o relato em ficha estruturada: fatos, partes, comarca/UF, pendências |
| 2 | **Tipificação penal** | Busca semântica nos artigos do Código Penal e aponta artigos, qualificadoras e penas |
| 3 | **Jurisprudência** | Busca acórdãos direto no site do tribunal via **MCP do juscraper** (24 TJs, TRF3, TRF5) |
| 4 | **Redação** | Notícia-crime, representação, queixa-crime ou notificação extrajudicial |

**Trilha trabalhista**

| Etapa | Agente | O que faz |
|---|---|---|
| 1 | **Triagem** | Mesma ficha: admissão, função, salário, jornada, modalidade de rescisão |
| 2 | **CLT** | Localiza os artigos da CLT que amparam cada pedido |
| 3 | **Convenção coletiva** | Busca as cláusulas da CCT **vigente na data da rescisão**, por categoria |
| 4 | **Jurisprudência** | Súmulas e OJs do TST via busca web — o MCP **não cobre a Justiça do Trabalho** |
| 5 | **Redação** | Reclamação trabalhista no padrão do escritório: CLT dá o fundamento, a CCT dá o percentual, os modelos dão a forma |

A CLT e a CCT são etapas separadas de propósito: quando um único agente fazia as duas buscas,
ele descartava as cláusulas da convenção ao compor a resposta final.

**Base legal indexada:** textos **compilados** baixados do Planalto, com parte, título, capítulo,
seção, rubrica e marcação de revogados:

- **Código Penal** — Decreto-Lei nº 2.848/1940 (434 artigos, 407 vigentes);
- **CLT** — Decreto-Lei nº 5.452/1943 (1.025 artigos, 852 vigentes).

Os dois ficam na coleção `legislacao`, e cada busca filtra pela sigla do diploma — o agente penal
nunca recebe artigo de CLT, e vice-versa.

**Modelos de peça do escritório:** capítulos de reclamações já redigidas, **anonimizados**, na
coleção `pecas_modelo`. O redator trabalhista consulta esses capítulos para seguir a redação da
casa — os modelos dão a forma, o caso dá o conteúdo. Os `.docx` originais **não entram no
repositório**: ficam na pasta apontada por `PASTA_PECAS` e só a versão mascarada é gravada.

**Convenções Coletivas:** 18 CCTs e termos aditivos (SESVESP/vigilância, SIEMACO/asseio,
SINDEEPRES/porteiros, de 2020 a 2026/27) em `dados/ccts/`, quebradas por cláusula nas tabelas
`cct_documentos` e `cct_chunks`. A busca filtra por categoria e por **data de vigência** antes de
ordenar por similaridade — perguntar "qual o adicional de hora extra" com a data da rescisão devolve
a cláusula da convenção que estava em vigor naquela data, não a mais recente.

**Banco vetorial:** PostgreSQL com a extensão **pgvector** — os 407 artigos vigentes ficam na
coleção `codigo_penal` (tabelas `langchain_pg_collection` e `langchain_pg_embedding`), com índice
HNSW por distância de cosseno.

---

## 🔧 Instalação

```bash
pip install -r requirements.txt
```

> Nesta máquina as dependências ficam em `.pylibs` (sem venv):
> `pip install --target .pylibs -r requirements.txt` e depois rode os comandos com
> `PYTHONPATH="$PWD/.pylibs" python ...`.
>
> O banco vetorial é externo (PostgreSQL + pgvector): nada de índice em disco local.

Copie `env_template.txt` para `.env` e preencha:

```
OPENAI_API_KEY=...
TAVILY_API_KEY=...
POSTGRES_URL=postgresql://usuario:senha@host:5432/banco
```

O banco precisa ter a extensão `pgvector` disponível — o próprio `construir_vectordb.py` executa o
`CREATE EXTENSION vector` na primeira indexação (requer usuário com permissão).

Indexe a legislação (uma vez, ~1 minuto):

```bash
python construir_vectordb.py
```

Rode a interface:

```bash
streamlit run app.py
```

Ou pela linha de comando:

```bash
python main.py "descreva o caso aqui"
```

---

## 🖨 Papel timbrado

O cabeçalho (logo) e o rodapé (barra de contatos) das peças do escritório são **imagens**, não
texto — nenhuma saída em Markdown consegue carregá-los. Por isso a entrega final é `.docx`, gerado
sobre `dados/modelo_peca.docx`, que é uma das peças reais com o corpo esvaziado e o timbre,
as margens (3,5 / 3,0 cm) e a fonte Arial 12 preservados.

```bash
python main.py "relato do caso" --saida peca.docx
python gerar_docx.py peca.md peca.docx     # converter um Markdown já gerado
```

Na interface, o botão "Baixar peça timbrada (.docx)" faz a mesma coisa. A primeira página leva logo
e rodapé; as seguintes, só o logo — como no modelo original.

---

## 📄 Modelos de peça

```bash
python preparar_pecas.py            # lê os .docx, mascara, deduplica e gera dados/pecas_modelo.json
python preparar_pecas.py --auditar  # só audita o que a máscara deixou passar, sem gravar
python indexar_pecas.py             # indexa na coleção pecas_modelo
```

O mascaramento troca CPF, CNPJ, RG, PIS, CTPS, CEP, e-mail, telefone, datas completas, endereços,
filiação e nomes de partes por marcadores. Nomes são detectados pela qualificação, pelas linhas em
caixa alta com CNPJ/CPF e pelo nome do arquivo, com filtro de frequência — termo que aparece mais de
12 vezes é vocabulário jurídico, não nome de parte.

A deduplicação mantém uma versão canônica por capítulo: das 175 seções das cinco peças, 24 eram
texto idêntico repetido, e restaram 133 capítulos com suas variantes reais.

**O `--auditar` é parte do processo, não um extra.** Ele lista o que sobrou para conferência humana
antes de qualquer coisa ir para o banco.

---

## 📑 Convenções Coletivas

```bash
python ingerir_ccts.py                 # ingere o que ainda não foi ingerido (idempotente)
python ingerir_ccts.py --so-metadados  # reprocessa vigência/registro sem gerar embeddings
python ingerir_ccts.py --refazer       # apaga tudo e reingere
```

Os metadados saem do próprio PDF, no padrão do sistema Mediador/MTE: número de registro, título e a
janela de vigência declarada na Cláusula Primeira. A ingestão ignora arquivo repetido por hash e
também o mesmo documento salvo com outro nome, comparando o registro no MTE.

Para adicionar uma convenção nova, coloque o PDF em `dados/ccts/<categoria>/` e rode o comando.

---

## 🔄 Atualizar a legislação

O texto do Código Penal muda com frequência. Para trazer a versão vigente do Planalto e reindexar:

```bash
python baixar_legislacao.py && python construir_vectordb.py   # CP e CLT
python baixar_legislacao.py clt                               # só um diploma
```

O download vem do Planalto e não depende de bibliotecas externas de parsing. Para acrescentar um
diploma novo (CF/88, CPC, CDC), basta uma entrada em `DIPLOMAS` no `baixar_legislacao.py` e a sigla
em `DIPLOMAS_INDEXADOS` no `config.py`.

---

## 🗂 Estrutura

```
app.py                     # interface Streamlit (português)
main.py                    # execução por linha de comando
crew.py                    # as duas equipes (penal e trabalhista)
roteador.py                # classifica o relato e escolhe a trilha
config.py                  # modelos, caminhos, fontes de jurisprudência
baixar_legislacao.py       # baixa CP e CLT do Planalto e gera os JSONs em dados/
construir_vectordb.py      # indexa os artigos no PostgreSQL/pgvector
ingerir_ccts.py            # lê as CCTs em PDF, quebra por cláusula e grava no banco
preparar_pecas.py          # mascara e deduplica os modelos de peça do escritório
indexar_pecas.py           # indexa os modelos na coleção pecas_modelo
gerar_docx.py              # converte a peça em Markdown para .docx timbrado
dados/modelo_peca.docx     # timbre do escritório (cabeçalho, rodapé, margens)
cct_store.py               # schema e busca das CCTs (vigência como coluna DATE)
consultar_vectordb.py      # consulta rápida à base (teste)
agents/                    # triagem, tipificação, jurisprudência, redação
tasks/                     # tarefas correspondentes, com prompts em português
tools/                     # buscas: legislação (pgvector), CCT, modelos, acórdãos (MCP) e web
renderizar_modelo.py       # renderiza a inicial a partir do MODELO_PRINCIPAL v17
dados/codigo_penal.json    # Código Penal
dados/clt.json             # CLT
dados/ccts/                # PDFs das convenções coletivas, por sindicato
exemplos_de_relatos.txt    # casos de teste
```

---

## ⚖️ Jurisprudência

A busca de acórdãos usa o **MCP do juscraper** (`MCP_JUSCRAPER_URL`), que raspa o site do próprio
tribunal e devolve ementa, número do processo, câmara, relator e data — sem chave de API.

| Cobertura | Detalhe |
|---|---|
| 24 tribunais de justiça estaduais | acórdãos de 2º grau; o TJSP tem também 1º grau e consulta processual |
| TRF3 e TRF5 | acórdãos de 2º grau |
| Datajud e Comunica CNJ | metadados de processos e publicações do DJEN |
| **TRT e TST** | **não cobertos** — matéria trabalhista depende da busca web (Tavily) |
| TJMG e jus.br | fora do escopo do MCP (captcha e autenticação gov.br) |

O mesmo servidor está registrado em `.mcp.json`, então quem abrir este repositório no Claude Code
consulta os tribunais direto na conversa, sem configurar nada.

Por isso a trilha penal usa o MCP e a trabalhista continua na busca web: citar acórdão de TJ numa
reclamação trabalhista seria citar tribunal sem competência para a matéria.

---

## 🔩 Configuração (via `.env`)

| Variável | Padrão | Função |
|---|---|---|
| `OPENAI_API_KEY` | — | Chave da OpenAI (obrigatória) |
| `LLM_MODEL` | `openai/gpt-4o` | Modelo usado pelos agentes |
| `MCP_JUSCRAPER_URL` | `https://juscraper.nexusdevhub.com/mcp` | MCP de jurisprudência (sem autenticação) |
| `TAVILY_API_KEY` | — | Busca web, usada na jurisprudência trabalhista |
| `EMBEDDING_PROVIDER` | `openai` | `openai` ou `huggingface` (local, sem custo de API) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo de embedding |
| `POSTGRES_URL` | — | Conexão do PostgreSQL com pgvector (obrigatória) |
| `COLLECTION_NAME` | `legislacao` | Coleção da legislação |
| `COLLECTION_PECAS` | `pecas_modelo` | Coleção dos modelos de peça |
| `PASTA_PECAS` | `~/Área de trabalho/enterevista e petição` | Onde estão os `.docx` originais |
| `EMBEDDING_DIM` | `1536` | Dimensão do vetor (deve bater com o modelo de embedding) |
| `TOP_K` | `5` | Artigos retornados por busca |
| `FONTES_JURISPRUDENCIA` | `stf.jus.br,stj.jus.br,jusbrasil.com.br,cnj.jus.br` | Domínios aceitos na pesquisa |

Trocar de provedor ou de modelo de embedding muda a dimensão do vetor e exige reindexar
(`python construir_vectordb.py`, que recria a coleção do zero).

---

## ✅ Verificado nesta adaptação

- `python baixar_codigo_penal.py` → 434 artigos, sem lacunas entre os arts. 1º e 361 e sem duplicatas (27 revogados marcados).
- `python construir_vectordb.py` → 1.259 artigos vigentes (407 do CP e 852 da CLT) no PostgreSQL 18.6
  com pgvector 0.8.6, vetores de 1536 dimensões e índice HNSW.
- Filtro por diploma: "intervalo intrajornada" devolve só CLT (arts. 71, 59, 58);
  "subtrair coisa alheia móvel" devolve só CP (arts. 155, 156, 168).
- Buscas de teste: "arrombou a janela e furtou joias durante o repouso noturno" → arts. 155, 157, 156;
  "golpe do falso funcionário do banco com PIX" → arts. 171, 171-A, 307.
- `python main.py "..."` → fluxo completo gerando notícia-crime endereçada ao Delegado, com fundamento
  no art. 5º, II, do CPP e no art. 157, § 2º, VII, do CP (caso de roubo) e no art. 171, § 2º-A,
  do CP (golpe do PIX).
- Sem `TAVILY_API_KEY`, a etapa de jurisprudência avisa que está indisponível e o fluxo segue.
- `python ingerir_ccts.py` → 18 convenções e 1.346 cláusulas, todas com vigência detectada.
- `python preparar_pecas.py` → 175 capítulos das 5 peças, 133 após deduplicação, sem CPF/CNPJ/
  e-mail/endereço/nome de cliente remanescente e sem termo jurídico apagado por engano.
- Peça gerada com os modelos ligados saiu no padrão da casa ("com fulcro nos artigos 840, § 1°, da
  CLT, c/c 319 do CPC", "Para elucidação dos direitos aqui pleiteados...") e com o piso correto da
  função (R$ 1.789,16, Cláusula Terceira).
- Trilha penal ponta a ponta com o MCP: citou os acórdãos 1532019-77.2023.8.26.0228 (9ª Câmara
  Criminal) e 2175978-49.2026.8.26.0000 (13ª Câmara), ambos reais e retornados pela ferramenta.
- Roteador classificou corretamente 4 relatos de teste (2 penais, 2 trabalhistas).
- Fluxo trabalhista completo para porteiro dispensado em 15/04/2024: citou a CCT SINDEEPRES
  2024, piso de R$ 1.789,16, hora extra de 50% (Cláusula Décima Sexta), adicional noturno de 20%
  (Décima Oitava) e cartão alimentação de R$ 148,94 — todos conferidos contra o texto da convenção.
- Busca por "percentual de hora extra" em vigilância devolve a Cláusula Décima Segunda da CCT
  2024/2025 (60%) para uma rescisão em 12/03/2024, e a mesma cláusula da CCT 2021 para 01/06/2021.

---

## 📌 Limites atuais

- `Termo Aditivo Convencao Coletiva 2023.pdf` (SESVESP) é PDF escaneado e não foi ingerido —
  precisa de OCR. As outras 18 convenções entraram.
- O mascaramento das peças é heurístico. Nos cinco arquivos não sobrou CPF, CNPJ, e-mail, data,
  endereço nem nome de parte, mas **arquivo novo pede `--auditar` antes de indexar**. Nomes de
  ministros do TST em citações de jurisprudência são mantidos de propósito.
- Tabela de piso salarial é o ponto fraco da busca semântica: a tabela de salários profissionais é
  densa e afunda no ranking frente a cláusulas genéricas de "salário normativo". A busca de CCT usa
  janela maior para compensar, mas **o piso da função merece conferência humana**.

- A base indexada cobre **apenas o Código Penal**. Legislação extravagante (Lei nº 11.343/2006,
  Lei Maria da Penha, Estatuto do Desarmamento, CDC, CLT, CTB) ainda não está indexada — o agente
  de tipificação sinaliza quando o caso depende dessas leis.
- Para incluir outro diploma, gere um JSON no mesmo formato de `dados/codigo_penal.json` e
  acrescente-o em `construir_vectordb.py`.
- **Conteúdo gerado por IA não substitui a análise de advogado inscrito na OAB.** Confira sempre o
  texto legal no Planalto e os julgados nos sites oficiais antes de protocolar qualquer peça.
