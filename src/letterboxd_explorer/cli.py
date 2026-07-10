"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from letterboxd_explorer import __version__, ingest, report, tmdb


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="letterboxd-explorer",
        description="Análise exploratória do seu export do Letterboxd em um "
                    "relatório HTML interativo de arquivo único.",
    )
    ap.add_argument("export", help="ZIP do export do Letterboxd ou pasta com os CSVs")
    ap.add_argument("--tmdb-key", default=os.environ.get("TMDB_API_KEY"),
                    help="Chave da API do TMDB v3 ou token v4 (ou env TMDB_API_KEY)")
    ap.add_argument("-o", "--output", default=None,
                    help="Arquivo HTML de saída (padrão: relatorio_letterboxd.html)")
    ap.add_argument("--year", type=int, default=None,
                    help="Modo retrospectiva: analisa só um ano do diário")
    ap.add_argument("--offline", action="store_true",
                    help="Não consulta a API; usa apenas tmdb_cache.json")
    ap.add_argument("--cache", type=Path, default=tmdb.DEFAULT_CACHE,
                    help="Caminho do cache TMDB (padrão: tmdb_cache.json)")
    ap.add_argument("--refresh", action="append", default=[], metavar="TÍTULO",
                    help="Força rebuscar filmes cujo nome contém o texto "
                         "(útil quando a busca casou com o filme errado; "
                         "pode ser repetido)")
    ap.add_argument("--retry-misses", action="store_true",
                    help="Rebusca no TMDB os filmes que ficaram sem "
                         "correspondência em execuções anteriores")
    ap.add_argument("--save-figs", type=Path, default=None, metavar="PASTA",
                    help="Também exporta as figuras principais como PNG "
                         "(requer: pip install kaleido)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    try:
        frames = ingest.read_export(Path(args.export))
        films = ingest.build_films(frames)
        diary = ingest.build_diary(frames)
        print(f"{len(films)} filmes únicos encontrados no export.")

        if args.year:
            films, diary = ingest.filter_year(films, diary, args.year)
            print(f"Retrospectiva {args.year}: {len(films)} filmes.")

        films = tmdb.enrich(films, args.tmdb_key, args.offline, args.cache,
                            retry_misses=args.retry_misses,
                            refresh=args.refresh)

        default_name = (f"retrospectiva_{args.year}.html" if args.year
                        else "relatorio_letterboxd.html")
        out = Path(args.output or default_name)
        report.build_report(films, diary, frames, out, year=args.year,
                            save_figs=args.save_figs)
        print(f"\n✔ Relatório salvo em: {out.resolve()}")
    except ingest.ExportError as e:
        sys.exit(f"Erro: {e}")


if __name__ == "__main__":
    main()
