import pandas as pd
import matplotlib.pyplot as plt

# Load the file without header (columns will be numbered 0, 1, 2...)
df = pd.read_csv("sim_results/port-S.csv", comment='#', skiprows=1, header=None)
df2 = pd.read_csv("sim_results_2/port-S.csv", comment='#', skiprows=1, header=None)

# Plot: column 0 = Frequency, column 1 = S11
plt.plot(df.iloc[:, 0], df.iloc[:, 1], marker='o', label="|S11| (dB)")
plt.plot(df2.iloc[:, 0], df2.iloc[:, 1], marker='x', label="|S11| (dB)")

plt.xlabel("Frequency (GHz)")
plt.ylabel("S11 (dB)")
plt.title("S11 vs Frequency")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
