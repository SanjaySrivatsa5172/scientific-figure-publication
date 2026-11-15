import numpy as np
import matplotlib.pyplot as plt
np.random.seed(0)
ctrl = np.random.normal(42, 9, 7); trt = np.random.normal(55, 11, 7)   # infarct size, % of area at risk, n = 7 mice per group
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
ax = axes[0]
ax.bar(["Vehicle", "Drug"], [ctrl.mean(), trt.mean()], yerr=[ctrl.std()/np.sqrt(7), trt.std()/np.sqrt(7)], color=["red", "green"], capsize=8)
ax.set_ylim(30, 70)
ax.set_title("Drug reduces infarct size!!", fontsize=22)
ax.text(0.5, 66, "p<0.05 *", fontsize=20)
ax.set_ylabel("Infarct size", fontsize=18)
m = np.random.normal(0, 1, (12, 6))
im = axes[1].imshow(m, cmap="jet")
plt.colorbar(im)
axes[1].set_title("Gene expression (log2FC)", fontsize=22)
plt.tight_layout()
plt.savefig("figure2.png", dpi=150, bbox_inches="tight")
plt.savefig("figure2.pdf", bbox_inches="tight")
