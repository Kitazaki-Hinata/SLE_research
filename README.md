# Data Cleaning

Raw files are stored in `data/source/`, and cleaned CSV files are stored in `data/cleaned/`. The table below describes the transformations reflected in the current outputs.

| Source file | Cleaned file | Cleaning steps and value meaning |
| --- | --- | --- |
| `DXY1DTVC.csv` | `DXY1DTVC.csv` | Convert Unix timestamps to UTC dates, keep the original `close`, and remove other price and volume columns. Add missing calendar dates and forward-fill the last available close. Values are DXY closing levels. |
| `USDSLL1DICE.csv` | `USDSLL1DICE.csv` | Apply the same timestamp conversion, column selection, and daily forward-fill. Keep USD/SLL closing values at their original scale. |
| `USDSLE1DICE.csv` | `USDSLE1DICE.csv` | Apply the same timestamp conversion, column selection, and daily forward-fill. Keep USD/SLE closing values at their original scale. |
| `WORLDGDP.csv` | `SLEGDP.csv` | Skip the metadata preamble, select Sierra Leone (`SLE`), and reshape year columns into rows. Values are annual GDP growth (%); the initial missing value remains blank. |
| `SLEunemployment.xls` | `SLEunemployment.csv` | Read the `Data` sheet, remove metadata, and reshape year columns into rows. Values are unemployment as a percentage of the total labor force (modeled ILO estimate). Initial missing values remain blank. |
| `SLEBalanceofTrade.xls` | `SLEBalanceofTrade.csv` | Read the `Data` sheet, remove metadata, and reshape year columns into rows. Values are net trade in goods in current US dollars; negative values indicate a deficit. Forward-fill the missing 2025 value from 2024, leaving initial missing values blank. |
| `WORLDInfla.xlsx` (`hcpi_m` sheet) | `SLE_hcpi_m.csv` | Select Sierra Leone, remove metadata, and reshape monthly columns into rows. Values are headline consumer price index levels, preserved without conversion to inflation rates. |
| `WORLDInfla.xlsx` (`fcpi_m` sheet) | `SLE_fcpi_m.csv` | Select Sierra Leone, remove metadata, and reshape monthly columns into rows. Values are food and non-alcoholic beverage price index levels, preserved without conversion to inflation rates. |

Each cleaned CSV has a header and two columns: `date,close` for the three daily market series, or `date,value` for the annual and monthly economic series. Rows are in ascending date order. Blank numeric fields mean missing data, not zero; both CPI files retain their initial missing observations.

Read `date` as an eight-digit `YYYYMMDD` string. Daily dates refer to the corresponding calendar day, including added dates carrying the previous close. Annual observations are labeled **January 1 of the following year** (the 2025 GDP value appears at `20260101`). Monthly observations are labeled **the first day of the following month** (January 2007 CPI appears at `20070201`). These labels describe period alignment rather than verified publication dates.

For example, load a cleaned file with pandas and parse its date column explicitly:

```python
import pandas as pd

df = pd.read_csv("data/cleaned/SLEGDP.csv", dtype={"date": "string"})
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
```
