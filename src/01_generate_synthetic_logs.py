# src/01_generate_synthetic_logs.py

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

n_wells = 28
depth_start = 2500.0
depth_end = 3100.0
step = 0.5

rows = []

for w in range(1, n_wells + 1):

    well_id = f"WELL_{w:02d}"
    depths = np.arange(depth_start, depth_end + step, step)

    for md in depths:
        if md < 2650:
            zone = "SEAL_TOP"
            gr_base = 115
            phi_base = 0.06
            rt_base = 2
        elif md < 2820:
            zone = "RES_A"
            gr_base = 45
            phi_base = 0.23
            rt_base = 35
        elif md < 2920:
            zone = "SEAL_MID"
            gr_base = 125
            phi_base = 0.05
            rt_base = 1.5
        else:
            zone = "RES_B"
            gr_base = 55
            phi_base = 0.18
            rt_base = 20

        gr = np.random.normal(gr_base, 8)
        nphi = max(0.01, np.random.normal(phi_base, 0.025))
        rhob = 2.65 - 0.75 * nphi + np.random.normal(0, 0.025)

        # Sonic em us/ft, valores realistas simplificados
        dt = 55 + 75 * nphi + 0.10 * gr + np.random.normal(0, 2.5)
        dts = 95 + 130 * nphi + 0.15 * gr + np.random.normal(0, 4.0)

        rt = max(0.2, np.random.lognormal(np.log(rt_base), 0.35))

        rows.append({
            "well_id": well_id,
            "md_m": md,
            "zone": zone,
            "gr_api": gr,
            "rhob_gcc": rhob,
            "nphi_vv": nphi,
            "dt_usft": dt,
            "dts_usft": dts,
            "rt_ohmm": rt
        })

df = pd.DataFrame(rows)
df.to_csv(RAW_DIR / "synthetic_logs_28_wells.csv", index=False)

print(df.head())
print(df.shape)





