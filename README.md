# Projeto Petrova

Pesquisa aplicada sobre **chunking e recuperação de informação em documentos
brasileiros** para sistemas RAG (Retrieval-Augmented Generation).

> O nome é só um codinome de trabalho. O foco é técnico.

---

## Por que esse projeto existe

Sistemas RAG dependem de quebrar documentos em pedaços (*chunks*) que serão
indexados e recuperados depois. Os algoritmos atuais (LangChain, LlamaIndex,
Unstructured) foram **pensados e otimizados em inglês**, em geral em textos
narrativos. Quando aplicados a:

- documentos em **português brasileiro**,
- com muitas **tabelas estruturadas**,
- e formatos típicos do mercado nacional (DRE, balanço, releases CVM/B3,
  laudos, editais),

o resultado é ruim de formas mensuráveis: tabelas quebradas, números sem
unidade, notas de rodapé órfãs, colunas mescladas. Tudo isso degrada a
qualidade das respostas finais do LLM.

A pergunta de pesquisa, hoje, é estreita de propósito:

> **Como construir um pipeline de chunking + retrieval que responda
> corretamente a perguntas numéricas sobre demonstrações financeiras
> e relatórios operacionais de empresas brasileiras listadas?**

Começando estreito, com chance real de gerar evidência empírica antes de
qualquer reivindicação grande.

---

## Estrutura do repositório

```
.
├── README.md                       Este arquivo (visão geral)
├── ROADMAP.md                      Fases do projeto e checkpoints
├── LICENSE                         Licença MIT
├── O problema nao resolvido.md     Notas iniciais (rascunho de pesquisa)
└── tabelabr/                       Código e dados do estudo
    ├── README.md                   Guia de uso do código
    ├── requirements.txt
    ├── data/                       PDFs originais e saídas processadas
    ├── reports/                    Relatórios gerados pelos scripts
    ├── scripts/                    Scripts numerados (01_, 02_, ...)
    └── src/                        Módulos reutilizáveis
```

---

## Estado atual

| Fase | Descrição | Status |
|------|-----------|--------|
| 0 | Provar que o problema existe (rodar baselines em DF reais) | em andamento |
| 1 | Construir benchmark próprio (TabelaBR-50: perguntas com gabarito) | pendente |
| 2 | Atacar o modo de falha dominante com algoritmo próprio | pendente |
| 3 | Avaliação rigorosa vs. baselines | pendente |
| 4 | Documentação, post técnico, repositório público maduro | pendente |

Detalhes em [`ROADMAP.md`](./ROADMAP.md).

---

## Como começar

```powershell
# 1. Clone o repositório
git clone https://github.com/Nishuw/Projeto-Petrova.git
cd Projeto-Petrova

# 2. Setup do ambiente Python (3.11+)
cd tabelabr
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Coloque um PDF de DF real em data/raw/ e rode o baseline
python scripts\01_baseline_pdfplumber.py "data\raw\<seu_arquivo>.pdf"
```

O relatório de saída fica em `tabelabr/reports/`.

---

## Princípios de trabalho

- **Escopo apertado vence escopo amplo.** Resolver uma dor específica de um
  usuário específico em um documento específico vale mais do que uma proposta
  genérica que tenta cobrir tudo.
- **Evidência antes de algoritmo.** Antes de propor uma solução, mostrar com
  dados reais que o problema existe.
- **Métrica verificável por terceiro.** Não "qualidade do chunk"; sim
  "número correto na resposta final".
- **Cada etapa entrega valor.** O benchmark sozinho já é entregável; a análise
  de falhas sozinha já é entregável; o algoritmo é um bônus em cima disso.

---

## Licença

[MIT](./LICENSE).
