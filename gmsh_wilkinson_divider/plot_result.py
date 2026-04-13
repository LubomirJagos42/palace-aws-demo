import matplotlib.pyplot as plt
import pandas as pd

# Load the file without header (columns will be numbered 0, 1, 2...)
df = pd.read_csv("sim_result/port-S.csv", comment='#', skiprows=1, header=None)

# Plot: column 0 = Frequency, column 1 = S11
plt.plot(df.iloc[:, 0], df.iloc[:, 1], marker='o', label="|S11| (dB)")
plt.plot(df.iloc[:, 0], df.iloc[:, 3], marker='x', label="|S21| (dB)")
plt.plot(df.iloc[:, 0], df.iloc[:, 5], marker='d', label="|S31| (dB)")

plt.xlabel("Frequency (GHz)")
plt.ylabel("S-param (dB)")
plt.title("S11, S21, S31vs Frequency")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
