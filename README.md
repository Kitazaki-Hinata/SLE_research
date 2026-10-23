<h3 align="center">塞拉利昂汇率研究</h3>

> 作者：Yi Yang

<p align="center">
    简体中文 | <a href="doc/README_EN.md">English</a>
</p>

### 一、项目介绍

本项目研究塞拉利昂利昂兑美元汇率（USDSLE）与货币、财政和外汇供求因素之间的关系。研究变量包括基础货币、外汇储备、燃料进口、食品进口、铁矿石出口、政府债务和经常账户。

目前已完成数据清洗与月度对齐、描述性统计、ADF/KPSS 平稳性检验，以及因子相关性和 VIF 检查。分析代码、图表和结果保存在三个 Jupyter 笔记本中。

### 二、初始测试模型与测试方法

#### 2.1 初始模型

月度数据位于 `data/final_monthly/`，覆盖 2012 年 1 月至 2026 年 6 月，共 174 个月末日期。当前诊断使用 2012 年 1 月至 2024 年 12 月的训练数据。

设 E(t) 为每美元兑换的利昂数量，汇率变化率为：

```text
Y(t) = 100 × [ln E(t) − ln E(t−1)]
```

Y(t) > 0 表示利昂贬值，Y(t) < 0 表示利昂升值。

初始模型的候选变量框架：

```text
Y(t) = α + βY × Y(t−1) + βM × M(t) + βR × R(t) + βO × O(t) + βF × F(t)
         + βD × D(t) + βC × C(t) + βI × I(t)
         + γ1 × P1(t) + … + γK × PK(t) + ε(t)
```

α 为截距，β 和 γ 为系数，ε(t) 为误差项。当前已完成该框架下的数据整理与因子诊断。

| 符号 | 变量定义 |
|---|---|
| Y(t−1) | 上一期 USDSLE 对数变化率 |
| M(t) | 基础货币对数变化率 |
| R(t) | 外汇储备对数变化率 |
| O(t) | 矿物燃料及润滑油进口额对数变化率 |
| F(t) | 食品进口额对数变化率 |
| D(t) | 政府债务/GDP 年度百分点变化，同年各月重复 |
| C(t) | 经常账户/GDP 年度百分点变化，同年各月重复 |
| I(t) | 铁矿石出口额对数变化率 |
| P1(t) 至 PK(t) | 政策事件 dummy：当月发生为 1，其余为 0 |

对数变化率统一按 `100 × [ln X(t) − ln X(t−1)]` 计算。政策记录见[政策事件表](data/source/Sierra_Leone_Policy_Events_2000_2026.csv)，数据来源与变量信息见[元数据表](data/metadata.xlsx)。

#### 2.2 检验因子流程

| 阶段 | 笔记本 | 已完成内容 |
|---|---|---|
| 描述性统计 | [1_descriptive.ipynb](notebook/1_descriptive.ipynb) | 样本与缺失检查、分布统计、滚动均值与标准差、趋势和季节性筛查 |
| 平稳性检验 | [2_adf.ipynb](notebook/2_adf.ipynb) | ADF、KPSS 及滞后设定敏感性检查，显著性水平为 0.05；年度变量按年检验 |
| 共线性检查 | [3_colinearity_check.ipynb](notebook/3_colinearity_check.ipynb) | 七个同期因子的 Pearson 相关矩阵、热力图、VIF 和矩阵秩；样本含 156 个月，使用原版铁矿石序列，排除 USDSLE 和政策 dummy |

当前结果：

- 描述性筛查发现部分序列存在季节性和波动变化。
- ADF/KPSS 结果支持月度序列和经常账户年度变化保留当前形式；政府债务年度变化的结论不明确。`NO_FILL` 铁矿石的平稳性检验使用最长连续区间，共 77 个月。
- 七因子的最大绝对相关系数为 0.4759，出现在基础货币与外汇储备之间。VIF 为 1.0056–1.3070，含截距的矩阵秩为 8，当前样本未显示明显多重共线性。

两项年度因子在训练期各有 13 个年度观测，逐月重复后用于共线性诊断。原版铁矿石保留源数据的前向填充；`NO_FILL` 版本剔除两段长期填充及受其影响的变化率，训练期保留 124 个月。

### 三、Python 使用方法与项目架构

#### 3.1 目录结构

主要文件结构：

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
│   ├── source/              # 原始数据
│   ├── cleaned/             # 整理后的中间数据
│   ├── final_daily/         # 日度汇率与政策事件数据
│   └── final_monthly/       # 月度分析数据
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

#### 3.2 运行方法

项目使用 Python 3.13 和 uv。在项目根目录安装依赖：

```powershell
uv sync
```

在支持 Jupyter 的编辑器中选择项目 `.venv` 的 Python 内核，按编号运行 `notebook/` 下的三个笔记本。笔记本支持从项目根目录或 `notebook/` 目录读取数据，表格和图形保存在笔记本内。

