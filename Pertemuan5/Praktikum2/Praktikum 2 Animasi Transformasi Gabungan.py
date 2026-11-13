"""
Praktikum 2 - Pelari: kecepatan bisa diatur + HUD (frame, waktu, jarak, speed, PACE)

Transformasi badan   : M_badan   = T . R . S
Transformasi anggota : M_anggota = M_badan . T(pivot) . R(sudut) . T(-pivot)

Kontrol (mode tampil):
    Slider "Kecepatan"  : geser untuk mempercepat / memperlambat pelari
    Tombol keyboard     : Up atau +  = tambah 1 km/jam | Down atau - = kurangi 1 km/jam | R = reset
Mode simpan GIF (otomatis akselerasi dari jalan santai sampai sprint):
    python pelari_berlari_v3.py --simpan
File satu folder: latar.png dan bagian_*.png (badan, lengan_kiri, lengan_kanan, kaki_kiri, kaki_kanan)
"""
import os, sys, time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Ellipse, Rectangle
from matplotlib.transforms import Affine2D
from matplotlib.widgets import Slider, Button
from itertools import count

# =============== PARAMETER YANG BOLEH DIUBAH ===============
URUTAN        = "TRS"   # urutan transformasi badan (coba "RTS", "STR", ...)
FPS           = 30
KMH_AWAL      = 8.0     # kecepatan awal (km/jam)
KMH_MAKS      = 30.0    # batas slider
PX_PER_METER  = 80      # skala dunia: 80 piksel = 1 meter (pelari setinggi ~1,5 m)
PANJANG_LANGKAH_M = 0.9 # panjang 1 langkah (m); 1 siklus kaki kiri+kanan = 2 langkah
AYUN_CEPAT    = 1.6     # pengali kecepatan ayunan kaki & tangan (1 = normal, makin besar = makin cepat)
TINGGI_AWAL   = 125     # tinggi pelari (piksel)
Y_JALAN       = 78      # posisi kaki di jalan (piksel dari bawah)

SKALA_AMP     = 0.03    # denyut scaling badan
ROTASI_AMP    = 3.0     # goyang badan (± derajat)
LOMPAT_AMP    = 6       # tinggi lompatan maksimum (piksel)
KAKI_AMP      = 32.0    # ayunan kaki maksimum (± derajat)
TANGAN_AMP    = 28.0    # ayunan tangan maksimum (± derajat)
AYUN_MIN      = 0.75    # ayunan minimum saat lambat (0..1) agar kaki & tangan tetap kelihatan bergerak

N_DEMO        = 135     # jumlah frame GIF (mode --simpan)
KMH_DEMO      = (5.0, 24.0)   # akselerasi GIF: dari ... sampai ... km/jam
# ===========================================================

try:
    folder = os.path.dirname(os.path.abspath(__file__))
except NameError:
    folder = os.getcwd()
# folder = r"E:\SEMESTER 5\Grafika Komputer\Pertemuan6\Praktikum2"   # <- isi manual jika perlu

SIMPAN = "--simpan" in sys.argv

latar = plt.imread(os.path.join(folder, "latar.png"))
H, W = latar.shape[:2]
bagian = {n: plt.imread(os.path.join(folder, f"bagian_{n}.png"))
          for n in ["kaki_kiri", "kaki_kanan", "lengan_kiri", "lengan_kanan", "badan"]}
ph, pw = bagian["badan"].shape[:2]
k = TINGGI_AWAL / ph
lw, lh = pw * k, ph * k

PIVOT_PX = {"lengan_kiri": (56, 180), "lengan_kanan": (148, 190),
            "kaki_kiri": (68, 288),   "kaki_kanan": (100, 286)}
PIVOT = {n: ((x - pw / 2) * k, (ph - y) * k) for n, (x, y) in PIVOT_PX.items()}
SIKLUS_PX = 2 * PANJANG_LANGKAH_M * PX_PER_METER    # jarak (piksel) per 1 siklus langkah

# ---------- Matriks homogen 3x3 ----------
def S(sx, sy): return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], float)
def R(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)
def T(dx, dy): return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)

# ---------- Kanvas: adegan (atas) + panel kontrol (bawah) ----------
PANEL = 90
fig = plt.figure(figsize=(W / 100, (H + PANEL) / 100), dpi=100)
ax = fig.add_axes([0, PANEL / (H + PANEL), 1, H / (H + PANEL)])
ax.imshow(latar, extent=(0, W, 0, H), zorder=0)

bayangan = Ellipse((0, Y_JALAN - 4), lw * 0.7, 12, color="black", alpha=0.3, zorder=1)
ax.add_patch(bayangan)
garis_cepat = [ax.plot([], [], color="white", lw=2, alpha=0, zorder=1.5, solid_capstyle="round")[0]
               for _ in range(7)]

zorder = {"kaki_kiri": 2, "kaki_kanan": 2, "lengan_kiri": 3, "lengan_kanan": 3, "badan": 4}
layer = {n: ax.imshow(img, extent=(-lw / 2, lw / 2, 0, lh), zorder=zorder[n])
         for n, img in bagian.items()}
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

# ---------- HUD ----------
gaya = dict(family="monospace", fontsize=8, zorder=8, va="top", multialignment="left")
hud = ax.text(8, H - 8, "", ha="left", color="#7CFFB2",
              bbox=dict(boxstyle="round,pad=0.5", fc="#0b1320", ec="#00d4ff", lw=1.5, alpha=0.88), **gaya)
hud_tf = ax.text(W - 8, H - 8, "", ha="right", color="#ffd166",
                 bbox=dict(boxstyle="round,pad=0.5", fc="#0b1320", ec="#ffd166", lw=1.5, alpha=0.88), **gaya)
mode_txt = ax.text(8, H - 130, "", ha="left", va="top", fontsize=10, fontweight="bold",
                   color="white", zorder=8,
                   bbox=dict(boxstyle="round,pad=0.3", fc="#2a9d8f", ec="none"))
ax.text(W / 2, H - 10, "Pelari: Translasi + Rotasi + Scaling", ha="center", va="top",
        fontsize=12, fontweight="bold", color="white", zorder=8,
        bbox=dict(boxstyle="round", fc="#1f3a93", ec="none", alpha=0.85))

# Speedometer (bar)
BAR_X, BAR_Y, BAR_W, BAR_H = 190, 14, 360, 12
ax.add_patch(Rectangle((BAR_X, BAR_Y), BAR_W, BAR_H, fc="#222", ec="white", lw=1, zorder=8))
bar = Rectangle((BAR_X, BAR_Y), 1, BAR_H, fc="lime", ec="none", zorder=9)
ax.add_patch(bar)
ax.text(BAR_X - 6, BAR_Y + BAR_H / 2, "SPEED", ha="right", va="center", fontsize=8,
        fontweight="bold", color="white", zorder=9)
ax.text(BAR_X + BAR_W + 6, BAR_Y + BAR_H / 2, f"{KMH_MAKS:.0f} km/j", ha="left", va="center",
        fontsize=8, color="white", zorder=9)

# ---------- Kontrol ----------
s_kmh = Slider(fig.add_axes([0.25, 0.115, 0.50, 0.045]), "Kecepatan (km/jam)", 0, KMH_MAKS,
               valinit=KMH_AWAL, valstep=0.5, color="#2a9d8f")
btn = Button(fig.add_axes([0.82, 0.105, 0.12, 0.06]), "Reset")
fig.text(0.5, 0.03, "Keyboard:  Up / +  = lebih cepat     Down / -  = lebih lambat     R = reset",
         ha="center", fontsize=8, color="#444")

st = {"x": -lw, "fase": 0.0, "jarak": 0.0, "waktu": 0.0, "n": 0,
      "t": time.perf_counter(), "fps": 0.0}

def reset(_=None):
    s_kmh.set_val(KMH_AWAL)
    st.update(x=-lw, fase=0.0, jarak=0.0, waktu=0.0, n=0)
btn.on_clicked(reset)

def tombol(e):
    if e.key in ("up", "+", "="):   s_kmh.set_val(min(KMH_MAKS, s_kmh.val + 1))
    elif e.key in ("down", "-"):    s_kmh.set_val(max(0, s_kmh.val - 1))
    elif e.key in ("r", "R"):       reset()
fig.canvas.mpl_connect("key_press_event", tombol)

# ---------- Format keterangan ----------
def fmt_pace(kmh):
    if kmh < 0.5: return "--:--"
    dtk = 3600 / kmh
    return f"{int(dtk // 60):02d}:{int(dtk % 60):02d}"

def level(kmh):
    if kmh < 0.5:  return "DIAM",        "#6c757d"
    if kmh < 5:    return "JALAN",       "#2a9d8f"
    if kmh < 9:    return "JOGGING",     "#57cc99"
    if kmh < 14:   return "LARI",        "#f4a261"
    if kmh < 20:   return "LARI CEPAT",  "#e76f51"
    return "SPRINT!", "#d00000"

cmap = plt.get_cmap("RdYlGn_r")

# ---------- Update tiap frame ----------
def update(frame):
    if SIMPAN:                                   # GIF: akselerasi otomatis
        kmh = KMH_DEMO[0] + (KMH_DEMO[1] - KMH_DEMO[0]) * (frame / max(N_DEMO - 1, 1))
        s_kmh.set_val(kmh)
    else:
        kmh = s_kmh.val

    v_ms = kmh / 3.6                              # m/s
    v_px = v_ms * PX_PER_METER / FPS              # piksel per frame
    kec = min(kmh / 20.0, 1.0)                    # 0..1 untuk menskalakan efek

    # keadaan (kontinu, jadi tidak melompat saat kecepatan diubah)
    st["x"] += v_px
    if st["x"] > W + lw:
        st["x"] -= (W + 2 * lw)                   # muncul lagi dari kiri
    st["fase"] += 2 * np.pi * v_px / SIKLUS_PX * AYUN_CEPAT   # irama langkah mengikuti kecepatan
    st["jarak"] += v_ms / FPS
    st["waktu"] += 1 / FPS
    st["n"] += 1
    fase = st["fase"]

    # --- transformasi badan ---
    amp = AYUN_MIN + (1 - AYUN_MIN) * kec          # ayunan kaki/tangan makin besar saat cepat
    sy = 1 + SKALA_AMP * amp * np.sin(fase)
    sx = 1 - SKALA_AMP * amp * 0.6 * np.sin(fase)
    miring = -2 - 6 * kec                          # makin cepat makin condong
    theta = np.deg2rad(miring + ROTASI_AMP * amp * np.sin(fase + np.pi / 3))
    dx = st["x"]
    dy = Y_JALAN + LOMPAT_AMP * amp * abs(np.sin(fase))
    mat = {"T": T(dx, dy), "R": R(theta), "S": S(sx, sy)}
    M = np.eye(3)
    for h in URUTAN:
        M = M @ mat[h]

    # --- anggota badan ---
    kaki   = np.deg2rad(KAKI_AMP * amp * np.sin(fase))
    tangan = np.deg2rad(TANGAN_AMP * amp * np.sin(fase))
    sudut = {"kaki_kanan": kaki, "kaki_kiri": -kaki,
             "lengan_kiri": tangan, "lengan_kanan": -tangan}
    for nama, im in layer.items():
        if nama == "badan":
            Mp = M
        else:
            px, py = PIVOT[nama]
            Mp = M @ T(px, py) @ R(sudut[nama]) @ T(-px, -py)
        im.set_transform(Affine2D(Mp) + ax.transData)

    naik = dy - Y_JALAN
    bayangan.center = (dx, Y_JALAN - 4)
    bayangan.width = lw * 0.7 * (1 - 0.35 * naik / max(LOMPAT_AMP, 1e-6))

    # --- garis kecepatan di belakang pelari ---
    kuat = np.clip((kmh - 10) / 14, 0, 1)
    for i, g in enumerate(garis_cepat):
        yy = Y_JALAN + 12 + i * 15
        panjang = (20 + 70 * kuat) * (0.6 + 0.4 * ((i * 37) % 5) / 4)
        x_akhir = dx - lw * 0.35
        g.set_data([x_akhir - panjang, x_akhir], [yy, yy])
        g.set_alpha(0.6 * kuat)

    # --- HUD ---
    mnt, dtk = divmod(st["waktu"], 60)
    if SIMPAN:
        fps_txt = f"{FPS}"
    else:
        now = time.perf_counter()
        if st["n"] > 1:
            st["fps"] = 0.9 * st["fps"] + 0.1 / max(now - st["t"], 1e-6)
        st["t"] = now
        fps_txt = f"{st['fps']:.1f} (target {FPS})"
    hud.set_text(
        "== RUN STATS ==\n"
        f"Frame : {st['n']}\n"
        f"Waktu : {int(mnt):02d}:{dtk:04.1f}\n"
        f"Jarak : {st['jarak']:.1f} m\n"
        f"Speed : {kmh:.1f} km/jam\n"
        f"        {v_ms:.2f} m/s\n"
        f"PACE  : {fmt_pace(kmh)} /km\n"
        f"FPS   : {fps_txt}")
    hud_tf.set_text(
        "== TRANSFORMASI ==\n"
        f"Badan   : {'.'.join(URUTAN)}\n"
        f"S(sx,sy): ({sx:.2f},{sy:.2f})\n"
        f"R(theta): {np.rad2deg(theta):+.1f} deg\n"
        f"T(dx,dy): ({dx:.0f},{dy:.0f})\n"
        f"Kaki    : {np.rad2deg(kaki):+.0f} deg\n"
        f"Tangan  : {np.rad2deg(tangan):+.0f} deg\n"
        f"Langkah : {v_ms / PANJANG_LANGKAH_M * AYUN_CEPAT:.1f} /detik")
    nama_lv, warna = level(kmh)
    mode_txt.set_text(f" {nama_lv} ")
    mode_txt.get_bbox_patch().set_facecolor(warna)

    lebar = max(1, BAR_W * kmh / KMH_MAKS)
    bar.set_width(lebar)
    bar.set_facecolor(cmap(kmh / KMH_MAKS))
    return list(layer.values())

if SIMPAN:
    ani = animation.FuncAnimation(fig, update, frames=N_DEMO, interval=1000 / FPS, blit=False)
    ani.save(os.path.join(folder, "hasil_v3.gif"), writer="pillow", fps=FPS)
    print("Tersimpan: hasil_v3.gif")
else:
    ani = animation.FuncAnimation(fig, update, frames=count(), interval=1000 / FPS,
                                  blit=False, cache_frame_data=False)
    plt.show()