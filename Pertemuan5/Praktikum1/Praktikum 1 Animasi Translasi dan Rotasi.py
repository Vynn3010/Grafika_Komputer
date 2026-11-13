import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
import numpy as np
import time

# ===== Nilai awal =====
DX_AWAL, DTHETA_AWAL = 0.1, 5        # jarak/frame bola, derajat/frame roda
FPS_BOLA_AWAL, FPS_RODA_AWAL = 30, 30
TICK_MS = 10                          # "detak" dasar timer (10 ms = 100 Hz)

# ===== Kanvas =====
fig, ax = plt.subplots(figsize=(8, 6))
plt.subplots_adjust(bottom=0.40)
ax.set_xlim(0, 10); ax.set_ylim(-1, 4)
ax.set_aspect('equal'); ax.axis('off')
ax.set_title("Translasi dan Rotasi", fontsize=16, fontweight='bold')

bola, = ax.plot(0, 2, 'o', color='red', markersize=20)
t = np.linspace(0, 2*np.pi, 100)
ax.plot(7 + np.cos(t), 2 + np.sin(t), color='gray', lw=6)
roda, = ax.plot([], [], '-', color='gray', lw=3)
sudut = np.linspace(0, 2*np.pi, 7)[:-1]

# Keterangan FPS masing-masing objek
txt_bola = ax.text(0.1, 3.9, "", ha='left', va='top', fontsize=10,
                   bbox=dict(boxstyle="round", fc="mistyrose", ec="red"))
txt_roda = ax.text(9.9, 3.9, "", ha='right', va='top', fontsize=10,
                   bbox=dict(boxstyle="round", fc="lightgray", ec="gray"))

# ===== Slider =====
def buat_slider(y, label, lo, hi, init, step):
    return Slider(plt.axes([0.25, y, 0.6, 0.035]), label, lo, hi,
                  valinit=init, valstep=step)

s_fps_b = buat_slider(0.30, 'FPS bola',          1, 120, FPS_BOLA_AWAL, 1)
s_dx    = buat_slider(0.24, 'Jarak bola (dx)',   0, 1.0, DX_AWAL, 0.01)
s_fps_r = buat_slider(0.16, 'FPS roda',          1, 120, FPS_RODA_AWAL, 1)
s_dt    = buat_slider(0.10, 'Putar roda (Δθ°)',  0, 60,  DTHETA_AWAL, 1)

btn = Button(plt.axes([0.42, 0.02, 0.16, 0.05]), 'Reset')
btn.on_clicked(lambda e: [s.reset() for s in (s_fps_b, s_dx, s_fps_r, s_dt)])

# ===== Keadaan =====
now0 = time.perf_counter()
st = {"x": 0.0, "theta": 0.0,
      "tb": now0, "tr": now0,          # waktu update terakhir bola / roda
      "fb": 0.0, "fr": 0.0,            # FPS aktual (dihaluskan)
      "nb": 0, "nr": 0}                # jumlah frame

def gerak_bola():
    st["x"] = (st["x"] + s_dx.val) % 10
    bola.set_data([st["x"]], [2])

def gerak_roda():
    st["theta"] += np.deg2rad(s_dt.val)
    xs, ys = [], []
    for a in sudut:
        xs += [7, 7 + np.cos(a + st["theta"]), np.nan]
        ys += [2, 2 + np.sin(a + st["theta"]), np.nan]
    roda.set_data(xs, ys)

def haluskan(lama, baru):
    return baru if lama == 0 else 0.8 * lama + 0.2 * baru

def update(_):
    now = time.perf_counter()

    # Bola diperbarui hanya jika sudah waktunya menurut FPS bola
    if now - st["tb"] >= 1.0 / s_fps_b.val:
        st["fb"] = haluskan(st["fb"], 1.0 / (now - st["tb"]))
        st["tb"] = now; st["nb"] += 1
        gerak_bola()

    # Roda diperbarui menurut FPS roda (terpisah dari bola)
    if now - st["tr"] >= 1.0 / s_fps_r.val:
        st["fr"] = haluskan(st["fr"], 1.0 / (now - st["tr"]))
        st["tr"] = now; st["nr"] += 1
        gerak_roda()

    # Kecepatan nyata = jarak per frame x FPS
    v_bola = s_dx.val * s_fps_b.val
    v_roda = s_dt.val * s_fps_r.val
    txt_bola.set_text(f"BOLA\nFPS target : {s_fps_b.val:.0f}\nFPS aktual : {st['fb']:.1f}\n"
                      f"Kecepatan  : {v_bola:.1f} satuan/detik")
    txt_roda.set_text(f"RODA\nFPS target : {s_fps_r.val:.0f}\nFPS aktual : {st['fr']:.1f}\n"
                      f"Kecepatan  : {v_roda:.0f} °/detik")
    return bola, roda, txt_bola, txt_roda

ani = animation.FuncAnimation(fig, update, interval=TICK_MS, blit=False,
                              cache_frame_data=False)
plt.show()