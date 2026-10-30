本目录保存按发布日期对齐的实际因子，以及按指定年度日期启用的 IMF 模拟预测因子。五组实际值和预测值互斥填充，同一指标同一天最多一列有数值。

输出日期逐行复制 `USDSLE_daily.csv` 的 `date`，保留现有格式和周末，共 5,295 行，范围为 2012/1/1 至 2026/6/30。汇率、政策事件、原始月度输入和 `../IMF_predict_data/` 原始文件均保留。

超出此日历的年度差分仍保存在 `metadata/imf_prediction_calendar.csv`，包括至 2031 年的输入；本次没有将它们提前放入日度文件，也没有扩展汇率日历。

五个实际因子文件及五个 `PREDICT_IMF` 文件均只有两列：`date` 和数据列。实际因子的原数值列名保留；债务的 `period_classification` 移出日度输入，分类信息仍可在发布记录中核对。

| 实际文件 | 对应预测文件 |
|---|---|
| `headline_cpi_log_change_daily.csv` | `PREDICT_IMF_headline_cpi_log_change_daily.csv` |
| `gdp_annual_pct_change_daily.csv` | `PREDICT_IMF_gdp_annual_pct_change_daily.csv` |
| `trade_balance_annual_pct_change_daily.csv` | `PREDICT_IMF_trade_balance_annual_pct_change_daily.csv` |
| `fx_reserves_log_change_daily.csv` | `PREDICT_IMF_fx_reserves_log_change_daily.csv` |
| `general_government_gross_debt_annual_change_pp_daily.csv` | `PREDICT_IMF_general_government_gross_debt_annual_change_pp_daily.csv` |

预测值的差分在原始年度数据上完成，再按更新日期展开到日历。设 `y` 为目标年份，差分必须使用同一原始序列中相邻的 `y`、`y−1` 两年。

| 指标 | 采用的 IMF 原始列 | 差分公式 | 模拟更新日期 |
|---|---|---|---|
| CPI | `cpi_annual_average_index_dec2021_100` | `100 × [ln CPI(y) − ln CPI(y−1)]` | 目标年份 10 月 13 日 |
| GDP | `real_gdp_growth_pct` | `100 × [g(y) − g(y−1)] / abs(g(y−1))` | 目标年份 10 月 13 日 |
| 政府债务 | `general_government_gross_debt_pct_gdp` | `Q(y) − Q(y−1)` | 目标年份 10 月 13 日 |
| 贸易差额 | `goods_trade_balance_usd_million` | `100 × [TB(y) − TB(y−1)] / abs(TB(y−1))` | 目标年份 7 月 7 日 |
| 外汇储备 | `gross_reserves_excl_swaps_with_rsf_usd_million` | `100 × [ln R(y) − ln R(y−1)]` | 目标年份 5 月 29 日 |

GDP 和贸易差额使用基期的绝对值作分母，保留变化方向。债务直接相减，单位为百分点，不对结果取绝对值。CPI 和储备预测仍为年度对数变化，实际文件中的对应值仍为月度对数变化；它们没有被转换为相同统计期的指标。日度展开不除以 12 或 365，也不在更新日期之间插值。

相邻基期缺失、原值缺失、百分比差分的分母为零，或对数差分的原值非正时，差分留空。原始文件范围以外的目标年份也留空，不使用其他年份补造。首个年度观测只作为基期，其差分为空。

固定年度日期是本次指定的模拟规则。原始文件只有 WEO October 2026 和 Country Report 26/168 两个发布版本，其中既有实际、初步值，也有估计和预测。本次按要求将各目标年份的数据用作模拟预测输入，并保留原始分类、版本和原报告发布日期。不能据此声称这些数值在各历史年份已经公开可得。储备的 5 月 29 日也仅作为指定的模拟启用日。

互斥切换按以下规则执行：

- 每年到达指定预测更新日，有效的新预测启用，实际列从当天起留空。如果该年预测缺失或缺少差分基期，预测列留空，已经启用的实际值继续保留。
- 如果上一年的预测仍在使用，而下一年度更新日缺少有效新预测，旧预测在该日过期，两列暂时留空。随后等同一目标年份或更新年份的实际数据发布，或有效新预测出现；不继续填充旧预测。
- 预测启用后，在同一目标年份或更新年份的实际数据随后发布时，切回实际列，预测列从当天起留空。已经在预测启用前发布过的实际值不会立即清掉新预测；迟到的旧年份实际值也不会覆盖较新年份预测。
- CPI 和储备沿用现有月度实际发布记录，在预测启用后，同一目标年份的下一次月度实际数据发布时切回。随后继续按实际发布记录更新，直到下一年度预测启用。
- 预测与符合条件的实际数据同日更新时，实际值优先。没有后续实际发布记录时，当前预测保持到下一年度预测更新日；不会补造实际更新事件。
- 实际状态中的已知值保持到后续有效发布或预测切换事件。未取得任何可用数据的日期留空。缺失与因互斥而停用的空值在元数据中区分。

例如 GDP 在 2025-10-13 启用 2025 年模拟预测，实际列中的旧年份值随即留空；2026-06-18 发布 2025 年实际值后，实际列恢复，预测列留空。

实际发布事件从 `metadata/publication_calendar.csv` 重建，避免直接使用已经遮蔽的日度文件再次处理。债务原始日度列曾在 2026-04-14 选用 2026 年 `Projection (2026+)` 值；本次排除这条预测，将同日发布的 2025 年 `-1.5` 接回实际列。该观测在原来源中标为 `Earlier year`，不代表已独立核实为最终实际值。

实际数据的发布时间保留原有规则：能够核实对应统计期公告日期时采用公告日期；缺少可采用日期时，月度使用次月 15 日，年度使用次年 6 月 18 日。只有数据库更新批次、下载日期或报告月份的证据不作为精确发布日期。日期对齐采用日末信息约定，从可用日开始使用；若用于预测当日开盘前的汇率，需要另外限制实际信息时点。

基础发布证据覆盖 360 个非空宏观统计期：CPI 有 151 期采用公告所印日期，7 期因日期矛盾使用假设日期；储备 160 期使用次月 15 日；GDP 的 14 期、贸易差额的 13 期和债务的 13 个历史年度使用次年 6 月 18 日；债务另 2 期使用已识别版本日期。现有数值没有重建历史首次发布版本，因此发布时间对齐仍保留数据修订的限制。实际储备采用 IMF IFS 不含黄金口径，预测储备采用报告中排除 swaps、包含 RSF 的口径，二者定义尚未统一。

政策事件文件保持六个单日脉冲。事件按公告日、投票日或实施日安排，不作月度发布延迟，也不向后填充。改值公告使用央行网页标注的 2021-08-12，PDF 签发日及旧记录的 2021-08-11 保留在证据中；Brexit 为 2016-06-23，SDR 分配生效日为 2021-08-23。

| 元数据文件 | 用途 |
|---|---|
| `metadata/publication_calendar.csv` | 实际输入的基础发布记录，包含值、分类、采用日期、证据和未采用候选日期；其中选用天数属于互斥处理前的基础结果 |
| `metadata/daily_factor_availability.csv` | 互斥处理前的日度实际信息来源和数据年龄 |
| `metadata/alignment_summary.json` | 基础发布日期对齐的数量、规则和输入 SHA-256 |
| `metadata/*_evidence.csv` | 逐期实际发布证据与政策事件日期证据 |
| `metadata/imf_prediction_calendar.csv` | 年度预测变换、模拟启用日期及原始来源记录 |
| `metadata/imf_prediction_daily_availability.csv` | 最终互斥输出的逐日状态、实际或预测来源及缺失原因 |
| `metadata/imf_prediction_summary.json` | 最终输出统计、处理规则和输入校验信息 |

从项目根目录生成或重建最终互斥数据：

```powershell
python scripts/prepare_imf_prediction_daily.py
```

只读核对最终结果：

```powershell
python scripts/prepare_imf_prediction_daily.py --check
```

默认使用下一次同年月度实际发布日切回和包含 RSF 的储备列。可用 `--monthly-switch december_release` 改为等待目标年份 12 月实际数据发布，或用 `--reserves-scenario without_rsf` 改为不含 RSF 的储备列。核对时需要传入生成数据时相同的选项。

基础脚本 `python scripts/prepare_pos_daily_factors.py` 仍用于重建原始发布日期对齐结果。运行它会恢复未遮蔽的实际日度文件，因此随后需要再次运行 `prepare_imf_prediction_daily.py`。基础脚本的 `--check` 仅适用于基础结果阶段；最终互斥文件应使用新脚本的 `--check`。

互斥留空避免同一指标的两列同时填值，但不能保证与其他解释变量之间不存在共线性。后续回归不能将实际列和预测列一起执行整行 `dropna`，否则会删除互斥样本。应根据逐日状态区分停用项和真正缺失，再设计模型编码；本次 CSV 不将空值改为零。
