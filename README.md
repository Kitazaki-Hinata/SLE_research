<h3 align="center">
Sierra Leone Exchange Rate Research

塞拉利昂汇率研究
</h3>

>  作者 / Author：Yi Yang

>  English version is at the bottom part of this README.md



### 一、项目介绍

本项目研究塞拉利昂利昂汇率变动与国内货币、财政状况、外汇供求及国际商品市场之间的关系，进而预测后续USDSLE走势。研究以宏观因子回归为起点，逐步加入政策事件、伪样本外预测和情景模拟，评估不同经济条件下的汇率变化及其不确定性。

研究背景包括政府融资与货币扩张、食品和燃料进口带来的外汇需求，以及铁矿石等矿产出口带来的外汇收入。IMF的研究指出，财政融资和货币扩张与2022到2023年的通胀上升密切相关，同时讨论了食品进口对外部收支的压力及矿业冲击对出口的影响。这些材料用于提出研究问题，不替代本项目自身的实证检验。参见[IMF《Sierra Leone: Selected Issues》](https://www.imf.org/-/media/files/publications/cr/2024/english/1sleea2024002-print-pdf.pdf)，正文p4、p36、p50-p56页。

**项目重点考察以下问题：**

1. 货币增长、政府债务和储备变化如何与利昂升贬值相关？
2. 燃油、食品进口及铁矿石出口的金额或价格变化，能否解释额外的汇率波动？
3. 政策调整、国际融资和其他宏观事件发生前后，模型关系是否稳定？
4. 模型能否在未参与估计的时期提供有效预测，并反映不同情景下的风险范围？


### 二、初始测试模型与测试方法

#### 2.1 初始模型

- 数据日期从2012年1月1日到2026年6月30日。模型将使用Pseudo Out-of-sample方法，设置2012-01-01到2024-12-31的数据用于模型拟合和测试，2025-01-01到2026-06-30用于测试模型预测准确性。最后，模型将预测2026-06-30到2027-12-31的外汇数据。

- 回归统一使用 `data/final_monthly/` 的月度数据，当前汇率变化率、事件虚拟变量和已转换的宏观因子文件均保留174期（2012年1月至2026年6月），日期采用月末标签，从2012-01-31到2026-06-30。`data/final_daily/` 保留5295期日度数据（2012-01-01至2026-06-30），用于事件与日期核对。基础货币、外汇储备、燃料进口、食品进口和铁矿石出口的对数变化率已完成转换和月度对齐；政府债务/GDP与经常账户/GDP已生成年度百分点变化的逐月重复版本。保留174行不代表每个变量都有174个有效观测，最终有效样本取决于所选变量的覆盖情况与滞后设定。

- 用 E(t) 表示本期每美元兑换的利昂数量，E(t−1) 表示上一期的汇率。统一新旧货币单位后，汇率变动率计算为：

```text
Y(t) = 100 × [ln E(t) − ln E(t−1)]
```

- 其中，t 表示本期，t−1 表示上一期；ln 表示自然对数。Y(t) 是汇率的对数变化率，可近似理解为百分比变化。**Y(t) > 0 表示每美元可兑换更多利昂，即利昂相对美元贬值；Y(t) < 0 表示利昂升值。**


**以下为候选因子框架，月度基准模型按可用数据选择其中的因素：**

```text
Y(t) = α + βY× Y(t-1)+ βM × M(t) + βR × R(t) + βO × O(t) + βF × F(t)
         + βD × D(t) + βC × C(t) + βI × I(t)
         + γ1 × P1(t) + … + γK × PK(t) + ε(t)
```

- 其中，α 是常数项；βM、βR 等是对应经济变量的回归系数，表示其他变量不变时，该变量增加一个单位与 Y(t) 变化的关系。P1(t) 至 PK(t) 是 K 个政策事件变量，γ1 至 γK 是各自的回归系数；ε(t) 是模型未解释的扰动。各经济变量的含义如下：

- 政策候选事件记录在[政策事件表](data/source/Sierra_Leone_Policy_Events_2000_2026.csv)。使用时区分公告日期、生效日期、日期精度和实施状态。

| 符号            | 含义及待确定口径                                                                      |
|---------------|-------------------------------------------------------------------------------|
| Y(t-1)        | 上一个周期的USDSLE变化值                                                               |
| M(t)          | 基础货币对数增长率，数据截止到2026-04。对数变化率：100 × [ln B(t) − ln B(t−1)]；**不是M2增长率**          |
| R(t)          | 外汇储备指标:  对数变化率。数据截止到2025-04                                                   |
| O(t)          | 燃料进口额变化: 对数变化率，当前采用矿物燃料及润滑油进口额口径                                               |
| F(t)          | 食品进口额变化: 对数变化率                                                                |
| D(t)          | 政府债务/GDP的年度变化：本年比率减上年比率，单位为百分点，同年各月重复该值                                  |
| C(t)          | 经常账户/GDP的年度变化：本年比率减上年比率，单位为百分点，同年各月重复该值                                  |
| I(t)          | 铁矿石出口额变化：对数变化率。原版本保留源数据的前向填充，连续填充值会产生0变化；`NO_FILL`版本仅剔除两段长期填充及受其影响的变化率，仍保留更早的填充。缺失月份不能直接用于回归。 |
| P1(t) 至 PK(t) | 按政策日期和作用机制构造的事件虚拟变量。                                                          |

政府债务/GDP和经常账户/GDP的原始频率仍为年度。现有月度文件将年度比率的一阶差分按统计年份重复到各月，不取对数、不再乘以100，也不除以12；保留 `period_classification`，其中2026年为预测值。这种对齐未按发布日期或信息可得时间处理，当前notebook仅对这两项展示描述性滚动图；在确定适当的频率处理与信息可得性之前，不将其直接纳入月度基准模型。现有月度事件表采用“当月发生过该事件为1，否则为0”的编码；后续是否采用持续状态或窗口，需按研究设定另行确定。


#### 2.2 检验因子流程

1. **核对输入：** 从 `data/final_monthly/` 读取回归输入，确认真实统计期、单位、预测标记和保留的填充记录。当前汇率变化率、事件虚拟变量和宏观因子已按同一月度日期排序；使用时仍需核对缺失值、年度重复值及源文件中的填充标记。
2. **描述统计与平稳性：** 使用 `notebook/descriptive.ipynb` 查看训练期的分布、滚动统计、线性趋势和月份季节性；当前已完成描述性筛查，ADF/KPSS尚未实现，后续结合单位根检验及经济含义确定模型变量。
3. **共线性检查：** 对实际进入模型的变量和滞后项计算相关矩阵与VIF。
4. **基准估计：** 使用OLS估计简约模型，再按变量组扩展；报告系数、置信区间、样本区间和有效样本数。
5. **残差与稳定性：** 检查自相关、异方差、异常点影响和系数稳定性。
6. **稳健性与预测：** 比较合理的变量口径、滞后和样本设定；在共同样本上比较模型，避免把样本变化误认为模型改善。

#### 2.3 伪样本外检验


#### 2.4 情景与蒙特卡洛模拟

### 三、Python使用方法与项目架构

#### 3.1 数据分层与数据解读

- `data/source/`：保存原始下载文件、来源工作簿和政策事件资料，用于溯源。当前包括新旧利昂汇率、美元指数及英镑相关汇率、基础货币与储备工作簿、IMF宏观数据、贸易工作簿、世界谷物价格指数、燃料与铁矿石市场序列，以及GDP、通胀、失业和贸易差额资料。
- `data/cleaned/`：保存中间整理序列，用于追踪清洗过程；保留的年度序列用于背景分析和候选扩展。
- `data/final_daily/`：保留日度汇率变化率和事件虚拟变量，用于事件与日期核对。
- `data/final_monthly/`：后续回归的统一输入目录，当前包含汇率变化率、事件虚拟变量、基础货币与储备对数变化率、三项贸易对数变化率、铁矿石 `NO_FILL` 版本，以及两项年度比率变化的逐月重复版本，共10个CSV。各月度文件按 `USDSLE_monthly.csv` 的日期与排序对齐。基础货币与储备分别有172和160个有效月度变化值；铁矿石原版本有174个，`NO_FILL`版本有142个，其余32个月为空值。
- [data/metadata.xlsx](data/metadata.xlsx)：记录原始与中间序列的变量名称、覆盖日期、频率、预测状态、变化形式、前向填充和来源。其中基础货币与储备的覆盖日期仍记为2024年12月，尚未同步更新；当前覆盖范围和最终变化形式需结合现有CSV及处理脚本核对。README不再重复列出数据来源表。

其中：

1. 元数据中的覆盖日期描述统计期间。基础货币与储备中间CSV的标签是当月1日，贸易中间CSV的标签是次月1日，年度比率CSV的标签是次年1月1日；这些不等于发布日期。处理脚本分别映射到对应统计月的月末或统计年份。最终文件按其实际日期约定读取，不应再次机械平移。
2. 空值不等于零；前向填充不等于新增真实观测；预测值与历史观测应分别识别。
3. CPI和商品指数的水平值不等于通胀率或价格变化率。基础货币中间文件保存余额，最终月度文件已由相邻月度余额计算对数增长率；已转换为变化率的最终汇率和宏观因子数据不再重复取增长率。
4. 新旧利昂计价、美元金额的千/百万/十亿单位，以及铁矿石干吨/湿吨口径需要明确区分。相同经济变量的不同单位版本不应同时作为独立解释变量。
5. 数据完成清洗不代表所有序列必须进入同一个模型。最终样本应由选定变量共同决定，并保留计算增长率及滞后所需的前期数据。

#### 3.2 目录结构

以下列出实际数据、脚本和notebook目录及后续代码布局；标注“规划”的目录和模块尚未创建。

```text
SLE_research/
├── README.md
├── LICENSE
├── pyproject.toml           # Python依赖与ipykernel开发依赖
├── uv.lock                  # 依赖锁定文件
├── .python-version          # Python 3.13
├── data/
│   ├── metadata.xlsx
│   ├── source/
│   ├── cleaned/
│   ├── final_daily/          # 日度汇率与事件数据，供事件和日期核对
│   └── final_monthly/        # 月度对齐数据；含宏观变化率、年度重复值和NO_FILL版本
├── scripts/
│   ├── prepare_trade_monthly.py
│   ├── prepare_money_reserves_monthly.py
│   ├── prepare_annual_changes_monthly.py
│   └── prepare_iron_ore_no_long_fill.py
├── notebook/
│   └── descriptive.ipynb     # 训练期描述统计、滚动图及趋势与季节性筛查
├── configs/                 # 规划：变量、滞后、样本及模拟参数
├── src/                     # 规划
│   └── sle_research/
│       ├── data_io.py       # 读取最终数据和元数据
│       ├── features.py      # 构造尚未提供的模型特征和滞后
│       ├── models.py        # 回归估计
│       ├── diagnostics.py   # 统计诊断
│       ├── backtest.py      # 伪样本外检验
│       └── simulation.py    # 情景和蒙特卡洛模拟
├── outputs/                 # 规划：回归表、诊断、预测及图形
└── tests/                   # 规划：日期、单位和信息泄漏检查
```

回归、诊断、预测及图形等分析输出应保存于 `outputs/`，不覆盖最终输入数据。当前notebook在单元格内显示图表和汇总表，尚未导出到该目录。每次运行记录变量、样本、滞后、标准误类型、随机种子和数据版本，以便复现。

#### 3.3 Python环境与读取示例

python版本：3.13，使用uv管理依赖。使用以下指令安装所有python依赖：
```powershell
uv sync
uv add --dev ipykernel
```
回归统一使用 `final_monthly`；仅在核对日度数据时改读 `final_daily`。日期解析及后续模型特征应按最终文件的列名和元数据定义执行，`USDSLE_monthly.csv` 的 `USDSLE_monthly` 列已是乘以100的对数变化率。

当前项目依赖包括pandas、NumPy、Matplotlib、statsmodels、IPython和datetime，开发依赖为ipykernel。在支持Jupyter的编辑器中打开 `notebook/descriptive.ipynb`，选择项目 `.venv` 对应的Python内核后按顺序运行；notebook支持从项目根目录或 `notebook/` 目录定位数据。

现有数据处理脚本从 `data/cleaned/` 读取中间数据，并以 `USDSLE_monthly.csv` 的174个月末日期为基准写入 `data/final_monthly/`。需要重新生成时，可在项目根目录使用 `uv run python scripts/<脚本名>.py`，各脚本内容如下：

| 脚本 | 当前处理内容 |
|---|---|
| `prepare_trade_monthly.py` | 计算矿物燃料及润滑油进口、食品进口和铁矿石出口的 `100 × [ln X(t) − ln X(t−1)]`，使用2011年12月作为首期滞后，保留源文件已有填充，不新增填充；当期或上期水平缺失或非正时留空。 |
| `prepare_money_reserves_monthly.py` | 计算基础货币与外汇储备的月度对数变化率，使用同样的相邻月份规则；储备采用百万美元列，不对缺失值填充或预测。 |
| `prepare_annual_changes_monthly.py` | 将政府债务/GDP和经常账户/GDP的年度百分点变化重复到同年各月，使用2011年作为首年滞后，保留至统计年2026及其预测标记。 |
| `prepare_iron_ore_no_long_fill.py` | 在原铁矿石变化率基础上排除2018年6月至2019年6月、2019年8月至2020年12月的长期前向填充值，同时将受上期填充值影响的2019年7月、2021年1月变化率留空，保留更早的填充。 |

当前脚本输出与已提交CSV的命名存在差异：变化率脚本写入的值列使用 `_log_change_pct` 或 `_annual_change_pp` 后缀，已提交的连续指标CSV值列则与各自文件名（去掉 `.csv`）一致；铁矿石变体脚本写入 `iron_ore_exports_log_change_monthly_no_long_fill.csv`，而当前notebook读取 `NO_FILL_iron_ore_exports_log_change_monthly.csv`。重新生成前需核对这些差异；铁矿石变体脚本读取原版本的 `iron_ore_exports_log_change_pct` 列，因此依赖贸易脚本生成的版本。notebook只读取每个CSV的前两列，年度变量的预测标记不会进入该描述统计流程。

#### 3.4 当前notebook内容与进度

`notebook/descriptive.ipynb` 默认检查2012-01-31至2024-12-31的训练期，尚未使用2025年至2026年6月的留出期进行预测检验。当前读取9个连续指标文件，包括汇率、基础货币、储备、三项贸易指标、铁矿石 `NO_FILL` 版本及两项年度重复序列，不对政策事件虚拟变量进行本轮筛查。

1. **输入与描述统计：** 检查日期是否有效、重复或非月末，检查无穷值，按训练期月历对齐并保留缺失值；逐项展示有效样本数、均值、标准差、最小值、四分位数、中位数和最大值。
2. **图形与滚动统计：** 每个CSV生成一张含三个面板的图，展示原序列及12个月滚动均值、12个月滚动标准差，以及去除线性斜率后的月份均值。年度重复序列仅展示描述性滚动图，第三个面板标明不适用。
3. **趋势与季节性：** 对适用的月度序列估计含线性时间趋势和月份虚拟变量的OLS筛查模型，采用12阶HAC标准误，并对月份效应做联合Wald检验。存在缺失时仅使用最长连续完整区间，要求至少36个月；对本轮所有趋势与季节性检验的p值统一进行Holm校正，显著性水平为0.05。
4. **筛查标记：** 滚动均值的90%与10%分位数之差除以筛查区间标准差，达到1.0时提示均值漂移；滚动标准差的90%与10%分位数之比达到2.0时提示波动变化。这两个阈值是探索性设定。`screen_pass=True`表示本轮未触发信号，`False`表示存在信号或训练期缺口，`<NA>`表示不适用或无法判断；通过筛查不代表已证实平稳。
5. **当前结果与下一步：** 已保存9张图及汇总表。基础货币、食品进口、燃料进口和储备提示季节性；除基础货币外，其余6项可筛查指标均提示波动变化。`NO_FILL`铁矿石在训练期缺失32个月，有效观测为124个月；其他8个文件各有156个非空值。7项可筛查指标的 `screen_pass` 均为 `False`，两项年度重复序列为 `<NA>`；本轮未触发线性趋势或均值漂移提示。后续将开展ADF/KPSS检验，并比较包含与不包含月份虚拟变量的模型。正式汇率回归、伪样本外检验及情景与蒙特卡洛模拟仍待实现。

---

### I. Project Introduction

This project studies the relationship between changes in the Sierra Leone leone exchange rate and domestic monetary and fiscal conditions, foreign exchange supply and demand, and international commodity markets, with the aim of forecasting subsequent USDSLE movements. The research starts with macroeconomic factor regression and gradually incorporates policy events, pseudo out-of-sample forecasting, and scenario simulation to assess exchange rate changes and their uncertainty under different economic conditions.

The research background includes government financing and monetary expansion, foreign exchange demand arising from food and fuel imports, and foreign exchange earnings from exports of minerals such as iron ore. IMF research indicates that fiscal financing and monetary expansion were closely related to the rise in inflation from 2022 to 2023, and also discusses the pressure of food imports on the external balance and the effects of mining shocks on exports. These materials are used to formulate research questions and do not replace this project's own empirical tests. See the [IMF's Sierra Leone: Selected Issues](https://www.imf.org/-/media/files/publications/cr/2024/english/1sleea2024002-print-pdf.pdf), main text pp. 4, 36, and 50–56.

**The project focuses on the following questions:**

1. How are monetary growth, government debt, and changes in reserves related to appreciation and depreciation of the leone?
2. Can changes in the values or prices of fuel and food imports and iron ore exports explain additional exchange rate fluctuations?
3. Are the model relationships stable before and after policy adjustments, international financing, and other macroeconomic events?
4. Can the model provide effective forecasts for periods not used in estimation and reflect the range of risks under different scenarios?


### II. Initial Test Model and Testing Methods

#### 2.1 Initial Model

- The data cover January 1, 2012 to June 30, 2026. The model will use a pseudo out-of-sample approach, with data from 2012-01-01 to 2024-12-31 used for model fitting and testing, and data from 2025-01-01 to 2026-06-30 used to test forecast accuracy. Finally, the model will forecast foreign exchange data from 2026-06-30 to 2027-12-31.

- All regressions use the monthly data in `data/final_monthly/`. The current exchange rate change, event dummy, and converted macroeconomic factor files all retain 174 periods (January 2012 to June 2026), with month-end date labels from 2012-01-31 to 2026-06-30. `data/final_daily/` retains 5,295 daily periods (2012-01-01 to 2026-06-30) for checking events and dates. Log changes in base money, foreign exchange reserves, fuel imports, food imports, and iron ore exports have been converted and aligned monthly; monthly repetitions of annual percentage-point changes in government debt/GDP and current account/GDP have also been generated. Retaining 174 rows does not mean that every variable has 174 valid observations; the final usable sample depends on the coverage of the selected variables and the lag specification.

- Let E(t) denote the number of leones per US dollar in the current period and E(t−1) the exchange rate in the previous period. After harmonizing the old and new currency units, the exchange rate change is calculated as:

```text
Y(t) = 100 × [ln E(t) − ln E(t−1)]
```

- Here, t denotes the current period, t−1 the previous period, and ln the natural logarithm. Y(t) is the log change in the exchange rate and can be interpreted approximately as a percentage change. **Y(t) > 0 means that each US dollar buys more leones, indicating depreciation of the leone against the US dollar; Y(t) < 0 indicates appreciation of the leone.**


**The following is a candidate factor framework; the monthly baseline model selects factors from it according to the available data:**

```text
Y(t) = α + βY× Y(t-1)+ βM × M(t) + βR × R(t) + βO × O(t) + βF × F(t)
         + βD × D(t) + βC × C(t) + βI × I(t)
         + γ1 × P1(t) + … + γK × PK(t) + ε(t)
```

- Here, α is the intercept; βM, βR, and so on are the regression coefficients for the corresponding economic variables, indicating the relationship between a one-unit increase in that variable and the change in Y(t), holding other variables constant. P1(t) to PK(t) are K policy event variables, γ1 to γK are their respective regression coefficients, and ε(t) is the disturbance unexplained by the model. The economic variables are defined below:

- Candidate policy events are recorded in the [policy event table](data/source/Sierra_Leone_Policy_Events_2000_2026.csv). When using them, distinguish announcement dates, effective dates, date precision, and implementation status.

| Symbol | Meaning and definitions to be determined |
|---|---|
| Y(t-1) | USDSLE change in the previous period |
| M(t) | Log growth rate of base money, with data through 2026-04. Log change: 100 × [ln B(t) − ln B(t−1)]; **not the M2 growth rate** |
| R(t) | Foreign exchange reserve indicator: log change. Data through 2025-04 |
| O(t) | Change in fuel import value: log change, currently measured using imports of mineral fuels and lubricants |
| F(t) | Change in food import value: log change |
| D(t) | Annual change in government debt/GDP: the current year's ratio minus the previous year's ratio, in percentage points, repeated in every month of the same year |
| C(t) | Annual change in current account/GDP: the current year's ratio minus the previous year's ratio, in percentage points, repeated in every month of the same year |
| I(t) | Change in iron ore export value: log change. The original version retains forward fills in the source data, and consecutive filled values produce zero changes; the `NO_FILL` version excludes only two long fill intervals and the changes affected by them, while retaining earlier fills. Missing months cannot be used directly in regression. |
| P1(t) to PK(t) | Event dummy variables constructed according to policy dates and mechanisms of impact. |

The original frequency of government debt/GDP and current account/GDP remains annual. The existing monthly files repeat first differences of the annual ratios across the months of each statistical year, without taking logarithms, multiplying by 100 again, or dividing by 12; they retain `period_classification`, with 2026 values classified as projections. This alignment does not account for publication dates or when information became available, and the current notebook only displays descriptive rolling plots for these two series. They will not be included directly in the monthly baseline model until appropriate frequency treatment and information availability have been established. The existing monthly event table is coded as “1 if the event occurred during the month, otherwise 0”; whether to use persistent states or windows later will be determined separately according to the research specification.


#### 2.2 Factor Testing Workflow

1. **Check inputs:** Read regression inputs from `data/final_monthly/` and confirm the actual statistical periods, units, projection flags, and retained fill records. Exchange rate changes, event dummies, and macroeconomic factors are currently ordered by the same monthly dates; missing values, repeated annual values, and fill flags in the source files still need to be checked when using them.
2. **Descriptive statistics and stationarity:** Use `notebook/descriptive.ipynb` to examine training-period distributions, rolling statistics, linear trends, and calendar-month seasonality. Descriptive screening is complete, while ADF/KPSS tests have not yet been implemented; model variables will subsequently be determined using unit root tests and economic interpretation.
3. **Collinearity checks:** Calculate correlation matrices and VIFs for the variables and lag terms actually included in the model.
4. **Baseline estimation:** Estimate a parsimonious model using OLS, then extend it by variable group; report coefficients, confidence intervals, sample periods, and effective sample sizes.
5. **Residuals and stability:** Check autocorrelation, heteroskedasticity, the influence of outliers, and coefficient stability.
6. **Robustness and forecasting:** Compare reasonable variable definitions, lags, and sample specifications; compare models on a common sample to avoid mistaking sample changes for model improvements.

#### 2.3 Pseudo Out-of-Sample Testing


#### 2.4 Scenario and Monte Carlo Simulation

### III. Python Usage and Project Architecture

#### 3.1 Data Layers and Interpretation

- `data/source/`: Stores original downloads, source workbooks, and policy event materials for traceability. Current contents include old and new leone exchange rates, the US dollar index and pound sterling exchange rates, the base money and reserves workbook, IMF macroeconomic data, the trade workbook, the world cereal price index, fuel and iron ore market series, and GDP, inflation, unemployment, and trade balance materials.
- `data/cleaned/`: Stores intermediate series to track the cleaning process; retained annual series are used for background analysis and candidate extensions.
- `data/final_daily/`: Retains daily exchange rate changes and event dummies for checking events and dates.
- `data/final_monthly/`: The common input directory for subsequent regressions. It currently contains exchange rate changes, event dummies, log changes in base money and reserves, three trade log-change series, the iron ore `NO_FILL` version, and monthly repetitions of changes in two annual ratios, totaling 10 CSV files. All monthly files follow the dates and ordering of `USDSLE_monthly.csv`. Base money and reserves have 172 and 160 valid monthly changes, respectively; the original iron ore version has 174, while the `NO_FILL` version has 142, with the remaining 32 months left empty.
- [data/metadata.xlsx](data/metadata.xlsx): Records variable names, coverage dates, frequencies, projection status, transformation forms, forward fills, and sources for original and intermediate series. Coverage dates for base money and reserves are still recorded as December 2024 and have not yet been updated; current coverage and final transformation forms need to be checked against the existing CSVs and processing scripts. The README does not repeat the data source table.

In particular:

1. Coverage dates in the metadata describe statistical periods. Intermediate base money and reserve CSVs are labeled with the first day of the current month, intermediate trade CSVs with the first day of the following month, and annual ratio CSVs with January 1 of the following year; these are not publication dates. The processing scripts map them to the corresponding statistical month-end or statistical year. Read final files according to their actual date conventions rather than mechanically shifting them again.
2. Missing values are not zeros; forward fills are not additional actual observations; projections and historical observations should be identified separately.
3. Levels of CPI and commodity indices are not inflation rates or price changes. The intermediate base money file stores balances, while the final monthly file already contains log growth rates calculated from adjacent monthly balances; do not calculate growth rates again for final exchange rate and macroeconomic factor data that have already been converted to changes.
4. Old and new leone denominations, US dollar amounts in thousands/millions/billions, and dry versus wet tonnes of iron ore must be clearly distinguished. Different unit versions of the same economic variable should not be included simultaneously as independent explanatory variables.
5. Completing data cleaning does not mean that all series must enter the same model. The final sample should be determined jointly by the selected variables, while retaining the earlier observations needed to calculate growth rates and lags.

#### 3.2 Directory Structure

The following lists the actual data, script, and notebook directories and the subsequent code layout; directories and modules marked “planned” have not yet been created.

```text
SLE_research/
├── README.md
├── LICENSE
├── pyproject.toml           # Python dependencies and ipykernel development dependency
├── uv.lock                  # Dependency lock file
├── .python-version          # Python 3.13
├── data/
│   ├── metadata.xlsx
│   ├── source/
│   ├── cleaned/
│   ├── final_daily/          # Daily exchange rate and event data for checking events and dates
│   └── final_monthly/        # Monthly aligned data; includes macroeconomic changes, repeated annual values, and the NO_FILL version
├── scripts/
│   ├── prepare_trade_monthly.py
│   ├── prepare_money_reserves_monthly.py
│   ├── prepare_annual_changes_monthly.py
│   └── prepare_iron_ore_no_long_fill.py
├── notebook/
│   └── descriptive.ipynb     # Training-period descriptive statistics, rolling plots, and trend and seasonality screening
├── configs/                 # Planned: variables, lags, samples, and simulation parameters
├── src/                     # Planned
│   └── sle_research/
│       ├── data_io.py       # Read final data and metadata
│       ├── features.py      # Construct model features and lags not yet provided
│       ├── models.py        # Regression estimation
│       ├── diagnostics.py   # Statistical diagnostics
│       ├── backtest.py      # Pseudo out-of-sample testing
│       └── simulation.py    # Scenario and Monte Carlo simulation
├── outputs/                 # Planned: regression tables, diagnostics, forecasts, and plots
└── tests/                   # Planned: checks for dates, units, and information leakage
```

Analysis outputs such as regressions, diagnostics, forecasts, and plots should be saved in `outputs/`, without overwriting final input data. The current notebook displays plots and summary tables within its cells and does not yet export them to that directory. Record variables, samples, lags, standard error types, random seeds, and data versions for each run to support reproducibility.

#### 3.3 Python Environment and Reading Example

Python version: 3.13, with dependencies managed using uv. Use the following commands to install all Python dependencies:
```powershell
uv sync
uv add --dev ipykernel
```
All regressions use `final_monthly`; switch to `final_daily` only when checking daily data. Date parsing and subsequent model features should follow the column names in the final files and the metadata definitions. The `USDSLE_monthly` column in `USDSLE_monthly.csv` is already a log change multiplied by 100.

The current project dependencies include pandas, NumPy, Matplotlib, statsmodels, IPython, and datetime, with ipykernel as a development dependency. Open `notebook/descriptive.ipynb` in an editor that supports Jupyter, select the Python kernel corresponding to the project's `.venv`, and run the cells in order; the notebook can locate the data from either the project root or the `notebook/` directory.

The existing data processing scripts read intermediate data from `data/cleaned/` and write to `data/final_monthly/` using the 174 month-end dates in `USDSLE_monthly.csv` as the reference. When regeneration is needed, run `uv run python scripts/<script_name>.py` from the project root. The scripts perform the following tasks:

| Script | Current processing |
|---|---|
| `prepare_trade_monthly.py` | Calculates `100 × [ln X(t) − ln X(t−1)]` for imports of mineral fuels and lubricants, food imports, and iron ore exports, using December 2011 as the lag for the first period. Retains existing fills in the source files without adding new fills; leaves the change empty when the current or previous level is missing or nonpositive. |
| `prepare_money_reserves_monthly.py` | Calculates monthly log changes in base money and foreign exchange reserves using the same adjacent-month rules; uses the reserves column in millions of US dollars, without filling or forecasting missing values. |
| `prepare_annual_changes_monthly.py` | Repeats annual percentage-point changes in government debt/GDP and current account/GDP across the months of the same year, using 2011 as the lag for the first year and retaining data through statistical year 2026 and its projection flags. |
| `prepare_iron_ore_no_long_fill.py` | Starting from the original iron ore changes, excludes long forward-filled values from June 2018 to June 2019 and August 2019 to December 2020, and also leaves the July 2019 and January 2021 changes empty because they are affected by filled values in the preceding month, while retaining earlier fills. |

There are naming differences between current script outputs and the committed CSVs: value columns written by the change scripts use the `_log_change_pct` or `_annual_change_pp` suffix, while value columns in the committed continuous-indicator CSVs match their respective filenames without `.csv`; the iron ore variant script writes `iron_ore_exports_log_change_monthly_no_long_fill.csv`, whereas the current notebook reads `NO_FILL_iron_ore_exports_log_change_monthly.csv`. Check these differences before regenerating the files; the iron ore variant script reads the `iron_ore_exports_log_change_pct` column in the original version and therefore depends on the version generated by the trade script. The notebook reads only the first two columns of each CSV, so the projection flags for annual variables do not enter this descriptive statistics workflow.

#### 3.4 Current Notebook Contents and Progress

`notebook/descriptive.ipynb` checks the training period from 2012-01-31 to 2024-12-31 by default and has not yet used the held-out period from 2025 to June 2026 for forecast testing. It currently reads nine continuous-indicator files, including the exchange rate, base money, reserves, three trade indicators, the iron ore `NO_FILL` version, and two repeated annual series. Policy event dummies are not included in this round of screening.

1. **Inputs and descriptive statistics:** Checks for invalid, duplicate, or non-month-end dates and infinite values, aligns the data to the training-period monthly calendar, and retains missing values; displays the valid sample size, mean, standard deviation, minimum, quartiles, median, and maximum for each series.
2. **Plots and rolling statistics:** Generates one three-panel figure per CSV, showing the original series with its 12-month rolling mean, the 12-month rolling standard deviation, and calendar-month means after removing the linear slope. Repeated annual series receive only descriptive rolling plots, with the third panel marked as not applicable.
3. **Trends and seasonality:** For applicable monthly series, estimates an OLS screening model with a linear time trend and month dummies, uses HAC standard errors with 12 lags, and conducts a joint Wald test of month effects. When values are missing, only the longest complete continuous interval is used, with at least 36 months required; p-values from all trend and seasonality tests in this round are jointly adjusted using the Holm method, at a significance level of 0.05.
4. **Screening flags:** The difference between the 90th and 10th percentiles of the rolling mean, divided by the standard deviation over the screening interval, flags mean drift when it reaches 1.0; the ratio of the 90th to the 10th percentile of the rolling standard deviation flags volatility changes when it reaches 2.0. These two thresholds are exploratory settings. `screen_pass=True` means that no signal was triggered in this round, `False` means that signals or training-period gaps are present, and `<NA>` means that the method is not applicable or no judgment can be made; passing the screen does not establish stationarity.
5. **Current results and next steps:** Nine figures and a summary table have been saved. Base money, food imports, fuel imports, and reserves show seasonality signals; all six other screenable indicators besides base money show volatility-change signals. The `NO_FILL` iron ore series has 32 missing months in the training period and 124 valid observations; each of the other eight files has 156 nonmissing values. All seven screenable indicators have `screen_pass=False`, while the two repeated annual series have `<NA>`; no linear trend or mean drift signal was triggered in this round. Next, ADF/KPSS tests will be conducted, and models with and without month dummies will be compared. Formal exchange rate regression, pseudo out-of-sample testing, and scenario and Monte Carlo simulation remain to be implemented.

