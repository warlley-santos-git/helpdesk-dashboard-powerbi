"""
Gera um relatório automático de indicadores de help desk a partir dos CSVs.

Lê dados/chamados.csv e dados/categorias.csv e cria relatorio/relatorio_<data>.md com:
  - Resumo geral (volume, % no SLA, tempo médio, satisfação)
  - Evolução mensal
  - Categorias que mais estouram o SLA (onde agir primeiro)
  - Desempenho por técnico

Uso:
  python scripts/relatorio.py
  python scripts/relatorio.py --ultimos-meses 3
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
PASTA_SAIDA = RAIZ / "relatorio"


def carregar() -> pd.DataFrame:
    chamados = pd.read_csv(
        PASTA_DADOS / "chamados.csv", sep=";", decimal=",", encoding="utf-8-sig",
        parse_dates=["data_abertura", "data_fechamento"],
    )
    categorias = pd.read_csv(PASTA_DADOS / "categorias.csv", sep=";", encoding="utf-8-sig")
    tecnicos = pd.read_csv(PASTA_DADOS / "tecnicos.csv", sep=";", encoding="utf-8-sig")

    df = chamados.merge(categorias, on="categoria", how="left").merge(tecnicos, on="id_tecnico", how="left")
    df["mes"] = df["data_abertura"].dt.to_period("M").astype(str)
    df["no_sla"] = df["tempo_resolucao_h"] <= df["sla_horas"]
    return df


def pct(valor: float) -> str:
    return f"{valor:.1%}".replace(".", ",")


def num(valor: float, casas: int = 0) -> str:
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    linhas = ["| " + " | ".join(str(v) for v in linha) + " |" for linha in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def gerar(df: pd.DataFrame, ultimos_meses: int | None) -> str:
    if ultimos_meses:
        meses = sorted(df["mes"].unique())[-ultimos_meses:]
        df = df[df["mes"].isin(meses)]

    fechados = df[df["status"] == "Fechado"]
    periodo = f"{df['mes'].min()} a {df['mes'].max()}"

    # Resumo
    resumo = [
        f"- **Chamados abertos no período:** {num(len(df))}",
        f"- **Média por mês:** {num(len(df) / df['mes'].nunique())}",
        f"- **Resolvidos dentro do SLA:** {pct(fechados['no_sla'].mean())}",
        f"- **Tempo médio de resolução:** {num(fechados['tempo_resolucao_h'].mean(), 1)} h "
        f"(mediana {num(fechados['tempo_resolucao_h'].median(), 1)} h)",
        f"- **Taxa de reabertura:** {pct(fechados['reaberto'].mean())}",
        f"- **Satisfação média:** {num(df['nota_satisfacao'].mean(), 2)} de 5 "
        f"({pct(df['nota_satisfacao'].notna().mean())} responderam)",
        f"- **Chamados ainda abertos:** {num((df['status'] == 'Aberto').sum())}",
    ]

    # Evolução mensal
    mensal = (
        fechados.groupby("mes")
        .agg(Chamados=("id_chamado", "count"), SLA=("no_sla", "mean"), Tempo=("tempo_resolucao_h", "mean"))
        .reset_index()
    )
    mensal["SLA"] = mensal["SLA"].map(pct)
    mensal["Tempo"] = mensal["Tempo"].map(lambda v: num(v, 1) + " h")
    mensal = mensal.rename(columns={"mes": "Mês", "SLA": "% no SLA", "Tempo": "Tempo médio"})
    mensal["Chamados"] = mensal["Chamados"].map(num)

    # Categorias que mais estouram o SLA
    cat = (
        fechados.groupby(["categoria", "sla_horas"])
        .agg(Chamados=("id_chamado", "count"), Fora=("no_sla", lambda s: (~s).sum()), Tempo=("tempo_resolucao_h", "mean"))
        .reset_index()
        .sort_values("Fora", ascending=False)
    )
    cat["% fora do SLA"] = (cat["Fora"] / cat["Chamados"]).map(pct)
    pior = cat.iloc[0]
    cat = cat.rename(columns={"categoria": "Categoria", "sla_horas": "SLA (h)", "Fora": "Fora do SLA"})
    cat["Tempo médio"] = cat["Tempo"].map(lambda v: num(v, 1) + " h")
    cat = cat[["Categoria", "SLA (h)", "Chamados", "Fora do SLA", "% fora do SLA", "Tempo médio"]]
    cat["Chamados"] = cat["Chamados"].map(num)

    # Técnicos
    tec = (
        fechados.groupby(["nome", "nivel"])
        .agg(Chamados=("id_chamado", "count"), SLA=("no_sla", "mean"), Nota=("nota_satisfacao", "mean"))
        .reset_index()
        .sort_values("Chamados", ascending=False)
    )
    tec["SLA"] = tec["SLA"].map(pct)
    tec["Nota"] = tec["Nota"].map(lambda v: num(v, 2))
    tec["Chamados"] = tec["Chamados"].map(num)
    tec = tec.rename(columns={"nome": "Técnico", "nivel": "Nível", "SLA": "% no SLA", "Nota": "Satisfação"})

    return "\n\n".join([
        f"# Relatório de Help Desk — {periodo}",
        f"Gerado automaticamente em {datetime.now():%d/%m/%Y %H:%M}. Dados fictícios.",
        "## Resumo",
        "\n".join(resumo),
        "## Onde agir primeiro",
        f"A categoria **{pior['categoria']}** concentra mais chamados fora do SLA: "
        f"{num(pior['Fora'])} de {num(pior['Chamados'])} ({pct(pior['Fora'] / pior['Chamados'])}). "
        "Revisar o processo dessa categoria tende a dar o maior ganho de SLA.",
        tabela_md(cat),
        "## Evolução mensal",
        tabela_md(mensal),
        "## Desempenho por técnico",
        tabela_md(tec),
    ]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Relatório automático de help desk.")
    parser.add_argument("--ultimos-meses", type=int, default=None, help="Filtra os N meses mais recentes")
    args = parser.parse_args()

    if not (PASTA_DADOS / "chamados.csv").exists():
        raise SystemExit("Base não encontrada. Rode antes: python scripts/gerar_dados.py")

    texto = gerar(carregar(), args.ultimos_meses)

    PASTA_SAIDA.mkdir(exist_ok=True)
    arquivo = PASTA_SAIDA / f"relatorio_{datetime.now():%Y%m%d}.md"
    arquivo.write_text(texto, encoding="utf-8")
    print(f"Relatório salvo em {arquivo}")


if __name__ == "__main__":
    main()
