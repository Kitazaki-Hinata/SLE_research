import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
cells = []


def cell(kind, source):
    source = textwrap.dedent(source).strip() + "\n"
    item = {
        "cell_type": kind,
        "id": f"collinearity-{len(cells):02d}",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    cells.append(item)


def md(source):
    cell("markdown", source)


def code(source):
    cell("code", source)


md(r"""
# 因子相关性与多重共线性 / Factor correlation and multicollinearity

本笔记本使用 **2012-01 至 2024-12** 的训练数据，检查七个因子的 Pearson 相关性矩阵和方差膨胀因子（VIF）。经核对，候选因子为五个月度变量和两个年度变量，本次使用全部七项。2025–2026 年留作后续预测评估，不参与本次数据诊断或参数计算。

政策事件 dummy 和 USDSLE 不进入因子矩阵。铁矿石出口先使用原版数据；由于原版保留了长期填充，随后用 `NO_FILL` 版本替换同一因子进行敏感性检查。两个铁矿石版本分别计算。

This notebook examines Pearson correlations and variance inflation factors (VIFs) for all seven factors using the **January 2012 to December 2024** training period. The selection contains five monthly variables and two annual variables. The 2025–2026 evaluation data are excluded from all diagnostics and parameter calculations.

Policy event dummies and USDSLE are excluded from the factor matrix. The original iron ore export series is used first. Its retained long fill intervals motivate a second check that replaces this factor with the `NO_FILL` version. The two versions are evaluated separately.
""")

code("""
# Import the packages used throughout this notebook.
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
""")

md("""
## 读取 CSV / Read the CSV files

先用 pandas 读取原始 CSV，再设置训练区间与检查阈值。每个文件只选取指定的经济变量列，`period_classification` 等元数据保留在原始表中。所有变量已完成变化率转换，本笔记本直接使用现有形式。

Read the CSV files with pandas before setting the training window and diagnostic thresholds. Each file contributes only its specified economic variable; metadata such as `period_classification` remain in the raw frames. All variables have already been transformed into changes, so their existing forms are used.

| 代码中的因子 / Factor label | 中文含义 | English definition | 原始频率 / Original frequency |
|---|---|---|---|
| Base money | 基础货币对数变化率 | Base money log change (%) | 月度 / Monthly |
| FX reserves | 外汇储备对数变化率 | FX reserves log change (%) | 月度 / Monthly |
| Fuel imports | 燃料进口对数变化率 | Fuel imports log change (%) | 月度 / Monthly |
| Food imports | 食品进口对数变化率 | Food imports log change (%) | 月度 / Monthly |
| Iron ore exports | 铁矿石出口对数变化率 | Iron ore exports log change (%) | 月度 / Monthly |
| Government debt | 政府债务/GDP 年度百分点变化 | Annual change in government debt/GDP (pp) | 年度，逐月重复 / Annual, repeated monthly |
| Current account | 经常账户/GDP 年度百分点变化 | Annual change in current account/GDP (pp) | 年度，逐月重复 / Annual, repeated monthly |
""")

code("""
# Resolve data paths from either the project root or notebook directory.
DATA_DIR = Path("data/final_monthly")
if not DATA_DIR.is_dir():
    DATA_DIR = Path("../data/final_monthly")
if not DATA_DIR.is_dir():
    raise FileNotFoundError("Run from the project root or notebook directory.")

FACTOR_FILES = {
    "Base money": "base_money_log_change_monthly.csv",
    "FX reserves": "fx_reserves_log_change_monthly.csv",
    "Fuel imports": "fuel_imports_log_change_monthly.csv",
    "Food imports": "food_imports_log_change_monthly.csv",
    "Iron ore exports": "iron_ore_exports_log_change_monthly.csv",
    "Government debt": "general_government_gross_debt_annual_change_pp_monthly.csv",
    "Current account": "current_account_balance_annual_change_pp_monthly.csv",
}
NO_FILL_FILE = "NO_FILL_iron_ore_exports_log_change_monthly.csv"
""")

md("""
下面保留每张 CSV 的原始 DataFrame，便于检查列名和追溯来源。备用铁矿石数据单独读取，之后仅用于替换检查。

Keep each CSV as a raw DataFrame so that column names and sources remain traceable. Read the alternative iron ore series separately for the later replacement check.
""")

code("""
# Load raw CSVs before cleaning, alignment, or diagnostic calculations.
raw_frames = {
    factor: pd.read_csv(DATA_DIR / filename)
    for factor, filename in FACTOR_FILES.items()
}
raw_iron_no_fill = pd.read_csv(DATA_DIR / NO_FILL_FILE)

display(pd.DataFrame({
    "source_file": FACTOR_FILES,
    "value_column": {key: Path(value).stem for key, value in FACTOR_FILES.items()},
}).rename_axis("factor"))
display(raw_frames["Base money"].head(3))
""")

md("""
## 检查设置 / Diagnostic settings

在处理数据前固定训练日期和提示阈值：`|r| ≥ 0.80` 提示较强的两两线性相关；`VIF ≥ 5` 提示进一步核查，`VIF ≥ 10` 作为更高一级的提示。这些是本笔记本采用的经验界限，可根据研究设定调整。

相关矩阵和 VIF 在这里用于描述设计矩阵，不计算 p 值，也没有待拒绝的原假设，因此无需设置 `alpha`。以后加入假设检验时，应在检验前单独设置显著性水平，例如 `alpha = 0.05`。

Set the training dates and thresholds before processing the data. This notebook flags `|r| ≥ 0.80` for strong pairwise linear association, `VIF ≥ 5` for review, and `VIF ≥ 10` for a higher warning level. These are adjustable diagnostic conventions. The [statsmodels VIF documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.outliers_influence.variance_inflation_factor.html) discusses 5 as a screening guideline.

These calculations describe the design matrix without p-values or a null hypothesis, so they do not require `alpha`. If hypothesis tests are added later, set their significance level separately before testing, for example `alpha = 0.05`.
""")

code("""
# Set all sample and screening choices before processing observations.
TRAIN_START = pd.Timestamp("2012-01-31")
TRAIN_END = pd.Timestamp("2024-12-31")
EXPECTED_FACTOR_COUNT = 7
CORR_WARNING = 0.80
VIF_WARNING = 5.0
VIF_HIGH = 10.0
RUN_NO_FILL_CHECK = True

train_months = pd.date_range(TRAIN_START, TRAIN_END, freq="ME", name="date")
assert len(FACTOR_FILES) == EXPECTED_FACTOR_COUNT
assert TRAIN_END < pd.Timestamp("2025-01-01")
assert 0 < CORR_WARNING < 1 and 1 < VIF_WARNING < VIF_HIGH
""")

md("""
## 训练样本与数据检查 / Training sample and data checks

先按日期截取训练期，再转换数值、检查重复月份并按月末对齐。缺失值和无穷值保留为缺失；不进行填充、插值或额外差分。已有月末日期直接使用。

Filter to the training period before converting values, checking duplicate months, and aligning month-end dates. Missing and infinite values are treated as missing, with no filling, interpolation, or additional differencing. Existing month-end labels are used directly.
""")

code("""
def training_series(frame, value_column):
    'Extract one numeric series on the training calendar.'
    dates = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="raise")
    in_train = dates.between(TRAIN_START, TRAIN_END)
    train = frame.loc[in_train, [value_column]].copy()
    train.index = pd.DatetimeIndex(dates.loc[in_train], name="date")
    if train.index.has_duplicates:
        raise ValueError(f"Duplicate training dates: {value_column}")
    if not train.index.is_month_end.all():
        raise ValueError(f"Expected month-end training dates: {value_column}")
    values = pd.to_numeric(train[value_column], errors="raise").astype(float)
    return values.replace([np.inf, -np.inf], np.nan).reindex(train_months)


# Extract only the explicitly named factor columns.
train_factors = pd.DataFrame({
    factor: training_series(raw_frames[factor], Path(filename).stem)
    for factor, filename in FACTOR_FILES.items()
})
iron_no_fill = training_series(raw_iron_no_fill, Path(NO_FILL_FILE).stem)
""")

md("""
数据表报告训练期的有效月份、缺失月份、零变化和不同取值数量。零变化可以是真实结果，不能仅凭零值判定填充。两项年度因子的每年取值应保持一致；重复到各月不会增加年度信息量。

The audit reports valid months, missing months, zero changes, and distinct values within the training window. A zero change can be a real observation and alone does not identify a filled value. Each annual factor should be constant within a year; monthly repetition adds no annual information.
""")

code("""
quality = pd.DataFrame({
    "training_months": len(train_months),
    "valid_months": train_factors.notna().sum(),
    "missing_months": train_factors.isna().sum(),
    "zero_changes": train_factors.eq(0).sum(),
    "distinct_values": train_factors.nunique(),
    "first_valid": train_factors.apply(lambda s: s.first_valid_index()),
    "last_valid": train_factors.apply(lambda s: s.last_valid_index()),
}).rename_axis("factor")
display(quality)

# Validate annual repetition without treating repeated rows as new annual data.
annual_factors = ["Government debt", "Current account"]
annual_unique = train_factors[annual_factors].groupby(train_factors.index.year).nunique()
if annual_unique.gt(1).any().any():
    raise ValueError("An annual factor changes within a year; inspect the source.")
print(f"Training calendar: {len(train_months)} months; annual periods: {len(annual_unique)}")
""")

md("""
相关性矩阵和 VIF 统一使用七个因子均非缺失的月份。这样每个相关系数的样本与 VIF 完全一致。[pandas 的 `corr`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.corr.html) 默认使用每一对变量的非缺失行，因此这里先对整张因子表删除不完整行。

Use months with complete observations for all seven factors for both correlation and VIF. This gives every correlation coefficient the same sample as the VIF calculation. Since pandas `corr` uses pairwise complete observations by default, incomplete rows are removed from the full factor table first.
""")

code("""
def complete_sample(frame):
    'Keep common finite rows and reject undefined diagnostic inputs.'
    sample = frame.replace([np.inf, -np.inf], np.nan).dropna().copy()
    if len(sample) <= sample.shape[1] + 1:
        raise ValueError("Too few complete rows for the factor matrix and intercept.")
    constant = sample.columns[sample.nunique().le(1)].tolist()
    if constant:
        raise ValueError(f"Constant factors have undefined correlation/VIF: {constant}")
    if not sample.index.to_series().between(TRAIN_START, TRAIN_END).all():
        raise ValueError("A diagnostic sample contains dates outside training.")
    return sample


baseline_sample = complete_sample(train_factors)
print(f"Baseline: {len(baseline_sample)} complete months, {baseline_sample.shape[1]} factors")
print(f"Dates: {baseline_sample.index.min():%Y-%m} to {baseline_sample.index.max():%Y-%m}")
print(f"Dropped training months: {len(train_factors) - len(baseline_sample)}")
""")

md(r"""
## 因子相关性矩阵 / Factor correlation matrix

Pearson 相关系数描述两个因子的线性关联，范围为 $[-1, 1]$。正负号表示方向，绝对值表示强度。矩阵对角线恒为 1，不用于筛查；每一对因子只报告一次。较低的两两相关仍可能伴随多变量的线性依赖，需要继续检查 VIF。

Pearson correlation measures pairwise linear association on $[-1, 1]$. Its sign gives direction and its absolute value gives strength. The diagonal equals 1 and is excluded from screening; each distinct pair is listed once. Low pairwise correlations can coexist with dependence on a combination of other variables, which motivates the VIF check.
""")

code("""
def correlation_pairs(matrix):
    'Return each off-diagonal pair once, ordered by absolute correlation.'
    rows = []
    for i, factor_a in enumerate(matrix.columns):
        for factor_b in matrix.columns[i + 1:]:
            r = matrix.loc[factor_a, factor_b]
            rows.append({"factor_a": factor_a, "factor_b": factor_b, "r": r})
    pairs = pd.DataFrame(rows)
    pairs["abs_r"] = pairs["r"].abs()
    pairs["review"] = pairs["abs_r"].ge(CORR_WARNING)
    return pairs.sort_values("abs_r", ascending=False).reset_index(drop=True)


corr_matrix = baseline_sample.corr(method="pearson")
corr_pairs = correlation_pairs(corr_matrix)
display(corr_matrix.round(3))
display(corr_pairs.round(3))
print(f"Pairs at or above |r| = {CORR_WARNING:.2f}: {corr_pairs['review'].sum()}")
""")

md("""
热力图使用固定的 −1 至 1 色阶，并在格内标注相关系数。坐标轴使用上表中的英文名称，便于在不同系统上显示。

The heatmap uses a fixed scale from −1 to 1 and annotates each coefficient. Axis labels use the English names listed above for consistent display across systems.
""")

code("""
def plot_correlation(matrix, title):
    'Plot a labelled correlation matrix with a fixed colour scale.'
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    chart = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1)
    ticks = np.arange(len(matrix))
    ax.set_xticks(ticks, labels=matrix.columns, rotation=45, ha="right")
    ax.set_yticks(ticks, labels=matrix.index)
    for i in ticks:
        for j in ticks:
            value = matrix.iloc[i, j]
            colour = "white" if abs(value) > 0.60 else "black"
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", color=colour)
    ax.set_title(title)
    fig.colorbar(chart, ax=ax, label="Pearson correlation", shrink=0.85)
    plt.show()


plot_correlation(corr_matrix, f"Factor correlations | Training 2012-2024 | n={len(baseline_sample)}")
""")

md(r"""
## 方差膨胀因子 / Variance inflation factors

对每个因子 $X_j$，以其余六个因子和截距为解释变量进行辅助回归，得到 $R_j^2$：

$$\mathrm{VIF}_j = \frac{1}{1-R_j^2}, \qquad \mathrm{Tolerance}_j = 1-R_j^2.$$

VIF 接近 1 表示该因子与其他因子的线性关系较弱；VIF 越大，系数方差因这种关系而膨胀的程度越高。先用当前训练样本的均值和标准差进行标准化，再加入截距。该缩放改善数值计算，同时保留含截距回归的 VIF。结果表不报告截距的 VIF。

For each factor $X_j$, regress it on the other six factors and an intercept to obtain $R_j^2$. VIF measures variance inflation associated with linear dependence on the other factors. Values near 1 indicate little inflation. Standardize using the current training sample, then include an intercept. This scaling improves numerical stability and preserves VIF for regressions with an intercept. The intercept itself is excluded from the results table.
""")

code("""
def vif_table(sample):
    'Calculate centred VIFs using auxiliary regressions with an intercept.'
    scaled = (sample - sample.mean()) / sample.std(ddof=0)
    design = add_constant(scaled, has_constant="add").to_numpy(dtype=float)
    # Large or infinite VIFs remain visible in the output.
    with np.errstate(divide="ignore", invalid="raise"):
        values = [variance_inflation_factor(design, j + 1) for j in range(sample.shape[1])]
    result = pd.DataFrame({"VIF": values}, index=sample.columns)
    result["tolerance"] = 1 / result["VIF"]
    result["auxiliary_R2"] = 1 - result["tolerance"]
    result["review"] = result["VIF"].ge(VIF_WARNING)
    result["level"] = np.select(
        [result["VIF"].ge(VIF_HIGH), result["review"]],
        ["high", "review"], default="below threshold",
    )
    return result.rename_axis("factor").sort_values("VIF", ascending=False)


baseline_vif = vif_table(baseline_sample)
display(baseline_vif.round(4))
""")

md("""
同时检查含截距矩阵的秩。满秩表示当前矩阵没有完全线性依赖；接近线性依赖仍需参考 VIF。提示阈值不会自动触发因子删除。

Also check the rank of the matrix including the intercept. Full rank rules out exact linear dependence in the current matrix; VIF still needs to be considered for near dependence. Threshold flags do not automatically remove factors.
""")

code("""
def sample_summary(sample, vif):
    'Summarize coverage, correlations, and the rank of the scaled design.'
    scaled = (sample - sample.mean()) / sample.std(ddof=0)
    design = add_constant(scaled, has_constant="add").to_numpy(dtype=float)
    pairs = correlation_pairs(sample.corr())
    return {
        "n_months": len(sample),
        "start": sample.index.min().strftime("%Y-%m"),
        "end": sample.index.max().strftime("%Y-%m"),
        "missing_calendar_months": len(train_months.difference(sample.index)),
        "design_rank": np.linalg.matrix_rank(design),
        "design_columns": design.shape[1],
        "max_abs_r": pairs["abs_r"].max(),
        "flagged_pairs": int(pairs["review"].sum()),
        "max_VIF": vif["VIF"].max(),
        "flagged_VIFs": int(vif["review"].sum()),
    }


baseline_summary = sample_summary(baseline_sample, baseline_vif)
display(pd.DataFrame([baseline_summary], index=["Original iron ore"]).round(4))
""")

md("""
## 铁矿石替换检查 / Iron ore replacement check

项目的铁矿石处理脚本说明，原版保留了前向填充。`NO_FILL` 去除了两段长期填充及受相邻期填充影响的变化率，较早的填充仍然存在。先比较训练期两个版本的覆盖和保留值；被剔除月份会单独列出。

The project's iron ore preparation script documents forward fills in the original series. `NO_FILL` removes two long fill intervals and changes affected by adjacent filled periods; earlier fills remain. Compare training-period coverage and retained values before repeating the diagnostics. Excluded months are listed separately.

处理说明 / Preparation notes: [prepare_iron_ore_no_long_fill.py](../scripts/prepare_iron_ore_no_long_fill.py).
""")

code("""
iron_versions = pd.DataFrame({
    "original": train_factors["Iron ore exports"],
    "NO_FILL": iron_no_fill,
})
display(pd.DataFrame({
    "valid_months": iron_versions.notna().sum(),
    "missing_months": iron_versions.isna().sum(),
    "zero_changes": iron_versions.eq(0).sum(),
}))
excluded_iron = iron_versions["original"].notna() & iron_versions["NO_FILL"].isna()
shared_iron = iron_versions.dropna()
retained_equal = np.allclose(shared_iron["original"], shared_iron["NO_FILL"], rtol=0, atol=1e-12)
print(f"Original values excluded by NO_FILL: {excluded_iron.sum()}")
print("Excluded months:", ", ".join(iron_versions.index[excluded_iron].strftime("%Y-%m")))
print(f"Retained values identical within tolerance: {retained_equal}")
""")

md("""
第二次检查用 `NO_FILL` 替换铁矿石列，其他六个因子保持相同定义。为区分样本变化和数值变化，再计算“原版铁矿石、相同月份”的对照。三组结果都只使用训练期。

此处计算同月变量之间的相关性和辅助回归，删除缺失月份后可以使用全部完整行。保留真实日期，不把间断样本解释为连续月度序列。若后续增加滞后项，应先在完整日历上构建滞后，再删除缺失行。

Replace the iron ore column with `NO_FILL` while keeping the definitions of the other six factors. Also calculate an original-series control on exactly the same months to distinguish changes in coverage from changes in values. All three samples remain inside the training period.

These diagnostics use contemporaneous rows, so all complete months can be used despite gaps. Preserve the actual dates. If lags are added later, construct them on the full calendar before dropping incomplete rows.
""")

code("""
samples = {"Original / full training": baseline_sample}
vif_results = {"Original / full training": baseline_vif}

if RUN_NO_FILL_CHECK:
    alternative = train_factors.copy()
    alternative["Iron ore exports"] = iron_no_fill
    no_fill_sample = complete_sample(alternative)
    common_dates = baseline_sample.index.intersection(no_fill_sample.index)
    original_common = complete_sample(train_factors.loc[common_dates])
    no_fill_common = complete_sample(alternative.loc[common_dates])
    samples["Original / common months"] = original_common
    samples["NO_FILL / common months"] = no_fill_common
    for label in list(samples)[1:]:
        vif_results[label] = vif_table(samples[label])

comparison = pd.DataFrame({
    label: sample_summary(sample, vif_results[label])
    for label, sample in samples.items()
}).T
display(comparison)
""")

md("""
下面并列显示各因子的 VIF，并展示替换后的完整相关性矩阵和 VIF 表。如果两个铁矿石版本在共同月份的数值相同，共同月份上的两组结果也应相同。

Compare factor-level VIFs across samples, then show the full replacement correlation matrix and VIF table. If the iron ore values agree on common months, the two sets of diagnostics on those months should also agree.
""")

code("""
vif_comparison = pd.DataFrame({
    label: table["VIF"] for label, table in vif_results.items()
}).reindex(train_factors.columns)
display(vif_comparison.round(4))

if RUN_NO_FILL_CHECK:
    no_fill_corr = no_fill_common.corr(method="pearson")
    display(no_fill_corr.round(3))
    display(vif_results["NO_FILL / common months"].round(4))
    common_corr_delta = (original_common.corr() - no_fill_corr).abs().to_numpy().max()
    common_vif_delta = (
        vif_comparison["Original / common months"]
        - vif_comparison["NO_FILL / common months"]
    ).abs().max()
    print(f"Common-month maximum correlation difference: {common_corr_delta:.3g}")
    print(f"Common-month maximum VIF difference: {common_vif_delta:.3g}")
""")

md("""
## 结果解释 / Interpretation

下面的中英文结论随计算结果更新。判断使用前面设定的阈值，不将低 VIF 解释为模型已满足全部统计假设。

The bilingual conclusion below updates from the calculated results and uses the thresholds set above. Low VIF alone does not establish that a model satisfies all statistical assumptions.
""")

code(r"""
top_pair = corr_pairs.iloc[0]
top_factor = baseline_vif["VIF"].idxmax()
flagged = bool(corr_pairs["review"].any() or baseline_vif["review"].any())
verdict_cn = "存在达到提示阈值的结果，需进一步核查。" if flagged else "未达到预设提示阈值，当前七因子矩阵未显示明显多重共线性。"
verdict_en = "Threshold flags require further review." if flagged else "No screening threshold is reached; this seven-factor matrix shows no pronounced multicollinearity."

display(Markdown(
    f"原版样本包含 **{len(baseline_sample)} 个月**。最大绝对相关发生在 "
    f"**{top_pair['factor_a']}** 与 **{top_pair['factor_b']}**，r = **{top_pair['r']:.3f}**。"
    f"最大 VIF 为 **{baseline_vif['VIF'].max():.3f}**（{top_factor}）。{verdict_cn}\n\n"
    f"The original sample contains **{len(baseline_sample)} months**. The strongest pair is "
    f"**{top_pair['factor_a']}** and **{top_pair['factor_b']}**, with r = **{top_pair['r']:.3f}**. "
    f"The maximum VIF is **{baseline_vif['VIF'].max():.3f}** ({top_factor}). {verdict_en}"
))
""")

md("""
替换检查应结合样本数量解读。共同月份结果一致时，全样本与删减样本的差异来自月份选择，不能据此认定删除填充数据解决了共线性。

Interpret the replacement check together with its sample size. When common-month results agree, differences between the full and reduced samples arise from month selection and do not demonstrate that removing filled data resolved collinearity.
""")

code(r"""
if RUN_NO_FILL_CHECK:
    alternative_max_vif = vif_results["NO_FILL / common months"]["VIF"].max()
    alternative_max_r = correlation_pairs(no_fill_corr)["abs_r"].max()
    display(Markdown(
        f"NO_FILL 共同样本为 **{len(no_fill_common)} 个月**，最大 |r| 为 "
        f"**{alternative_max_r:.3f}**，最大 VIF 为 **{alternative_max_vif:.3f}**。"
        f"共同月份的相关系数和 VIF 最大差异分别为 {common_corr_delta:.3g} 和 "
        f"{common_vif_delta:.3g}。\n\n"
        f"The NO_FILL common sample contains **{len(no_fill_common)} months**, with maximum "
        f"|r| **{alternative_max_r:.3f}** and maximum VIF **{alternative_max_vif:.3f}**. "
        f"The largest common-month differences in correlation and VIF are "
        f"{common_corr_delta:.3g} and {common_vif_delta:.3g}, respectively."
    ))
""")

md("""
### 使用范围 / Scope of the findings

- 两项年度变量在本训练期各有 13 个年度观测，逐月重复后用于检查拟用月度矩阵。相关性和 VIF 无法确认其月度独立性，也不解决年度数据发布日期带来的信息可得性问题。进入预测模型前仍需明确频率处理与发布滞后。
- 本次仅检查这七个同期因子。后续加入 USDSLE 滞后、月份 dummy 或政策事件后，应对实际回归样本及完整解释变量矩阵重新计算。
- 低 VIF 不能验证平稳性、外生性、残差性质或预测能力。铁矿石填充问题仍需根据数据来源处理。这里不根据 VIF 自动删除变量。
- 2025–2026 年的数据未参与相关性、标准化、VIF 或替换检查。

- Each annual factor has 13 annual observations in this training window. Monthly repetition permits a check of the proposed monthly matrix but does not establish monthly independence or resolve publication timing. Frequency treatment and release lags still need to be specified before prediction.
- These results cover the seven contemporaneous factors. Recalculate diagnostics on the actual regression sample and full predictor matrix after adding USDSLE lags, month dummies, or policy events.
- Low VIF does not validate stationarity, exogeneity, residual behaviour, or forecasting performance. Iron ore fills still require source-based assessment. No factor is automatically removed on the basis of VIF.
- The 2025–2026 data do not contribute to correlation, scaling, VIF, or replacement diagnostics.
""")


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
target = ROOT / "notebook/3_colinearity_check.ipynb"
target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
code_cells = [item for item in cells if item["cell_type"] == "code"]
print(f"Wrote {len(cells)} cells ({len(code_cells)} code cells).")
print(f"Longest code cell: {max(len(item['source']) for item in code_cells)} lines.")
