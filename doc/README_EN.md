<h3 align="center">Sierra Leone Exchange Rate Research</h3>

> Author: Yi Yang

<p align="center">
    <a href="../README.md">简体中文</a> | English
</p>

### 1. Project Introduction

This project studies the relationship between the Sierra Leone leone exchange rate against the US dollar (USDSLE) and monetary, fiscal, and foreign exchange supply and demand factors. The variables include base money, foreign exchange reserves, fuel imports, food imports, iron ore exports, government debt, and the current account.

Completed work includes data cleaning and monthly alignment, descriptive statistics, ADF/KPSS stationarity tests, and factor correlation and VIF diagnostics. The analysis code, charts, and results are saved in three Jupyter notebooks.

### 2. Initial Model and Testing Methods

#### 2.1 Initial Model

Monthly data are stored in `data/final_monthly/`, covering January 2012 through June 2026 with 174 month-end dates. The current diagnostics use training data from January 2012 through December 2024.

Let E(t) denote the number of leones per US dollar. The exchange rate change is:

```text
Y(t) = 100 × [ln E(t) − ln E(t−1)]
```

Y(t) > 0 indicates leone depreciation, while Y(t) < 0 indicates leone appreciation.

The candidate variable framework for the initial model is:

```text
Y(t) = α + βY × Y(t−1) + βM × M(t) + βR × R(t) + βO × O(t) + βF × F(t)
         + βD × D(t) + βC × C(t) + βI × I(t)
         + γ1 × P1(t) + … + γK × PK(t) + ε(t)
```

α is the intercept, β and γ are coefficients, and ε(t) is the error term. Data preparation and factor diagnostics within this framework have been completed.

| Symbol | Variable definition |
|---|---|
| Y(t−1) | Previous-period USDSLE log change |
| M(t) | Base money log change |
| R(t) | Foreign exchange reserves log change |
| O(t) | Log change in the value of mineral fuel and lubricant imports |
| F(t) | Log change in the value of food imports |
| D(t) | Annual percentage-point change in government debt/GDP, repeated across months within the year |
| C(t) | Annual percentage-point change in current account/GDP, repeated across months within the year |
| I(t) | Log change in the value of iron ore exports |
| P1(t) to PK(t) | Policy event dummies: 1 in the month of the event and 0 otherwise |

All log changes are calculated as `100 × [ln X(t) − ln X(t−1)]`. Policy records are available in the [policy event table](../data/source/Sierra_Leone_Policy_Events_2000_2026.csv), and data sources and variable information are available in the [metadata workbook](../data/metadata.xlsx).

#### 2.2 Factor Testing Workflow

| Stage | Notebook | Completed work |
|---|---|---|
| Descriptive statistics | [1_descriptive.ipynb](../notebook/1_descriptive.ipynb) | Sample and missing-value checks, distribution statistics, rolling means and standard deviations, and trend and seasonality screening |
| Stationarity tests | [2_adf.ipynb](../notebook/2_adf.ipynb) | ADF, KPSS, and lag specification sensitivity checks at a significance level of 0.05; annual variables tested at annual frequency |
| Collinearity diagnostics | [3_colinearity_check.ipynb](../notebook/3_colinearity_check.ipynb) | Pearson correlation matrix, heatmap, VIF, and matrix rank for seven contemporaneous factors; 156 months using the original iron ore series, excluding USDSLE and policy dummies |

Current results:

- Descriptive screening identifies seasonality and changes in volatility in some series.
- ADF/KPSS results support retaining the current forms of the monthly series and annual changes in the current account; the result for annual changes in government debt is inconclusive. Stationarity tests for `NO_FILL` iron ore use the longest continuous interval, comprising 77 months.
- The largest absolute correlation among the seven factors is 0.4759, between base money and foreign exchange reserves. VIFs range from 1.0056 to 1.3070, and the matrix including the intercept has rank 8. The current sample shows no substantial multicollinearity.

Each of the two annual factors has 13 annual observations in the training period, repeated across months for collinearity diagnostics. The original iron ore series retains forward filling from the source data; the `NO_FILL` version removes two long filled intervals and the affected changes, retaining 124 months in the training period.

### 3. Python Usage and Project Structure

#### 3.1 Directory Structure

Main file structure:

```text
SLE_research/
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .python-version
├── doc/
│   └── README_EN.md
├── data/
│   ├── metadata.xlsx
│   ├── source/              # Raw data
│   ├── cleaned/             # Prepared intermediate data
│   ├── final_daily/         # Daily exchange rate and policy event data
│   └── final_monthly/       # Monthly analysis data
├── scripts/
│   ├── prepare_trade_monthly.py
│   ├── prepare_money_reserves_monthly.py
│   ├── prepare_annual_changes_monthly.py
│   └── prepare_iron_ore_no_long_fill.py
└── notebook/
    ├── 1_descriptive.ipynb
    ├── 2_adf.ipynb
    └── 3_colinearity_check.ipynb
```

#### 3.2 Running the Notebooks

The project uses Python 3.13 and uv. Install dependencies from the project root:

```powershell
uv sync
```

In an editor with Jupyter support, select the Python kernel from the project's `.venv` and run the three notebooks under `notebook/` in numerical order. The notebooks can read data from either the project root or the `notebook/` directory. Tables and charts are saved within the notebooks.
