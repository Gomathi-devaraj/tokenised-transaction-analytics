# Tokenised Money Settlement Dashboard — Build Guide

**Concept:** A project analyzing tokenised transaction settlement across institutions —
directly mirrors the themes in Barclays' "Tokenisation: The Next Chapter in Money's Evolution"
(interoperability, settlement speed, cross-institution risk). Built as a two-stage pipeline:
**Python does the cleaning, EDA, and anomaly detection → Power BI does the interactive
dashboard layer.** This is deliberate — it's the one project that proves SQL + Python +
Power BI together, instead of three separate projects that each show only one skill.

Dataset: `tokenised_transactions.csv` (3,000 synthetic transactions, Jan–Jul 2026)

## 0. Python Stage (run this first)

Run `eda_and_anomaly_detection.py` (Pandas, NumPy, Matplotlib, Seaborn) before touching Power BI.
It:
- Cleans the raw extract: drops duplicates, audits missing values (and explains *why* they're
  missing — `SettlementTime_Seconds` is null for Pending/Failed transactions structurally, not
  due to bad data), validates amounts
- Produces summary statistics and group-by breakdowns (by asset type, by network)
- Flags anomalous transactions using a **z-score on log-transformed amount** (log transform
  because the amounts are right-skewed/log-normal — a raw z-score would just flag "big
  transactions," while the log version flags amounts that are unusual *relative to typical
  activity*)
- Produces 4 charts: amount distribution with anomaly threshold, volume by asset type,
  settlement time by network (boxplot), and an anomaly scatter (amount vs. settlement time)
- Exports `tokenised_transactions_cleaned_flagged.csv` — this enriched file (with `z_score` and
  `is_anomalous` columns added) is what Power BI imports, not the raw CSV

This is your answer to "walk me through a Python project": cleaning logic, a documented
statistical method (z-score, log-transform reasoning), and visual output — all in one script
you can explain line by line.

## 1. Data Model (star schema)
Import `tokenised_transactions_cleaned_flagged.csv` (the Python output, not the raw file) and
build these dimension tables in Power Query:
- **Fact_Transactions** — TransactionID, Date, SendingInstitution, ReceivingInstitution, AssetType,
  Network, Region, Amount_USD, SettlementStatus, SettlementTime_Seconds,
  TraditionalRail_Benchmark_Hours, Fee_BPS, Fee_USD, z_score, is_anomalous
- **Dim_Date** — standard date table (Date, Year, Month, MonthName, Week, Quarter)
- **Dim_Institution** — unique list of institutions (for slicers)
- **Dim_AssetType** — unique list of asset types

Relationships: Fact_Transactions[Date] → Dim_Date[Date] (many-to-one)

## 2. Key DAX Measures

```dax
Total Volume USD = SUM(Fact_Transactions[Amount_USD])

Settled Transactions = 
CALCULATE(COUNTROWS(Fact_Transactions), Fact_Transactions[SettlementStatus] = "Settled")

Settlement Success Rate = 
DIVIDE([Settled Transactions], COUNTROWS(Fact_Transactions))

Avg Settlement Time (sec) = 
AVERAGE(Fact_Transactions[SettlementTime_Seconds])

Avg Traditional Rail Time (hrs) = 
AVERAGE(Fact_Transactions[TraditionalRail_Benchmark_Hours])

Speed Improvement Factor = 
DIVIDE([Avg Traditional Rail Time (hrs)] * 3600, [Avg Settlement Time (sec)])

Total Fees USD = SUM(Fact_Transactions[Fee_USD])

Avg Fee (bps) = AVERAGE(Fact_Transactions[Fee_BPS])

Failed Transaction Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_Transactions), Fact_Transactions[SettlementStatus]="Failed"),
    COUNTROWS(Fact_Transactions)
)

MoM Volume Growth % = 
VAR CurrMonth = [Total Volume USD]
VAR PrevMonth = CALCULATE([Total Volume USD], DATEADD(Dim_Date[Date], -1, MONTH))
RETURN DIVIDE(CurrMonth - PrevMonth, PrevMonth)
```

## 3. Page Layout (3 pages)

**Page 1 — Executive Overview**
- KPI cards: Total Volume, Settlement Success Rate, Avg Settlement Time (sec) vs Avg Traditional
  Rail Time (hrs), Speed Improvement Factor
- Line chart: Daily/weekly volume trend
- Donut: Volume share by AssetType
- Map or bar: Volume by Region

**Page 2 — Settlement & Network Performance**
- KPI card: **Anomalous Transactions** — `Anomaly Count = CALCULATE(COUNTROWS(Fact_Transactions), Fact_Transactions[is_anomalous] = TRUE)` — a headline number showing how many flagged transactions exist
- Bar chart: Avg Settlement Time by Network type (Permissioned / Public / Hybrid) — this is the
  "interoperability" story: show permissioned ledgers settle faster but public blockchain
  scales wider
- Scatter: Settlement Time vs Transaction Amount, colour-coded by `is_anomalous` (red for
  flagged, blue for normal) — this recreates the Python anomaly scatter chart, but interactive:
  hover/filter by institution or asset type live
- Table: **Flagged Transactions** — filtered to `is_anomalous = TRUE`, showing TransactionID,
  SendingInstitution, ReceivingInstitution, Amount_USD, z_score, SettlementStatus — this is the
  "drill into the suspicious ones" view
- Stacked bar: Settlement Status (Settled/Pending/Failed) by Institution — a proxy for
  "which institutions/networks are most reliable," echoing the interoperability risk theme
- Slicer: `is_anomalous` toggle, so the whole page can filter to "anomalies only" with one click

Extra DAX for this page:
```dax
Anomaly Count = 
CALCULATE(COUNTROWS(Fact_Transactions), Fact_Transactions[is_anomalous] = TRUE)

Anomaly Rate = 
DIVIDE([Anomaly Count], COUNTROWS(Fact_Transactions))
```

**Page 3 — Institution & Cost Analysis**
- Matrix: Sending → Receiving institution volume (who transacts with whom — visualizes the
  "network effect" / interoperability gap Barclays raises)
- Bar: Total fees by AssetType
- Card: Avg Fee (bps) — compare tokenised fee basis points to typical legacy cross-border fees
  (~20-50 bps) in your write-up as a talking point
- Slicers: Date range, Region, Network

## 4. The narrative to attach when you post it
Frame it as: *"Barclays' piece on tokenisation talks about interoperability and settlement speed
as the open questions. I built a mock dashboard to visualize what those tradeoffs actually look
like in transaction data — permissioned vs public networks, settlement time, and failure rates
across institutions."*

This shows you can translate an industry concept into a data model — which is the actual skill,
not just reacting to the article.
