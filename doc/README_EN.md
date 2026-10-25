<h3 align="center">Sierra Leone Exchange Rate Research</h3>

> Author: Yi Yang

<p align="center">
    <a href="../README.md">简体中文</a> | English
</p>

### 1. Project Introduction

This project studies the relationship between the Sierra Leone leone exchange rate against the US dollar (USDSLE) and monetary, fiscal, and foreign exchange supply and demand factors. The initial model uses base money, foreign exchange reserves, fuel imports, food imports, iron ore exports, government debt, and the current account. The second model uses CPI, changes in GDP growth, changes in the trade balance, foreign exchange reserves, and government debt/GDP, together with the lagged exchange rate change and event terms.

Completed work includes two rounds of data preparation, factor checks, and AR(1) regression, with hypothesis tests and residual diagnostics. The analysis code, charts, and results are saved in six Jupyter notebooks.

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

α is the intercept, β and γ are coefficients, and ε(t) is the error term. Data preparation, factor diagnostics, and the initial regression have been completed. The regression is in [4_auto_regression_model.ipynb](../notebook/4_auto_regression_model.ipynb).

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
| Initial regression | [4_auto_regression_model.ipynb](../notebook/4_auto_regression_model.ipynb) | OLS regression with the lagged exchange rate change, seven macro factors, and policy event terms; HAC hypothesis tests and residual diagnostics |

Initial factor-check results:

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
│   ├── final_monthly/       # Monthly data for the initial model
│   └── 2_regression_monthly/ # Monthly data for the second regression
│       ├── USDSLE_monthly.csv
│       ├── headline_cpi_log_change_monthly.csv
│       ├── gdp_annual_pct_change_monthly.csv
│       ├── trade_balance_annual_pct_change_monthly.csv
│       ├── fx_reserves_log_change_monthly.csv
│       ├── general_government_gross_debt_annual_change_pp_monthly.csv
│       └── Sierra_Leone_Policy_Event_Dummies_monthly.csv
├── scripts/
│   ├── prepare_trade_monthly.py
│   ├── prepare_money_reserves_monthly.py
│   ├── prepare_annual_changes_monthly.py
│   └── prepare_iron_ore_no_long_fill.py
└── notebook/
    ├── 1_descriptive.ipynb
    ├── 2_adf.ipynb
    ├── 3_colinearity_check.ipynb
    ├── 4_auto_regression_model.ipynb
    ├── 5_second_data_check.ipynb
    └── 6_second_regression.ipynb
```

#### 3.2 Running the Notebooks

The project uses Python 3.13 and uv. Install dependencies from the project root:

```powershell
uv sync
```

In an editor with Jupyter support, select the Python kernel from the project's `.venv` and run the six notebooks under `notebook/` in numerical order. Notebooks 1–4 cover the initial model, while 5–6 cover the second data check and regression. The notebooks can read data from either the project root or the `notebook/` directory. Tables and charts are saved within the notebooks.

#### 3.3 Data Used in the Second Regression

The second regression uses [data/2_regression_monthly/](../data/2_regression_monthly/). Each file retains 174 month-end dates from January 2012 through June 2026. Numerical series use the date and value columns; the government debt file's `period_classification` column is excluded from the regression.

| Data | Regression input file | Source |
|---|---|---|
| USDSLE | [USDSLE_monthly.csv](../data/2_regression_monthly/USDSLE_monthly.csv) | Reuses the [initial monthly exchange rate series](../data/final_monthly/USDSLE_monthly.csv), based on the new and old leone files `USDSLE1DICE.csv` and `USDSLL1DICE.csv` |
| CPI | [headline_cpi_log_change_monthly.csv](../data/2_regression_monthly/headline_cpi_log_change_monthly.csv) | The `hcpi_m` sheet in [WORLDInfla.xlsx](../data/source/WORLDInfla.xlsx), World Bank Inflation Database, with IFS as the underlying index source |
| Change in GDP growth | [gdp_annual_pct_change_monthly.csv](../data/2_regression_monthly/gdp_annual_pct_change_monthly.csv) | [WORLDGDP.csv](../data/source/WORLDGDP.csv), World Bank WDI, `NY.GDP.MKTP.KD.ZG` |
| Change in trade balance | [trade_balance_annual_pct_change_monthly.csv](../data/2_regression_monthly/trade_balance_annual_pct_change_monthly.csv) | [SLEBalanceofTrade.xls](../data/source/SLEBalanceofTrade.xls), World Bank WDI, net trade in goods in current US dollars, `BN.GSR.MRCH.CD` |
| Foreign exchange reserves | [fx_reserves_log_change_monthly.csv](../data/2_regression_monthly/fx_reserves_log_change_monthly.csv) | The [reserves and base money source workbook](../data/source/A-sierra_leone_reserves_base_money_monthly.xlsx), IMF IFS |
| Government debt/GDP | [general_government_gross_debt_annual_change_pp_monthly.csv](../data/2_regression_monthly/general_government_gross_debt_annual_change_pp_monthly.csv) | IMF WEO, `GGXWDG_NGDP`; intermediate data in `data/cleaned/5. IMF_general_government_gross_debt_percent_gdp.csv` |
| Event dummies | [Sierra_Leone_Policy_Event_Dummies_monthly.csv](../data/2_regression_monthly/Sierra_Leone_Policy_Event_Dummies_monthly.csv) | Six event columns, documented in [5_second_data_check.ipynb](../notebook/5_second_data_check.ipynb) |

The intermediate CPI date labels are one month later than the statistical month. Annual GDP and trade balance labels of `YYYY0101` represent year `YYYY−1`; the final inputs use the statistical periods. GDP and trade balance changes for 2012 use 2011 as their base year. All three annual factors repeat each year's change across its months without dividing by 12.

Missing values remain blank: CPI is missing in the first month and has valid changes through March 2025; GDP extends through December 2025; the trade balance extends through December 2024, with the previously filled 2025 value restored to missing; reserves extend through April 2025. Government debt data for 2026 are marked as projections. Data from 2025 onward are excluded from the current training-period estimation and diagnostics.

### 4. Final Regression Model and Factor Definitions

#### 4.1 Final Model

The final model is implemented in [6_second_regression.ipynb](../notebook/6_second_regression.ipynb). The exchange rate lag is constructed on the full monthly calendar before selecting complete observations. The estimation sample covers February 2012 through December 2024, comprising 155 months.

```text
Y(t) = α + φ × Y(t−1) + βπ × Π(t) + βG × G(t) + βB × B(t)
         + βR × R(t) + βD × D(t) + γ1 × P1(t) + … + γ5 × P5(t) + ε(t)
```

Y(t) remains `100 × [ln E(t) − ln E(t−1)]`, with positive values indicating leone depreciation. The model has an intercept, one AR(1) term, five contemporaneous macro factors, and five identifiable event terms, giving 12 parameters.

#### 4.2 Factor Definitions and Coefficients

The coefficients below are taken from the notebook's current output. Let y denote the statistical year, g(y) the original annual GDP growth rate (%), TB(y) the goods trade balance, and Q(y) the government debt/GDP ratio (%).

| Symbol | Variable definition | Approximate coefficient |
|---|---|---:|
| α | Intercept | −0.0263524 |
| Y(t−1) | Previous-month exchange rate log change | −0.162354 |
| Π(t) | Monthly CPI log change: `100 × [ln CPI(t) − ln CPI(t−1)]` | 1.04130 |
| G(t) | Annual change in the GDP growth rate itself: `100 × [g(y) − g(y−1)] / abs(g(y−1))` | −0.00210419 |
| B(t) | Annual trade balance change: `100 × [TB(y) − TB(y−1)] / abs(TB(y−1))` | 0.00115410 |
| R(t) | Monthly reserves log change: `100 × [ln Reserves(t) − ln Reserves(t−1)]` | −0.107443 |
| D(t) | Annual percentage-point change in government debt/GDP: `Q(y) − Q(y−1)` | 0.0827914 |

For CPI and reserves, `1.00` represents a 1% log change. For GDP and the trade balance, `1.00` represents a change equal to 1% of the absolute base-period value. For government debt, `1.00` represents an increase of one percentage point. The GDP factor measures relative changes in the growth rate itself. The trade balance is negative throughout the sample, so a positive B(t) indicates an improvement in the balance and a narrowing deficit.

Annual changes are repeated across the months of their statistical year, with 13 annual observations per series in the training period. Coefficients describe conditional associations after controlling for the other regressors and do not directly identify causal effects.

#### 4.3 Event Terms

The input event table has six columns. The two August 2021 event columns are identical and share one coefficient, leaving five event terms. Each term is 1 in its event month and 0 otherwise.

| Model term | Month | Event | Approximate coefficient |
|---|---|---|---:|
| P1(t) / `P_2015_11` | 2015-11 | IMF ECF review and disbursement | −6.23018 |
| P2(t) / `P_2016_06` | 2016-06 | UK referendum on EU membership | 32.4303 |
| P3(t) / `P_2021_08` | 2021-08 | Redenomination announcement and SDR allocation | 3.30607 |
| P4(t) / `P_2023_06` | 2023-06 | Sixth and seventh IMF ECF reviews | −20.3907 |
| P5(t) / `P_2023_11` | 2023-11 | Eighth IMF ECF review | −1.92627 |

Each single-month event term forces its month's residual to zero and lacks repeated-event information. Only coefficients are reported, without individual event HAC significance tests. The two events in the same month cannot be separately identified.

#### 4.4 Testing Methods and Current Results

| Stage | Notebook | Methods and settings |
|---|---|---|
| Second data check | [5_second_data_check.ipynb](../notebook/5_second_data_check.ipynb) | Five-factor charts, 12-month rolling means and standard deviations, and basic statistics; ADF/KPSS with a constant and `alpha=0.05`, testing annual factors at annual frequency |
| Correlation and collinearity | [6_second_regression.ipynb](../notebook/6_second_regression.ipynb) | Pearson correlation matrix and VIF for the five macro factors, with a VIF warning threshold of 5 |
| Regression and hypothesis tests | Same notebook | OLS coefficients with HAC(12) standard errors, Bartlett weights, and finite-sample scaling; Holm correction for the five individual factor tests and a joint Wald test of all five factors |
| Residual checks and charts | Same notebook | BG tests at lags 1, 6, and 12 with Holm correction; Koenker BP on non-event months; residual correlations with current and lagged exchange rate changes; observed versus fitted values, monthly residuals, and their distribution |

Current output:

- R² is 0.532932, adjusted R² is 0.497004, and in-sample RMSE is 3.2925.
- CPI has a Holm-adjusted p-value of 0.003003; the other four macro factors have adjusted p-values above 0.05. The joint Wald p-value for the five factors is 0.000178.
- All three adjusted BG p-values exceed 0.05; the non-event BP p-value is 0.383898, so the respective null hypotheses are not rejected. The residual correlation with the current exchange rate change follows an OLS identity and does not independently establish model validity.

These are in-sample estimates and diagnostics. Forecasting must account for the release dates of contemporaneous macro variables and annual data; out-of-sample predictive performance has not yet been validated.
