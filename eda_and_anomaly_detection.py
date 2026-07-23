import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

# load data
df = pd.read_csv("tokenised_transactions.csv")
print(df.shape)
print(df.dtypes)

# remove duplicates
duplicate_count = df.duplicated("TransactionID").sum()
print(f"Duplicates: {duplicate_count}")
df = df.drop_duplicates(subset="TransactionID")

# check missing values
missing = df.isna().sum()
print(missing[missing > 0])

# settlement time is null for pending/failed txns, that's expected
df["SettlementTime_Missing_Reason"] = np.where(
    df["SettlementTime_Seconds"].isna(), df["SettlementStatus"], "N/A"
)

# fix types
df["Date"] = pd.to_datetime(df["Date"])
df["Amount_USD"] = pd.to_numeric(df["Amount_USD"], errors="coerce")

# drop invalid amounts
df = df[df["Amount_USD"] > 0]
print(df.shape)

# summary stats
print(df["Amount_USD"].describe())

# group by asset type
by_asset = df.groupby("AssetType").agg(
    txn_count=("TransactionID", "count"),
    total_volume=("Amount_USD", "sum"),
    avg_amount=("Amount_USD", "mean"),
    avg_settlement_sec=("SettlementTime_Seconds", "mean"),
).sort_values("total_volume", ascending=False)
print(by_asset.round(2))

# group by network
by_network = df.groupby("Network").agg(
    txn_count=("TransactionID", "count"),
    avg_settlement_sec=("SettlementTime_Seconds", "mean"),
    failure_rate=("SettlementStatus", lambda s: (s == "Failed").mean()),
)
print(by_network.round(3))

# log transform amount, then z-score
df["log_amount"] = np.log1p(df["Amount_USD"])
mean_log = df["log_amount"].mean()
std_log = df["log_amount"].std()
df["z_score"] = (df["log_amount"] - mean_log) / std_log

# flag anomalies
Z_THRESHOLD = 3.0
df["is_anomalous"] = df["z_score"].abs() > Z_THRESHOLD

anomalies = df[df["is_anomalous"]].sort_values("z_score", ascending=False)
print(f"Anomalies: {len(anomalies)} of {len(df)}")
print(anomalies[["TransactionID", "SendingInstitution", "ReceivingInstitution",
                  "Amount_USD", "z_score", "SettlementStatus"]].head(10))

# chart 1: amount distribution with threshold line
plt.figure(figsize=(9, 5))
sns.histplot(df["log_amount"], bins=50, kde=True, color="#00395D")
plt.axvline(mean_log + Z_THRESHOLD * std_log, color="red", linestyle="--")
plt.axvline(mean_log - Z_THRESHOLD * std_log, color="red", linestyle="--")
plt.title("Transaction Amount Distribution with Anomaly Threshold")
plt.xlabel("log(Amount USD + 1)")
plt.tight_layout()
plt.savefig("chart_amount_distribution.png", dpi=150)
plt.close()

# chart 2: volume by asset type
plt.figure(figsize=(9, 5))
by_asset_sorted = by_asset.sort_values("total_volume")
sns.barplot(x=by_asset_sorted["total_volume"] / 1e6, y=by_asset_sorted.index, color="#00A9E0")
plt.title("Total Volume by Asset Type")
plt.xlabel("Volume (USD millions)")
plt.ylabel("")
plt.tight_layout()
plt.savefig("chart_volume_by_assettype.png", dpi=150)
plt.close()

# chart 3: settlement time by network
plt.figure(figsize=(9, 5))
sns.boxplot(data=df, x="Network", y="SettlementTime_Seconds")
plt.title("Settlement Time by Network")
plt.ylabel("Settlement Time (seconds)")
plt.tight_layout()
plt.savefig("chart_settlement_time_by_network.png", dpi=150)
plt.close()

# chart 4: scatter, anomalies highlighted
plt.figure(figsize=(9, 5))
sns.scatterplot(data=df, x="Amount_USD", y="SettlementTime_Seconds",
                 hue="is_anomalous", palette={True: "red", False: "#00A9E0"}, alpha=0.6, s=25)
plt.xscale("log")
plt.title("Amount vs Settlement Time - Anomalies Highlighted")
plt.xlabel("Amount USD (log scale)")
plt.ylabel("Settlement Time (seconds)")
plt.tight_layout()
plt.savefig("chart_anomaly_scatter.png", dpi=150)
plt.close()

# export for power bi
df.to_csv("tokenised_transactions_cleaned_flagged.csv", index=False)
print("done")
