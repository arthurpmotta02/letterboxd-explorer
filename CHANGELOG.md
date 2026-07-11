# Changelog

## 3.1.0 — 2026-07-11

Rigor: de **preditivo → validado**. O modelo agora prova, fora da amostra, que os números que mostra se sustentam.

### Validação e honestidade do modelo

- **Validação cruzada (k-fold)** no modelo da nota: além do R² de treino, o relatório mostra **CV-R²** e **erro médio (MAE) fora da amostra** — o número honesto. O gap treino−CV expõe overfitting.
- **`alpha` do ridge escolhido por validação cruzada** em vez de fixado arbitrariamente.
- **Importância por família medida fora da amostra** (queda de CV-R²): não premia mais famílias com muitos rótulos (diretor, gênero) só por decorarem o treino.
- **Rótulo honesto do intervalo dos coeficientes**: passa a dizer que é o intervalo de *variância* do estimador encolhido, não corrigido pelo viés do ridge.

### Watchlist com incerteza real

- **Intervalo de previsão por filme** (`pred_lo`/`pred_hi`): soma a incerteza dos coeficientes ao ruído residual. Filmes com poucas pistas conhecidas (cold-start, ex.: diretor fora do vocabulário) saem com faixa larga em vez de falsa confiança.

### Novas análises

- **Curva de calibração** predito × real, usando previsões de validação cruzada (sem vazamento): mostra se, quando o modelo prevê 4.5★, você realmente dá ~4.5★.
- **Benchmark não-linear (gradient boosting)**: compara o CV-R² do modelo linear com o de um GBM que capta interações — mede quanto do seu gosto NÃO é aditivo (ex.: drama longo sim, comédia longa não).
- **Watchlist com diversidade (MMR)**: a lista rankeada equilibra nota prevista e variedade, para não devolver vários filmes quase idênticos.
- **Caveat de viés de seleção**: a watchlist agora diz explicitamente que o modelo aprende só com filmes avaliados, então tende ao que você já conhece.

### Refino

- **Clustering (arquétipos)**: só as features contínuas são padronizadas; as binárias ficam 0/1, para não superpesar categorias raras. O número de clusters `k` é escolhido pela **maior silhueta**, não por heurística.
- +7 testes de propriedade: CV-R² ≤ R² de treino, alpha vindo do grid, intervalo de previsão contém a previsão, calibração bem formada.

## 3.0.0 — 2026-07-11

O salto de **descritivo → inferencial/preditivo** e de **relatório → produto**.

### Modelo do gosto (novo)

- **Modelo da nota (ridge)**: efeitos parciais de gênero, década, diretor, duração e popularidade sobre a sua nota, com IC de 95% (forest plot). Substitui comparações marginais enganosas.
- **Anatomia do seu 5★**: importância de cada família de características (queda de R²).
- **Generosidade real**: resíduo do modelo por ano — separa "ficou generoso" de "aprendeu a escolher".
- **Watchlist rankeada**: nota prevista para cada filme da watchlist, treinada no seu histórico (a watchlist agora também é enriquecida via TMDB).
- **Arquétipos do gosto**: KMeans + PCA (scikit-learn) sobre gênero/década/idioma/keywords, com rótulos automáticos.

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

- Sistema de cor com significado, na estética Letterboxd: verde = volume, laranja = suas notas, o par azul/laranja da marca como divergente (colorblind-safe) só para "acima/abaixo do esperado", sequencial única para heatmaps, categórica derivada da família da marca para gêneros/clusters.
- Curadoria do scroll: seções secundárias colapsam em "mais análises"; blocos em ordem narrativa fixa (panorama, tempo, composição, notas, modelo, tendências, pessoas, watchlist).
- Removidos gráficos redundantes com o modelo (nota média crua por ano, boxplot por gênero, nota por duração, orçamento, acumulado).
- Calendário de at