# letterboxd-explorer

Você entrega o export oficial da sua conta do Letterboxd e recebe um **relatório HTML interativo em arquivo único**: abre em qualquer navegador, dá para mandar por WhatsApp. O export do Letterboxd traz só título, ano, nota e data; gêneros, diretores, elenco, países, duração e keywords são enriquecidos pela [API do TMDB](https://developer.themoviedb.org/) com cache local.

## Demonstração

> Imagens geradas com `--save-figs docs/figs` (veja Opções) a partir de um export real.

![Calendário de atividade](docs/figs/calendario_atividade.png)

| | |
|---|---|
| ![Sua nota × TMDB](docs/figs/voce_vs_tmdb.png) | ![Maiores divergências](docs/figs/maiores_divergencias.png) |
| ![Notas por gênero](docs/figs/boxplot_generos.png) | ![Perfil por gênero](docs/figs/perfil_por_genero.png) |
| ![Diretores: volume, avaliação e consistência](docs/figs/diretores_volume_avaliacao.png) | ![Rede de colaborações](docs/figs/rede_colaboracoes.png) |
| ![Lançamento × visualização](docs/figs/lancamento_x_visualizacao.png) | ![Popularidade × avaliação](docs/figs/popularidade_x_avaliacao.png) |
| ![Evolução dos gêneros](docs/figs/evolucao_generos.png) | ![Sazonalidade dos gêneros](docs/figs/sazonalidade_generos.png) |

![Mapa de países](docs/figs/mapa_paises.png)

As seções com pôsteres (favoritos mais pessoais, melhor por gênero, joias escondidas) e as abas por ano são interativas: veja no HTML.

## O que o relatório mostra

O HTML é organizado em blocos, com abas por ano no topo (Tudo, 2026, 2025...), atalhos laterais para cada bloco, resumo executivo automático e botão de voltar ao topo. Tudo interativo (hover, zoom) e em um único arquivo.

### Visão geral

* **Cards de destaque**: total de filmes, horas de tela, nota média, rewatches, recorde anual e tamanho da watchlist.
* **Resumo executivo**: uma frase automática com seu gênero dominante, diretor mais constante e nota média.
* **Insights automáticos** (estilo Wrapped): seu dia da semana de cinema, maior maratona de dias seguidos, recorde de filmes em um dia, filme-conforto, defasagem média até assistir, nota mais comum, generosidade vs. TMDB, coeficiente cult (% de filmes pouco votados), saudosismo (pré-1980 vs. pós-2000), contraste entre gêneros ("você avalia Drama 0.8 acima de Ação"), contagem de curtas, resenhas e comentários.
* **Perfil por gênero**: radar com o volume relativo dos seus 8 gêneros mais vistos.

### Linha do tempo

* **Volume mensal** com média móvel de 3 meses para suavizar picos de maratona.
* **Calendário de atividade** estilo GitHub (filmes por semana, ano a ano).
* **Acumulado de visualizações** e **padrão semanal × mensal** (heatmap).

### Suas notas

* **Distribuição das notas** com linha de média.
* **Evolução da nota média** por ano (você está ficando mais generoso?).
* **Sua nota × nota TMDB**: scatter com histogramas marginais e cor pela divergência.
* **Maiores divergências**: barras divergentes (o que você defende e o que não perdoa).
* **Favoritos mais pessoais**: grade de pôsteres dos seus 4.5/5 estrelas mais distantes da nota TMDB (mínimo de 30 votos, para excluir médias sem lastro).
* **Melhor avaliado por gênero**: pôster campeão de cada gênero, com selo.
* **Joias escondidas**: nota alta sua em filmes que pouca gente viu.
* **Popularidade × avaliação**: scatter em escala log com linha de tendência por faixa.

### O que você assiste

* **Décadas de lançamento** (contagem) e **avaliação por década** (bolhas proporcionais).
* **Defasagem lançamento → visualização** com curva de densidade.
* **Lançamento × visualização**: scatter que revela suas fases ("2023 foi meu ano de mergulhar nos anos 70"), colorido pela nota.
* **Gêneros**: contagem, **boxplot de notas por gênero**, **evolução ano a ano** (área empilhada) e **sazonalidade** (terror em outubro?).
* **Keywords (microgêneros)** do TMDB: slow burn, neo-noir, coming of age...
* **Duração**: distribuição com KDE e avaliação por faixa, incluindo curtas (≤40 min).
* **Orçamento de produção**, **raridades do acervo** (pôsteres dos menos votados, com contagem dos zero-votos) e **rewatches mais frequentes**.

### Watchlist e resenhas

* **Crescimento da watchlist** e **filmes há mais tempo esperando**.
* **Vocabulário das resenhas**: palavras mais frequentes, sem stopwords.

### Pessoas e lugares

* **Diretores: volume × avaliação × consistência**: scatter com barras de desvio-padrão (consistente vs. ama-ou-odeia) e cor pela média bayesiana, que desconta amostras pequenas.
* **Atores e atrizes mais frequentes**.
* **Rede de colaborações diretor–ator**: diagrama bipartido das parcerias com 2+ filmes.
* **Mapa-múndi dos países de produção** em escala logarítmica, com os 249 códigos ISO 3166 mapeados (nenhum país é descartado silenciosamente).
* **Idiomas originais** com nomes legíveis.

## Instalação

Requisito: [Python 3.10+](https://www.python.org/downloads/). No Windows, marque **"Add Python to PATH"** durante a instalação.

Baixe este projeto (botão verde **Code** > **Download ZIP**, extraia) e abra um terminal na pasta do projeto.

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install .
```

Se o `Activate.ps1` for bloqueado, rode antes:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Como usar

1. **Exporte seus dados**: em [letterboxd.com](https://letterboxd.com), vá em Settings > Data > **Export your data**. Mova o ZIP baixado para a pasta do projeto (não precisa extrair).
2. **Crie uma chave gratuita do TMDB**: conta em [themoviedb.org/signup](https://www.themoviedb.org/signup), depois Settings > API > Create. Copie a **API Key**.
3. **Rode** (com o venv ativado):

```bash
letterboxd-explorer letterboxd-seuusuario-2026-01-01.zip --tmdb-key SUA_CHAVE
```

Abra o `relatorio_letterboxd.html` gerado. A primeira execução consulta o TMDB (1 a 3 min por 1000 filmes); depois tudo fica em `tmdb_cache.json` e é instantâneo.

### Opções

```
letterboxd-explorer EXPORT [opções]

--tmdb-key CHAVE   chave do TMDB (ou variável de ambiente TMDB_API_KEY)
-o saida.html      nome do arquivo de saída
--year 2025        exporta um HTML separado só com um ano (opcional; o
                   relatório padrão já tem abas por ano)
--offline          usa só o cache local, sem API
--retry-misses     rebusca filmes sem correspondência de execuções anteriores
--cache arquivo    caminho do cache
--save-figs PASTA  exporta as figuras principais como PNG (pip install kaleido)
```

`--save-figs docs/figs` gera 16 PNGs prontos para ilustrar um README ou post, incluindo calendário, radar, scatters, boxplot, rede de colaborações e o mapa.

### Demo sem chave

```bash
python scripts/make_sample_data.py
letterboxd-explorer sample-export --offline -o demo.html
```

## Arquitetura

```mermaid
flowchart LR
    E[Export do Letterboxd] --> I[ingest.py]
    K[Chave TMDB] --> T
    I --> T[tmdb.py<br>enriquecimento] --> S[stats.py<br>analises puras] --> R[report.py<br>Plotly + template]
    S --> N[insights.py] --> R
    T <--> C[(tmdb_cache.json)]
    R --> H[relatorio.html<br>arquivo unico]
```

```
src/letterboxd_explorer/
├── cli.py        # linha de comando
├── ingest.py     # leitura do export (ZIP ou pasta)
├── tmdb.py       # cliente TMDB: cache, retry, rate limit, chave v3 ou token v4
├── stats.py      # análises puras sobre DataFrames (testáveis, sem I/O)
├── insights.py   # frases-insight automáticas
└── report.py     # figuras Plotly e template HTML
```

## Privacidade

Seu histórico é pessoal. O `.gitignore` já impede de subir para o GitHub: `*.zip` (o export), os CSVs do export, `tmdb_cache.json`, os `*.html` gerados e `.env`. A chave do TMDB vai por argumento ou variável de ambiente, nunca em arquivo versionado. Tudo roda na sua máquina; nenhum dado seu sai dela além das consultas de metadados ao TMDB.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check src tests
pytest
```

CI no GitHub Actions roda lint e testes em Python 3.10 e 3.12. Os testes usam fixtures sintéticas: não dependem de dados reais nem de chave de API.

## Decisões técnicas

**HTML de arquivo único, sem framework de relatório.** O objetivo é um artefato que qualquer pessoa abre sem instalar nada; o template é gerado em Python com os gráficos Plotly embutidos e só o plotly.js vem de CDN, mantendo o arquivo leve.

**Enriquecimento paralelo com cache incremental.** O gargalo é a rede, não o processamento: as consultas ao TMDB rodam em 8 threads simultâneas e o cache é salvo periodicamente, então interromper no meio (Ctrl+C) não perde progresso e a próxima execução continua de onde parou.

**Análises desacopladas da renderização.** `stats.py` só transforma DataFrames, o que permite testar cada análise isoladamente e trocar o front-end sem reescrever a lógica.

**Busca com fallback.** O ano do Letterboxd às vezes diverge do TMDB (festival × lançamento comercial); a busca tenta com o ano e repete sem ele. Filme não encontrado não quebra o relatório.

## Por que TMDB e não a API do Letterboxd?

A [API oficial do Letterboxd](https://letterboxd.com/api-beta/) é liberada apenas mediante aprovação e, atualmente, **não concede acesso para projetos de análise e visualização de dados**. A própria página recomenda usar o export oficial da conta para os dados pessoais e o [TMDB](https://developer.themoviedb.org/docs/getting-started) para metadados de filmes: exatamente a arquitetura deste projeto. Se essa política mudar, o plano é migrar o enriquecimento para a API do Letterboxd.

## Análises consideradas e descartadas

**Curva de sobrevivência (Kaplan-Meier) da watchlist.** A ideia seria modelar "quanto tempo um filme sobrevive na watchlist até ser assistido". Descartada por limitação do dado, não da técnica: o `watchlist.csv` só traz a data de adição dos filmes **ainda não assistidos** (censurados); para os que saíram da lista, a data de adição se perde no export. Sem o tempo de entrada do grupo que sofreu o evento, a curva seria enviesada por construção.

## Tratamento de dados ausentes

**Filmes sem nota.** O Letterboxd só permite notas de 0.5★ a 5★ (não existe "nota zero"). Filmes assistidos sem nota entram em todas as contagens (volume, horas, gêneros, países, décadas...), mas são excluídos de qualquer análise de avaliação: sem imputação, o que evita distorcer médias e distribuições.

**Filmes sem correspondência no TMDB.** Ficam de fora apenas das análises enriquecidas (gêneros, diretores, mapa...); o relatório informa no cabeçalho quantos foram enriquecidos. A busca inclui títulos adultos (sem `include_adult`, eles nunca seriam encontrados e sumiriam de todas as análises). Se você rodou uma versão antiga, use `--retry-misses` uma vez para rebuscá-los.

**Filmes com zero votos no TMDB.** Aparecem contabilizados no subtítulo de "Filmes menos conhecidos", mas fora das barras (uma barra de comprimento zero não comunica nada).

**Diário escasso.** Se você marca filmes como vistos mas raramente registra no diário, as análises temporais e as abas por ano usam as datas do `watched.csv` (dia em que o filme foi marcado), descartando dias de importação em massa; as seções afetadas indicam isso no subtítulo.

**Datas.** O parser aceita tanto o formato ISO do export oficial (AAAA-MM-DD) quanto DD/MM/AAAA (arquivos que passaram pelo Excel), detectando automaticamente.

## Licença

MIT. Dados de filmes pelo [TMDB](https://www.themoviedb.org); este produto usa a API do TMDB mas não é endossado ou certificado pelo TMDB. Sem afiliação com o Letterboxd.
