"""
Gera uma base FICTÍCIA de chamados de help desk para o dashboard em Power BI.

Saída (pasta dados/):
  - chamados.csv   -> tabela fato (1 linha por chamado)
  - tecnicos.csv   -> dimensão técnicos
  - categorias.csv -> dimensão categorias, com o SLA de cada uma

Uso:
  python scripts/gerar_dados.py              # 12 meses, ~2.000 chamados/mês
  python scripts/gerar_dados.py --meses 6 --por-mes 800
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"

# categoria: (SLA em horas, peso de ocorrência, tempo médio de resolução em horas)
CATEGORIAS = {
    "Acesso e senha":        (4,  30, 1.2),
    "E-mail (Outlook)":      (8,  15, 3.0),
    "Teams":                 (8,  10, 2.5),
    "Rede e internet":       (4,  12, 3.5),
    "Instalação de software": (24, 13, 10.0),
    "Hardware":              (48,  8, 20.0),
    "Impressora":            (24,  7, 8.0),
    "Sistema interno":       (8,   5, 6.0),
}

TECNICOS = [
    ("T01", "Técnico 01", "N1"),
    ("T02", "Técnico 02", "N1"),
    ("T03", "Técnico 03", "N1"),
    ("T04", "Técnico 04", "N1"),
    ("T05", "Técnico 05", "N2"),
    ("T06", "Técnico 06", "N2"),
]

PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]
PESOS_PRIORIDADE = [35, 45, 15, 5]
CANAIS = ["Portal", "Telefone", "E-mail", "Teams"]
PESOS_CANAL = [50, 25, 15, 10]
SETORES = ["Operações", "Financeiro", "RH", "Comercial", "Jurídico", "Diretoria"]
PESOS_SETOR = [55, 12, 8, 15, 5, 5]


def horario_comercial(inicio: datetime) -> datetime:
    """Sorteia um horário de abertura entre 7h e 19h, de segunda a sábado."""
    while True:
        dia = inicio + timedelta(days=random.randint(0, 30))
        if dia.weekday() < 6:
            return dia.replace(hour=random.randint(7, 18), minute=random.randint(0, 59), second=0)


def gerar_chamados(meses: int, por_mes: int, semente: int) -> pd.DataFrame:
    random.seed(semente)
    hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nomes_cat = list(CATEGORIAS)
    pesos_cat = [CATEGORIAS[c][1] for c in nomes_cat]
    linhas = []
    numero = 100000

    for m in range(meses, 0, -1):
        inicio_mes = (hoje - timedelta(days=30 * m)).replace(day=1)
        qtd = int(por_mes * random.uniform(0.85, 1.15))

        for _ in range(qtd):
            numero += 1
            categoria = random.choices(nomes_cat, pesos_cat)[0]
            sla_h, _, media_h = CATEGORIAS[categoria]
            prioridade = random.choices(PRIORIDADES, PESOS_PRIORIDADE)[0]
            abertura = horario_comercial(inicio_mes)

            # Críticos são resolvidos mais rápido; o resto segue uma distribuição exponencial
            fator = {"Crítica": 0.4, "Alta": 0.7, "Média": 1.0, "Baixa": 1.3}[prioridade]
            horas = max(0.1, random.expovariate(1 / (media_h * fator)))

            # N2 pega mais chamados complexos
            nivel = "N2" if categoria in ("Hardware", "Rede e internet", "Sistema interno") and random.random() < 0.6 else "N1"
            tecnico = random.choice([t for t in TECNICOS if t[2] == nivel])[0]

            # Chamados muito recentes podem estar abertos
            aberto = abertura > hoje - timedelta(days=3) and random.random() < 0.4
            fechamento = None if aberto else abertura + timedelta(hours=horas)

            linhas.append({
                "id_chamado": f"CH{numero}",
                "data_abertura": abertura,
                "data_fechamento": fechamento,
                "categoria": categoria,
                "prioridade": prioridade,
                "canal": random.choices(CANAIS, PESOS_CANAL)[0],
                "setor_solicitante": random.choices(SETORES, PESOS_SETOR)[0],
                "id_tecnico": tecnico,
                "status": "Aberto" if aberto else "Fechado",
                "reaberto": (not aberto) and random.random() < 0.04,
                "nota_satisfacao": None if aberto or random.random() < 0.55 else random.choices([1, 2, 3, 4, 5], [2, 3, 10, 35, 50])[0],
            })

    df = pd.DataFrame(linhas).sort_values("data_abertura").reset_index(drop=True)
    df["tempo_resolucao_h"] = ((df["data_fechamento"] - df["data_abertura"]).dt.total_seconds() / 3600).round(2)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera base fictícia de chamados.")
    parser.add_argument("--meses", type=int, default=12)
    parser.add_argument("--por-mes", type=int, default=2000)
    parser.add_argument("--semente", type=int, default=42, help="Mesma semente = mesmos dados")
    args = parser.parse_args()

    PASTA_DADOS.mkdir(exist_ok=True)

    chamados = gerar_chamados(args.meses, args.por_mes, args.semente)
    tecnicos = pd.DataFrame(TECNICOS, columns=["id_tecnico", "nome", "nivel"])
    categorias = pd.DataFrame(
        [(c, v[0]) for c, v in CATEGORIAS.items()], columns=["categoria", "sla_horas"]
    )

    chamados.to_csv(PASTA_DADOS / "chamados.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M")
    tecnicos.to_csv(PASTA_DADOS / "tecnicos.csv", index=False, sep=";", encoding="utf-8-sig")
    categorias.to_csv(PASTA_DADOS / "categorias.csv", index=False, sep=";", encoding="utf-8-sig")

    print(f"{len(chamados):,} chamados gerados em {PASTA_DADOS}".replace(",", "."))


if __name__ == "__main__":
    main()
