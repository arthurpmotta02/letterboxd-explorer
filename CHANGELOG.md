# Changelog

## 3.0.0 — 2026-07-11

O salto de **descritivo → inferencial/preditivo** e de **relatório → produto**.

### Modelo do gosto (novo)

- **Modelo da nota (ridge)**: efeitos parciais de gênero, década, diretor, duração e popularidade sobre a sua nota, com IC de 95% (forest plot). Substitui comparações marginais enganosas.
- **Anatomia do seu 5★**: importância de cada família de características (queda de R²).
- **Generosidade real**: resíduo do modelo por ano — separa "ficou generoso" de "aprendeu a escolher".
- **Watchlist rankeada**: nota prevista para cada filme da watchlist, treinada no seu histórico (a watchlist agora também é enriquecida via TMDB).
- **Arquétipos do gosto**: k-means + PCA sobre gênero/década/idioma/keywords, com rótulos automáticos.

### Rigor estatístico

- Encolhimento bayesiano + IC de 95% em todas as agregações por grupo (gêneros, décadas).
- Calibração você × TMDB: Spearman separa "régua diferente" de "gosto diferente".
- Sazonalidade testada: heatmap observado/esperado com χ² e p-valor.
- Mudança de ritmo (changepoint) anotada no volume mensal, com p-valor.
- Efeito rewatch (teste t de Welch) no subtítulo de rewatches.
- Aviso de contagem múltipla no boxplot de gêneros.

### Novas análises

- Exploração × explotação: entropia de gêneros por ano + taxa de diretores/países inéditos.
- Mainstream ↔ cult como série temporal com IC.
- Retenção de diretores (quem te fisgou com 3+ filmes).
- Direção feminina ao longo do tempo (campo `gender` do TMDB, com cobertura sinalizada).
- Sentimento das resenhas × nota (léxico pt/en) e palavras-assinatura (frequência × espalhamento).
- "Fora da curva": % de filmes onde sua opinião padronizada destoa do TMDB.

### Design & UX

- Sistema de cor com significado: verde = volume, laranja = suas notas, divergente azul↔laranja (colorblind-safe) só para "acima/abaixo do esperado", sequencial única para heatmaps, categórica Okabe–Ito para gêneros/clusters.
- Curadoria do scroll: seções secundárias colapsam em "mais análises".
- Scrollspy: a navegação lateral destaca a seção ativa.
- Aba persistente na URL (#aba-N).
- Card compartilhável 9:16 com download em PNG (html2canvas).
- Radar com anéis de referência, rede com mais contraste, scatters densos com Viridis e opacidade.

### Engenharia

- `models.py`: ridge, k-means e PCA em numpy puro, sem I/O (testável).
- Validação de schema do export com erro claro se o formato do Letterboxd mudar.
- Cache TMDB versionado (schema v2) com backfill incremental de `gender`.
- `numpy` e `scipy` declarados no pyproject (scipy já era usado).
- +26 testes: propriedades (encolhimento nunca extrapola, entropia em [0, log k], predição dentro da escala) e snapshot estrutural do HTML.

## 2.2.0

- Versão anterior: EDA completo, tema escuro, abas por ano, insights estilo Wrapped, média bayesiana para diretores, rede de colaborações, mapa de países.
