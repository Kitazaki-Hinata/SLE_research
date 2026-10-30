本目录将第二轮回归因子按发布日期对齐到 `USDSLE_daily.csv` 的日历。

输入为 `../2_regression_monthly/` 中的五个宏观因子及政策事件文件。已有汇率文件、原始月度文件、因子数值和单位均保留。输出日期逐行复制本目录汇率文件的 `date`，包括其现有格式和周末，共 5,295 行，范围为 2012/1/1 至 2026/6/30。

| 日度输出文件 | 数值列及含义 |
|---|---|
| `headline_cpi_log_change_daily.csv` | `headline_cpi_log_change_monthly`，最新可用的月度 CPI 对数变化率 |
| `fx_reserves_log_change_daily.csv` | `fx_reserves_log_change_monthly`，最新可用的月度储备对数变化率 |
| `gdp_annual_pct_change_daily.csv` | `gdp_annual_pct_change_monthly`，最新可用的 GDP 增长率年度相对变化 |
| `trade_balance_annual_pct_change_daily.csv` | `trade_balance_annual_pct_change_monthly`，最新可用的贸易差额年度相对变化 |
| `general_government_gross_debt_annual_change_pp_daily.csv` | 原债务变化列及 `period_classification`，最新可用的年度债务/GDP 百分点变化 |
| `Sierra_Leone_Policy_Event_Dummies_daily.csv` | 与月度输入相同的六个事件列，各为单日脉冲 |

文件名中的 `daily` 表示日期频率。数值列继续使用原名，月度或年度变化率没有被转换成每日变化率，也没有除以天数。年度输入中重复在各月的同一数值先按统计年合并。

能够核实对应统计期公告日期时，采用公告日期。找不到可采用的日期时，按指定规则使用次月15日或次年6月18日。只有全球数据库更新批次、下载日期或报告月份的证据，不能当作塞拉利昂该期数据的精确发布日期；这些候选证据保存在年度证据表中。

本次检查了360个非空宏观统计期。CPI有151期采用公告所印日期，7期因公告日期早于统计期等矛盾使用假设日期；储备160期使用次月15日；GDP的14期、贸易差额的13期及债务的13个历史年度使用次年6月18日；债务另外2期采用已识别版本的发布日期。各期证据和未采用候选日期均保留。

宏观因子从可用日期起向后延续，直至更晚统计期的数据可用。首个可用日期以前留空；缺少新一期观测时继续保留最后已知值，不补造新观测。`metadata/daily_factor_availability.csv` 逐日记录原统计期、可用日期及数据年龄，能够识别长时间未更新的值。发布超出汇率日历范围的观测保留在发布日历中，不提前放入日度文件。

对齐采用日期粒度及日末信息约定：发布日期若存在于汇率日历，就从该日开始使用；否则顺延到下一个存在的日期。不在本步骤调整报价时区、交易时段或日历。若用于预测发布当日开盘前的汇率，应另按实际预测时点限制可用信息。

2025、2026年债务观测的来源版本为 IMF WEO April 2026，按其发布日2026-04-14对齐。两期同日可用时，单列采用较新统计期2026，且保留 `Projection (2026+)` 标记；2025年观测仍保存在发布日历内。此规则没有把2026年预测值当作实际值。晚公布的旧统计期不会覆盖已可用的新统计期。

政策事件按各自定义使用公告日、投票日或实施日，不作月度发布延迟，也不向后填充。改值公告在新输出采用央行网站标注的2021-08-12公开日期，PDF签发日及旧事件表日期2021-08-11保留在证据备注。Brexit列指2016-06-23投票日，SDR列指2021-08-23分配生效日，均不能直接解释为当日意外消息。

`metadata/publication_calendar.csv` 列出每个非空统计期的原值、采用日期、日期依据、候选日期及来源链接。`first_eligible_date` 为可用日之后首个参考日；`selected_on_days` 和 `first_selected_date` 记录实际被日度列选用的天数及首次选用日期。多个统计期同日发布或旧期迟发时，部分观测可能没有单独占据日度列，但全部保留在发布日历中。`metadata/alignment_summary.json` 汇总实际日期与假设日期数量、输出情况和输入文件 SHA-256。其余 `*_evidence.csv` 为逐期检索证据。

此次只调整已有数值的时间安排，没有重建历史初次发布版本。CPI公告日期不能证明现有 World Bank 数值在当时未经修订；年度值和储备也有同样限制。假设日期只用于本次 POS 数据准备，不代表已经确认实际发布时点。储备采用 IMF IFS 不含黄金口径，未借用 BSL 总外储的发布日期。

在项目根目录重建数据：

```powershell
python scripts/prepare_pos_daily_factors.py
```

只检查输出与证据表是否一致，不写文件：

```powershell
python scripts/prepare_pos_daily_factors.py --check
```
