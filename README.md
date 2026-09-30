# Dashboard de Help Desk (Power BI + Python)

Indicadores de uma central de suporte: volume de chamados, SLA, tempo de resolução, reabertura e satisfação. Os dados são **fictícios**, gerados por um script Python que simula cerca de 2.000 chamados por mês.

O projeto tem duas partes:

1. **Python:** gera a base de dados e produz um relatório automático em Markdown
2. **Power BI:** dashboard interativo em modelo estrela, com medidas DAX

## Perguntas que o dashboard responde

- Estamos cumprindo o SLA? Em quais categorias estouramos mais?
- O volume de chamados está subindo ou caindo mês a mês?
- Quanto tempo levamos, em média e na mediana, para resolver?
- Quais técnicos e níveis (N1/N2) concentram mais atendimentos?
- Os usuários estão satisfeitos?

## Estrutura

```
helpdesk-dashboard-powerbi/
├── dados/
│   ├── chamados.csv       # fato: 1 linha por chamado (~23 mil linhas)
│   ├── categorias.csv     # dimensão: categoria + SLA em horas
│   └── tecnicos.csv       # dimensão: técnico + nível
├── scripts/
│   ├── gerar_dados.py     # gera a base fictícia
│   └── relatorio.py       # gera o relatório automático
├── relatorio/             # exemplo de relatório gerado
└── powerbi/
    ├── medidas.dax        # todas as medidas DAX comentadas
    └── helpdesk.pbix      # arquivo do dashboard
```

## Modelo de dados (estrela)

```
   dTecnicos          dCalendario          dCategorias
  (id, nome, nível)   (data, mês, ano)     (categoria, SLA)
          \                 |                  /
           \                |                 /
            └──────── fChamados (fato) ──────┘
              id, abertura, fechamento, prioridade,
              canal, setor, status, tempo, nota
```

## Como rodar a parte em Python

```bash
pip install -r requirements.txt

# Gera 12 meses de dados (mesma semente = mesmos dados)
python scripts/gerar_dados.py

# Relatório com todos os meses ou só os últimos 3
python scripts/relatorio.py
python scripts/relatorio.py --ultimos-meses 3
```

Veja um [exemplo de relatório gerado](relatorio/relatorio_20260930.md).

## Como montar o dashboard no Power BI

1. **Obter dados > Texto/CSV**, carregar os três arquivos da pasta `dados` (delimitador ponto e vírgula)
2. Renomear as tabelas para `fChamados`, `dCategorias` e `dTecnicos`
3. Criar a tabela `dCalendario` e as colunas `data` e `dentro_sla` (código em `powerbi/medidas.dax`)
4. Relacionar: `fChamados[id_tecnico]` → `dTecnicos`, `fChamados[categoria]` → `dCategorias`, `fChamados[data]` → `dCalendario[Date]`
5. Criar as medidas do arquivo `medidas.dax`

### Páginas sugeridas

| Página | Visuais |
| --- | --- |
| Visão geral | Cartões: total, % no SLA, tempo médio, satisfação · Linha: chamados por mês · Barras: fora do SLA por categoria |
| SLA | Matriz categoria × mês com % no SLA e formatação condicional · Medidor com a meta de 90% |
| Equipe | Tabela por técnico: volume, % no SLA, satisfação · Segmentação por nível N1/N2 |

## Prints

_(adicionar prints das páginas do dashboard aqui)_

## O que pratiquei

Python com pandas (geração e tratamento de dados, agregações, relatório automático), modelagem em estrela, DAX (inteligência de tempo, `CALCULATE`, `RANKX`) e definição de indicadores de suporte (SLA, reabertura, satisfação).

---

Autor: **Warlley Santos** · [LinkedIn](https://linkedin.com/in/warlley-santos)
