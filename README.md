# letterboxd-explorer

[![CI](https://github.com/arthurpmotta02/letterboxd-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/arthurpmotta02/letterboxd-explorer/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

> Do export do Letterboxd a um relatório HTML interativo de arquivo único: retrato completo do seu histórico, modelo estatístico do seu gosto e watchlist rankeada pela nota que você provavelmente daria.

## Sumário

* [Proposta](#proposta)
* [Demonstração](#demonstração)
* [O que o relatório mostra](#o-que-o-relatório-mostra)
* [Instalação](#instalação)
* [Como usar](#como-usar)
* [Arquitetura](#arquitetura)
* [Metodologia](#metodologia)
* [Privacidade](#privacidade)
* [Desenvolvimento](#desenvolvimento)
* [Decisões técnicas](#decisões-técnicas)
* [Licença](#licença)

## Proposta

O Letterboxd mostra *o que* você assistiu; este projeto tenta explicar *como você assiste*, e prever o que vem a seguir. A proposta tem três camadas:

1. **Retrato descritivo**: volume, ritmo, calendário, gêneros, décadas, países e pessoas. O "Wrapped" completo do seu histórico, navegável, em um único HTML que abre em qualquer navegador.
2. **Inferência honesta**: em vez de comparar médias cruas (que confundem gosto com composição do acervo), um modelo estatístico isola o efeito de cada característica na sua nota; toda média vem com intervalo de confiança, e afirmações como "terror em outubro" passam por teste de hipótese antes de virar frase.
3. **Predição acionável**: o mesmo modelo treinado nas suas notas ordena a sua watchlist pela nota que você provavelmente daria. O relatório termina respondendo "o que eu assisto agora?".

Tudo a partir de dois insumos apenas: o export oficial do Letterboxd (título, ano, nota, data) e a API pública do TMDB (gêneros, elenco, países, duração, votos), com cache local. Nenhum dado seu sai da sua máquina.

## Demonstração

> Imagens geradas com `--save-figs docs/figs` a partir de um export real.

![Calendário de atividade](docs/figs/calendario_atividade.png)

| | |
|---|---|
| ![Modelo do gosto: efeitos parciais](docs/figs/modelo_do_gosto.png) | ![Anatomia do seu 5 estrelas](docs/figs/anatomia_5_estrelas.png) |
| ![Nota por gênero com incerteza](docs/figs/nota_genero_incerteza.png) | ![Generosidade real ao longo do tempo](docs/figs/generosidade_real.png) |
| ![Arquétipos do gosto](docs/figs/arquetipos_gosto.png) | ![Exploração e explotação](docs/figs/exploracao_explotacao.png) |
| ![Sua nota vs. TMDB](docs/figs/voce_vs_tmdb.png) | ![Distribuição das notas](docs/figs/distribuicao_notas.png) |
| ![Sazonalidade testada](docs/figs/sazonalidade_generos.png) | ![Mainstream vs. cult](docs/figs/mainstream_cult.png) |
| ![Diretores: volume, avaliação e consistência](docs/figs/diretores_volume_avaliacao.png) | ![Rede de colaborações](docs/figs/rede_colaboracoes.png) |
| ![Lançamento vs. visualização](docs/figs/lancamento_x_visualizacao.png) | ![Popularidade vs. avaliação](docs/figs/popularidade_x_avaliacao.png) |
| ![Evolução dos gêneros](docs/figs/evolucao_generos.png) | ![Sentimento das resenhas vs. nota](docs/figs/sentimento_resenhas.png) |

![Mapa de países](docs/figs/mapa_paises.png)

As seções com pôsteres (favoritos mais pessoais, melhor por gênero, joias escondidas, watchlist rankeada) e as abas por ano são interativas: veja no HTML.

## O que o relatório mostra

Os blocos seguem uma narrativa: panorama, quando você assiste, o que assiste, como avalia, o modelo do gosto, tendências, pessoas e lugares, e o que vem a seguir. O essencial abre expandido; o secundário fica em "mais análises" (colapsável). Navegação lateral com indicador de seção ativa, abas por ano com estado persistente na URL e card 9:16 para stories com download em PNG.

### Visão geral

* **Cards de destaque**: total de filmes, horas de tela, nota média, rewatches, recorde anual e tamanho da watchlist.
* **Insights automáticos**: seu dia de cinema, maratonas, filme-conforto, coeficiente cult, saudosismo, grau de "fora da curva" vs. TMDB, entre outros.
* **Perfil por gênero**: radar com o volume relativo dos seus 8 gêneros mais vistos.

### Linha do tempo

* **Volume mensal** com média móvel e, quando houver, o ponto de **mudança de ritmo** detectado por changepoint (com p-valor).
* **Calendário de atividade** estilo GitHub (filmes por semana, ano a ano).
* **Padrão semanal e mensal** (heatmap dia da semana por mês).

### O que você assiste

* **Décadas de lançamento**, **defasagem lançamento até visualização** e **lançamento vs. visualização** (as suas "fases").
* **Gêneros**: contagem, **evolução ano a ano** e **sazonalidade testada**: heatmap de observado/esperado com teste qui-quadrado ("outubro tem 2.3x mais terror, p < 0.01"), não só impressão visual.
* **Keywords (microgêneros)**, **duração**, **raridades do acervo** e **rewatches** (com teste: você avalia rewatch diferente de primeira sessão?).

### Suas notas

* **Distribuição das notas** com linha de média.
* **Sua nota vs. nota TMDB** com calibração honesta: Spearman separa "régua diferente" de "gosto diferente".
* **Maiores divergências** em azul e laranja (seguro para daltônicos): o que você defende e o que não perdoa.
* **Nota por gênero com incerteza**: encolhimento bayesiano e IC de 95%; onde as barras se sobrepõem, a diferença não é conclusiva.
* **Avaliação por década**, **favoritos mais pessoais**, **melhor por gênero**, **joias escondidas** e **popularidade vs. avaliação**.

### Modelo do gosto

* **O que de fato eleva a sua nota**: forest plot dos efeitos parciais (gênero, década, diretor, duração, popularidade) com IC de 95%.
* **Anatomia do seu 5 estrelas**: importância de cada família de características.
* **Generosidade real**: sua generosidade ao longo do tempo, descontado o efeito de "escolher filmes melhores".
* **Watchlist rankeada pelo seu gosto**: a resposta para "o que assistir a seguir".
* **Arquétipos do seu gosto**: clusters interpretáveis (KMeans + PCA, scikit-learn).

### Exploração e nicho

* **Exploração vs. explotação**: entropia de gêneros por ano e taxa de diretores/países inéditos.
* **Mainstream vs. cult** como série temporal com IC.
* **Quem te fisgou**: os diretores que você voltou a ver (3+ filmes), nome a nome, coloridos pela sua nota.
* **Direção feminina ao longo do tempo** (campo `gender` do TMDB, com cobertura sinalizada).

### Pessoas e lugares

* **Diretores: volume, avaliação e consistência** com barras de desvio-padrão e média bayesiana.
* **Rede de colaborações diretor-ator**, **mapa-múndi de países** (escala log, 249 códigos ISO mapeados), **atores mais frequentes** e **idiomas**.

### Watchlist e resenhas

* **Crescimento da watchlist** e **filmes há mais tempo esperando**.
* **O que você escreve vs. a nota que você dá**: sentimento léxico de cada resenha contra a estrela.
* **Suas palavras-assinatura**: termos frequentes e espalhados por muitas resenhas.

## Instalação

Requisito: [Python 3.10+](https://www.python.org/downloads/). No Windows, marque **"Add Python to PATH"** durante a instalação.

Baixe este projeto (botão verde **Code** > **Download ZIP**, extraia) e abra um terminal na pasta do projeto.

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install .
```

Se o `Activate.ps1` for bloqueado, rode antes: `Set-ExecutionPolicy -Scope Process Bypass`

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Como usar

1. **Exporte seus dados**: em [letterboxd.com](https://letterboxd.com), vá em Settings > Data > **Export your data**. Mova o ZIP baixado para a pasta do projeto (não precisa extrair). Atenção: o export completo pode exigir assinatura Pro; contas free têm acesso limitado ao recurso.
2. **Crie uma chave gratuita do TMDB**: conta em [themoviedb.org/signup](https://www.themoviedb.org/signup), depois Settings > API > Create. Copie a **API Key**.
3. **Rode** (com o venv ativado):

```bash
letterboxd-explorer letterboxd-seuusuario-2026-01-01.zip --tmdb-key SUA_CHAVE
```

Abra o `relatorio_letterboxd.html` gerado. A primeira execução consulta o TMDB (1 a 3 min por 1000 filmes, incluindo a watchlist); depois tudo fica em `tmdb_cache.json` e é instantâneo.

### Opções

```
letterboxd-explorer EXPORT [opções]

--tmdb-key CHAVE   chave do TMDB (ou variável de ambiente TMDB_API_KEY)
-o saida.html      nome do arquivo de saída
--year 2025        exporta um HTML separado só com um ano (opcional; o
                   relatório padrão já tem abas por ano)
--offline          usa só o cache local, sem API
--retry-misses     rebusca filmes sem correspondência de execuções anteriores
--refresh TÍTULO   força rebuscar um filme casado com o registro errado
--cache arquivo    caminho do cache
--save-figs PASTA  exporta as figuras principais como PNG (pip install kaleido)
```

`--save-figs docs/figs` gera os PNGs prontos para ilustrar um README ou post, incluindo o modelo do gosto, calendário, radar, rede de colaborações e o mapa.

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
    S --> M[models.py<br>ridge, KMeans, PCA] --> R
    S --> N[insights.py] --> R
    T <--> C[(tmdb_cache.json)]
    R --> H[relatorio.html<br>arquivo unico]
```

```
src/letterboxd_explorer/
├── cli.py        # linha de comando
├── ingest.py     # leitura do export (ZIP ou pasta) + validação de schema
├── tmdb.py       # cliente TMDB: cache versionado, retry, rate limit, v3/v4
├── stats.py      # análises puras sobre DataFrames (testáveis, sem I/O)
├── models.py     # modelagem: ridge analítico + scikit-learn (sem I/O)
├── insights.py   # frases-insight automáticas
└── report.py     # figuras Plotly e template HTML
```

## Metodologia

Três princípios guiam as análises: **mostrar incerteza** (média sem intervalo de confiança em amostra pequena é ruído travestido de insight), **separar gosto de composição** ("você gosta mais de Drama" pode ser só "você viu mais Drama bom") e **curadoria** (o essencial expandido, o secundário sob demanda).

### O modelo da nota

A peça central é uma regressão ridge com a sua nota como resposta e, como preditores, dummies de gênero, década, diretores recorrentes, idioma e ano em que você assistiu, mais duração e popularidade (log de votos) como contínuas. Três propriedades importam:

1. Os coeficientes são **efeitos parciais**: o "bônus de Drama" é estimado controlando por década, diretor e tudo o mais, o que também corrige a contagem múltipla de filmes com vários gêneros.
2. A penalização $\alpha$ **encolhe amostras pequenas**, cumprindo o papel de um prior bayesiano: um diretor com 3 filmes não ganha efeito gigante por sorte.
3. O mesmo modelo é reutilizado três vezes: coeficientes viram o forest plot, a queda de $R^2$ ao remover cada família vira a "anatomia do 5 estrelas", e a predição sobre a watchlist vira o ranking do que assistir.

Os intervalos exibidos são ICs de 95% aproximados, com

$$\widehat{\mathrm{Var}}(\hat\beta) = \hat\sigma^2 \, A^{-1} X^\top X \, A^{-1}, \qquad A = X^\top X + \alpha I.$$

O ridge é resolvido em forma fechada (numpy) porque o scikit-learn não expõe erros-padrão de coeficientes; clustering e projeção usam scikit-learn (KMeans com k-means++ e PCA).

### Generosidade sem viés de seleção

A curva ingênua de "nota média por ano" sobe tanto se você ficou generoso quanto se aprendeu a escolher melhor. O relatório usa o **resíduo do modelo** (nota observada menos nota prevista pelas características do filme, sem os dummies de ano): o que sobra é generosidade de fato, ano a ano, com IC.

### Incerteza e testes em tudo

Médias por grupo recebem **encolhimento bayesiano**

$$\tilde\mu_g = \frac{n_g \bar y_g + m \bar y}{n_g + m}$$

e IC de 95%; onde as barras se sobrepõem, o texto diz que a diferença não é conclusiva. A sazonalidade gênero por mês é um **teste qui-quadrado de independência** com heatmap de observado/esperado. A mudança de ritmo no volume mensal é um **changepoint por segmentação binária** validado com teste t de Welch; rewatch vs. primeira sessão idem. Na comparação com o TMDB, **Spearman sobre notas padronizadas** separa "minha régua é mais dura" (offset médio) de "meu ranking discorda" (correlação), já que escalas 0.5 a 5 e 0 a 10 não são comparáveis por subtração direta.

### Watchlist, clusters e texto

A watchlist é enriquecida no TMDB e pontuada pelo modelo; a predição nunca usa os dummies de "ano em que viu" (não se prevê o passado). Os **arquétipos** vêm de KMeans sobre gênero, década, idioma e keywords padronizados, projetados em 2D por PCA, com rótulos extraídos das features que mais distinguem cada cluster. Nas resenhas, o sentimento é **léxico** (listas pt/en compactas, sinalizado como heurístico) e as palavras-assinatura ponderam frequência por espalhamento, $\mathrm{tf} \cdot \log(1+\mathrm{df})$, para que uma resenha longa não domine o ranking. A variedade anual de repertório usa entropia de Shannon normalizada, $H/\log k \in [0, 1]$.

### O que o dado não permite

Curva de sobrevivência da watchlist ficou de fora: o export não traz a data de adição dos filmes que *saíram* da lista, o que enviesaria a curva por construção. O campo `gender` do TMDB é incompleto e binário-centrado; a seção de direção feminina exibe a cobertura do dado e pede leitura como aproximação.

## Privacidade

Seu histórico é pessoal. O `.gitignore` já impede de subir para o GitHub: `*.zip` (o export), os CSVs, `tmdb_cache.json`, os `*.html` gerados e `.env`. A chave do TMDB vai por argumento ou variável de ambiente, nunca em arquivo versionado. Tudo roda na sua máquina; nenhum dado seu sai dela além das consultas de metadados ao TMDB.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check src tests
pytest
```

CI no GitHub Actions roda lint e testes em Python 3.10 e 3.12. Os testes usam fixtures sintéticas (incluindo dados com sinal plantado para validar que o modelo o recupera) e testes de propriedade: o encolhimento nunca extrapola o intervalo entre a média do grupo e a global, a entropia fica em $[0, \log k]$, a nota prevista fica na escala 0.5 a 5.

## Decisões técnicas

**HTML de arquivo único, sem framework de relatório.** O objetivo é um artefato que qualquer pessoa abre sem instalar nada; o template é gerado em Python com os gráficos Plotly embutidos e só o plotly.js vem de CDN.

**Sistema de cor com significado, na estética Letterboxd.** Verde da marca para volume/contagem, laranja para as suas notas, e o próprio par azul/laranja da marca como escala divergente (que também é segura para daltônicos), reservada para "acima/abaixo do esperado". Sequencial única para intensidade; categórica derivada da família da marca para gêneros e clusters.

**Enriquecimento paralelo com cache incremental e versionado.** As consultas ao TMDB rodam em 8 threads e o cache é salvo periodicamente: interromper no meio não perde progresso. O cache tem schema versionado; campos novos (como `gender`) são preenchidos por backfill sem rebuscar tudo.

**Análises desacopladas da renderização.** `stats.py` e `models.py` só transformam DataFrames, sem I/O, o que permite testar cada análise isoladamente.

**Validação de schema na entrada.** Se o formato do export mudar, o erro é imediato e legível (essa validação já pegou um caso real: `likes/reviews.csv` do próprio export tem outro formato e sobrescrevia as resenhas).

**Busca com fallback.** O ano do Letterboxd às vezes diverge do TMDB; a busca tenta com o ano e repete sem ele. Filme não encontrado não quebra o relatório.

## Por que TMDB e não a API do Letterboxd?

A [API oficial do Letterboxd](https://letterboxd.com/api-beta/) é liberada mediante aprovação e atualmente não concede acesso para projetos de análise de dados. A própria página recomenda usar o export oficial para os dados pessoais e o [TMDB](https://developer.themoviedb.org/docs/getting-started) para metadados de filmes: exatamente a arquitetura deste projeto.

## Tratamento de dados ausentes

**Filmes sem nota** entram em todas as contagens, mas ficam fora das análises de avaliação: sem imputação. **Filmes sem correspondência no TMDB** ficam fora apenas das análises enriquecidas; o cabeçalho informa quantos foram enriquecidos e `--retry-misses` rebusca. **Diário escasso**: se você marca filmes como vistos mas raramente usa o diário, as análises temporais usam as datas do `watched.csv`, descartando dias de importação em massa (as seções afetadas avisam no subtítulo). **Datas** em ISO ou DD/MM/AAAA são detectadas automaticamente. **Anos sem atividade** aparecem como linhas vazias no calendário, sem fundir visualmente os vizinhos.

## Licença

MIT. Dados de filmes pelo [TMDB](https://www.themoviedb.org); este produto usa a API do TMDB mas não é endossado ou certificado pelo TMDB. Sem afiliação com o Letterboxd.
