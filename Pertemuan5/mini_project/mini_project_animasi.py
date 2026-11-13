"""
MINI PROJECT - ANIMASI 2D  (versi 2: interaktif)
Grafika Komputer - Pertemuan 6

Objek bergerak:
  1. 3 orang berjalan  (sprite 16 frame)  -> Orang 1 & 2 bisa LARI lewat tombol
  2. 2 burung terbang  (sprite 9 frame)   -> burung 2 (kuning) bisa MENUKIK
  3. Pengendara motor  (roda digambar kode) -> tombol NGEBUT: wheelie, loncat, asap knalpot, "Tin tin!"
  + bayangan untuk motor dan orang

Transformasi (matriks homogen 3x3):  M = T . R . S
    T = translasi | R = rotasi | S = scaling  (sx = -1  ->  refleksi / cermin)

Kontrol (tombol di bawah layar, atau keyboard):
    Animasi + / -   (keyboard + / -)  : percepat / perlambat seluruh animasi
    Motor NGEBUT    (keyboard M)      : motor ngebut + wheelie + loncat + asap
    Orang 1 LARI    (keyboard O)      : orang 1 berlari
    Orang 2 LARI    (keyboard P)      : orang 2 berlari
    Reset           (keyboard R)      : ulang dari awal          Spasi = jeda / lanjut

Cara pakai:
    python mini_project_animasi_v2.py                 -> tampil animasi interaktif
    python mini_project_animasi_v2.py --simpan        -> simpan GIF (demo otomatis menekan tombol)
    python mini_project_animasi_v2.py --simpan mp4    -> simpan MP4 (butuh ffmpeg)
Folder aset/ dibuat oleh potong_aset.py.
"""
import os, sys, time
from itertools import count
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Ellipse, Polygon
from matplotlib.collections import LineCollection
from matplotlib.transforms import Affine2D
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb
from matplotlib.widgets import Button

# ======================================================================
#                      PENGATURAN (ubah di sini)
# ======================================================================
FPS    = 30
DURASI = 10.0                       # detik (untuk file GIF/MP4)  -> 300 frame

# ---- Orang: x0 posisi awal | kec px/detik | arah +1 kanan / -1 kiri (refleksi)
#      skala0->skala1 & y0->y1: ukuran/posisi kaki awal -> akhir (SCALING: mendekat)
#      tunggu: detik sebelum mulai | jas: warna jas 0-1 (None = asli) | bisa_lari: ada tombol lari
ORANG = [
    dict(nama="Orang 1", x0=-60, kec=100, arah=+1, skala0=0.80, skala1=0.80, y0=40, y1=40, tunggu=0.0, jas=None, bisa_lari=True),
    dict(nama="Orang 2", x0=800, kec=100, arah=-1, skala0=0.72, skala1=0.72, y0=30, y1=30, tunggu=0.0, jas=0.36, bisa_lari=True),
    dict(nama="Orang 3", x0=-60, kec=125, arah=+1, skala0=0.78, skala1=1.05, y0=46, y1=26, tunggu=1.5, jas=0.02, bisa_lari=False),
]
URUTAN_JALAN  = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17]   # siklus jalan (frame sprite)
RASIO_LANGKAH = 0.75               # panjang 1 siklus jalan = 0,75 x tinggi badan
RASIO_LARI    = 1.20               # saat lari langkahnya lebih panjang
KEC_LARI      = 2.1                # kecepatan lari = kecepatan jalan x 2,1
HENTI_DETIK   = 1.6                # lama orang berhenti & menoleh saat diklakson
JARAK_REAKSI  = 230                # orang dalam jarak ini dari motor akan berhenti & menoleh

# ---- Motor
MOTOR = dict(
    tunggu=0.8, kec=180, kali_ngebut=1.85,   # px/detik normal, pengali saat ngebut
    arah=-1,                                  # -1 ke kiri (sesuai gambar), +1 ke kanan (dicerminkan)
    y=12, lebar=150,                          # posisi tanah & lebar motor (piksel)
    wheelie=12.0,                             # derajat angkat roda depan saat ngebut
    loncat_v=250, gravitasi=700,              # kecepatan loncat & gravitasi (px/detik, px/detik^2)
    jeda_loncat=1.5,                          # jeda antar loncatan saat ngebut
    jarak_klakson=150,                        # motor mengklakson jika orang sedekat ini
)

# ---- Burung  (burung 1: merah, jalur bolak-balik | burung 2: kuning, jalur gelombang + menukik)
BURUNG1 = dict(pusat_x=370, amp_x=330, y=305, amp_y=26, skala=1.0, fps_sayap=15, miring=14)
BURUNG2 = dict(pusat_x=360, amp_x=270, fase=2.4, y=285, amp_y=16, skala=0.85, fps_sayap=17,
               waktu_tukik=(3.7, 8.3), dalam_tukik=135, lebar_tukik=0.45, warna_badan=0.12)
IDX_TUKIK = 3                                  # frame sayap terlipat dipakai saat menukik

SPEED_ANIM = [0.5, 1.0, 1.5, 2.0, 3.0]         # pilihan kecepatan animasi (tombol Animasi +/-)

# ---- Demo otomatis untuk file GIF/MP4  (detik: mulai, selesai)
DEMO = dict(motor=[(2.0, 4.8), (7.0, 9.6)], orang1=[(1.0, 3.4)], orang2=[(5.2, 7.8)])
# ======================================================================

SIMPAN = "--simpan" in sys.argv
N_FRAME = int(round(FPS * DURASI))

try:
    folder = os.path.dirname(os.path.abspath(__file__))
except NameError:
    folder = os.getcwd()
# folder = r"E:\SEMESTER 5\Grafika Komputer\Pertemuan6\MiniProject"      # <- isi manual jika perlu
ASET = os.path.join(folder, "aset")

# ---------------------------------------------------------------- aset
def info(nama):
    with open(os.path.join(ASET, nama)) as f:
        return [float(v) for v in f.read().split()]

def muat(nama):
    return plt.imread(os.path.join(ASET, nama))

def ganti_warna_jas(img, hue):
    """Ubah piksel biru (jas) ke hue lain; kulit, rambut, dasi tidak berubah."""
    if hue is None:
        return img
    out = img.copy()
    hsv = rgb_to_hsv(out[..., :3])
    biru = (hsv[..., 1] > 0.15) & (hsv[..., 0] > 0.5) & (hsv[..., 0] < 0.75)
    hsv[..., 0][biru] = hue
    out[..., :3] = hsv_to_rgb(hsv)
    return out

def ganti_warna_badan_burung(img, hue):
    """Ubah bulu merah menjadi hue lain (sayap biru tetap)."""
    out = img.copy()
    hsv = rgb_to_hsv(out[..., :3])
    merah = (hsv[..., 1] > 0.45) & ((hsv[..., 0] < 0.04) | (hsv[..., 0] > 0.96))
    hsv[..., 0][merah] = hue
    out[..., :3] = hsv_to_rgb(hsv)
    return out

latar = muat("latar.png")
H, W = latar.shape[:2]
jw, jh, jax_, _ = info("jalan_info.txt")
frame_jalan = [muat(f"jalan_{i:02d}.png") for i in URUTAN_JALAN]
frame_berdiri = muat("jalan_00.png")
bw, bh, bax, bay, _ = info("burung_info.txt")
frame_burung = [muat(f"burung_{i}.png") for i in range(9)]
badan_motor = muat("motor_badan.png")
mw, mh = info("motor_info.txt")[:2]
roda_info = []
with open(os.path.join(ASET, "motor_info.txt")) as f:
    next(f)
    for baris in f:
        roda_info.append([float(v) for v in baris.split()])

# ---------------------------------------------------------------- matriks 3x3
def S(sx, sy): return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], float)
def R(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)
def T(dx, dy): return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)

def halus(nilai, target, dt, laju):
    """Dekati target secara mulus (easing)."""
    return nilai + (target - nilai) * min(1.0, dt * laju)

# ---------------------------------------------------------------- kanvas
PANEL = 0 if SIMPAN else 62                      # ruang tombol di bawah adegan
fig = plt.figure(figsize=(W / 100, (H + PANEL) / 100), dpi=100)
ax = fig.add_axes([0, PANEL / (H + PANEL), 1, H / (H + PANEL)])
ax.imshow(latar, extent=(0, W, 0, H), zorder=0)

# ---------------------------------------------------------------- gelembung teks
class Gelembung:
    """Gelembung ucapan: kotak teks + ekor segitiga yang menunjuk ke (x, y)."""
    def __init__(self, warna="white", ukuran=9):
        self.ekor = Polygon([[0, 0], [0, 0], [0, 0]], closed=True, fc=warna, ec="black",
                            lw=1.2, zorder=209, visible=False)
        ax.add_patch(self.ekor)
        self.txt = ax.text(0, 0, "", ha="center", va="center", fontsize=ukuran, fontweight="bold",
                           zorder=210, visible=False,
                           bbox=dict(boxstyle="round,pad=0.35", fc=warna, ec="black", lw=1.2))
    def tampil(self, teks, x, y):
        x = float(np.clip(x, 40, W - 40))
        self.txt.set_text(teks); self.txt.set_position((x, y + 20))
        self.ekor.set_xy([[x - 5, y + 11], [x + 5, y + 11], [x, y]])
        self.txt.set_visible(True); self.ekor.set_visible(True)
    def sembunyi(self):
        self.txt.set_visible(False); self.ekor.set_visible(False)

# ---------------------------------------------------------------- ORANG
class Orang:
    def __init__(self, cfg):
        self.c = cfg
        self.frames = [ganti_warna_jas(f, cfg["jas"]) for f in frame_jalan]
        self.berdiri = ganti_warna_jas(frame_berdiri, cfg["jas"])
        self.im = ax.imshow(self.frames[0], extent=(-jax_, jw - jax_, 0, jh), zorder=10)
        self.bayangan = Ellipse((0, 0), 30, 7, color="black", alpha=0.28, zorder=9.9)
        ax.add_patch(self.bayangan)
        self.bubble = Gelembung(ukuran=8)
        self.reset()

    def reset(self):
        c = self.c
        self.x, self.v, self.phase = c["x0"], 0.0, 0.0
        self.lari, self.henti, self.tunggu = 0.0, 0.0, c["tunggu"]
        self.hadap = c["arah"]
        self.s, self.y = c["skala0"], c["y0"]
        self.status, self.teks = "JALAN", "Eh!"

    def progres(self):
        x_akhir = -60 if self.c["arah"] < 0 else W + 60
        return float(np.clip((self.x - self.c["x0"]) / (x_akhir - self.c["x0"]), 0, 1))

    def berhenti_menoleh(self, teks):
        self.henti, self.teks = HENTI_DETIK, teks

    def maju(self, dt, ingin_lari, motor):
        c = self.c
        if self.tunggu > 0:                                    # belum mulai
            self.tunggu -= dt
            self.im.set_visible(False); self.bayangan.set_visible(False); self.bubble.sembunyi()
            return
        self.im.set_visible(True); self.bayangan.set_visible(True)

        self.lari = halus(self.lari, 1.0 if ingin_lari else 0.0, dt, 3)
        if self.henti > 0:
            self.henti -= dt
            target = 0.0
            self.hadap = 1 if motor.x > self.x else -1         # MENOLEH ke arah motor (refleksi)
        else:
            target = c["kec"] * (1 + (KEC_LARI - 1) * self.lari)
            self.hadap = c["arah"]
        self.v = halus(self.v, target, dt, 4)
        self.x += c["arah"] * self.v * dt                      # TRANSLASI

        p = self.progres()
        self.s = c["skala0"] + (c["skala1"] - c["skala0"]) * p  # SCALING (mendekat / menjauh)
        self.y = c["y0"] + (c["y1"] - c["y0"]) * p
        rasio = RASIO_LANGKAH + (RASIO_LARI - RASIO_LANGKAH) * self.lari
        self.phase += self.v * dt / (rasio * jh * self.s)      # fase langkah ~ jarak tempuh
        if p >= 1.0:                                           # keluar layar -> muncul lagi
            self.x = c["x0"]

        diam = self.v < 6 and self.henti > 0
        idx = int((self.phase % 1.0) * len(self.frames))
        self.im.set_data(self.berdiri if diam else self.frames[idx])
        bob = (1.0 + 3.0 * self.lari) * abs(np.sin(2 * np.pi * 2 * self.phase)) * self.s
        goyang = np.deg2rad(1.2 * np.sin(2 * np.pi * 2 * self.phase))
        condong = -self.hadap * np.deg2rad(9.0 * self.lari)    # ROTASI: badan condong saat lari
        M = T(self.x, self.y + bob) @ R(goyang + condong) @ S(self.hadap * self.s, self.s)
        self.im.set_transform(Affine2D(M) + ax.transData)
        self.im.set_zorder(20 - 0.2 * self.y)

        # bayangan di kaki
        self.bayangan.center = (self.x, self.y - 1)
        self.bayangan.width = 34 * self.s * (1 - 0.06 * bob)
        self.bayangan.height = 7.5 * self.s
        self.bayangan.set_zorder(19.9 - 0.2 * self.y)

        if self.henti > 0:
            self.bubble.tampil(self.teks, self.x, self.y + jh * self.s + 4)
        else:
            self.bubble.sembunyi()
        if self.henti > 0:
            self.status = "BERHENTI"
        else:
            self.status = "LARI" if self.lari > 0.5 else "JALAN"

# ---------------------------------------------------------------- ASAP KNALPOT
class Asap:
    """Partikel asap: lingkaran abu-abu yang membesar dan memudar."""
    def __init__(self):
        self.p = []                                            # [x, y, vx, vy, umur, hidup, r0, gelap]
        self.rng = np.random.default_rng(7)
        self.sc = ax.scatter([], [], s=[], zorder=37, edgecolors="none")
        self.tick = 0

    def reset(self):
        self.p, self.tick = [], 0

    def pancar(self, x, y, belakang, ngebut):
        self.tick += 1
        if ngebut:
            jumlah = 2
        else:
            jumlah = 1 if self.tick % 6 == 0 else 0
        for _ in range(jumlah):
            r = self.rng
            self.p.append([x, y, belakang * (35 + 45 * ngebut) * r.uniform(0.7, 1.3), r.uniform(18, 45),
                           0.0, 0.9 + 0.5 * ngebut, 3.0 + 2.5 * ngebut, 0.2 if ngebut else 0.55])

    def maju(self, dt):
        for q in self.p:
            q[4] += dt; q[0] += q[2] * dt; q[1] += q[3] * dt; q[3] *= (1 - 0.8 * dt)
        self.p = [q for q in self.p if q[4] < q[5]][-150:]
        if not self.p:
            self.sc.set_offsets(np.empty((0, 2))); return
        pos = np.array([[q[0], q[1]] for q in self.p])
        umur = np.array([q[4] / q[5] for q in self.p])
        r = np.array([q[6] for q in self.p]) * (1 + 3.2 * umur)           # makin tua makin besar
        g = np.array([q[7] for q in self.p]) + 0.4 * umur                  # makin tua makin terang
        warna = np.c_[g, g, g, 0.65 * (1 - umur)]
        self.sc.set_offsets(pos)
        self.sc.set_sizes((1.44 * r) ** 2)
        self.sc.set_facecolors(warna)

# ---------------------------------------------------------------- MOTOR
kmot = MOTOR["lebar"] / mw                       # skala gambar asli -> layar
ox = np.mean([r[0] for r in roda_info])          # titik asal lokal: tengah antara dua roda, di tanah
oy = roda_info[0][1] + roda_info[0][2]
r_roda = roda_info[0][2] * kmot
pusat_roda = [((cx - ox) * kmot, (oy - cy) * kmot) for cx, cy, _ in roda_info]
roda_belakang = max(pusat_roda, key=lambda p: p[0])
knalpot = ((701 - ox) * kmot, (oy - 545) * kmot)  # posisi knalpot (kanan-belakang) di koordinat lokal

class Motor:
    def __init__(self):
        self.bayangan = Ellipse((0, 0), 100, 11, color="black", alpha=0.30, zorder=30)
        ax.add_patch(self.bayangan)
        self.badan = ax.imshow(badan_motor, zorder=40,
                               extent=((0 - ox) * kmot, (mw - ox) * kmot, (oy - mh) * kmot, oy * kmot))
        self.roda = [self.buat_roda(39) for _ in pusat_roda]
        self.garis = [ax.plot([], [], color="white", lw=2, alpha=0, zorder=38, solid_capstyle="round")[0]
                      for _ in range(5)]
        self.asap = Asap()
        self.bubble = Gelembung(ukuran=10)
        self.reset()

    def buat_roda(self, z):
        r = r_roda
        sudut = np.deg2rad(np.arange(6) * 60)
        seg = [[(0, 0), (0.72 * r * np.cos(a), 0.72 * r * np.sin(a))] for a in sudut]
        spoke = LineCollection(seg, colors=["#d62828"] + ["#7b8794"] * 5, linewidths=2.2,
                               capstyle="round", zorder=z + 0.3)
        kabur = Circle((0, 0), r * 0.74, fc="#c9ced3", ec="none", alpha=0.0, zorder=z + 0.25)   # efek blur
        tanda = Circle((r * 0.56, 0), r * 0.06, fc="#ff9f1c", ec="none", zorder=z + 0.35)
        bagian = [Circle((0, 0), r, fc="#161616", ec="none", zorder=z),
                  Circle((0, 0), r * 0.86, fc="#2c2c2c", ec="none", zorder=z + 0.1),
                  Circle((0, 0), r * 0.74, fc="#e6e9ec", ec="#8f979e", lw=1.2, zorder=z + 0.2),
                  kabur, spoke,
                  Circle((0, 0), r * 0.22, fc="#9aa1a6", ec="#4a4f55", lw=1, zorder=z + 0.4),
                  Circle((0, 0), r * 0.09, fc="#333333", ec="none", zorder=z + 0.5), tanda]
        for b in bagian:
            ax.add_collection(b) if isinstance(b, LineCollection) else ax.add_patch(b)
        self.kabur_spoke = (kabur, spoke, tanda)
        return bagian

    def reset(self):
        m = MOTOR
        self.x = (W + 0.6 * m["lebar"]) if m["arah"] < 0 else -0.6 * m["lebar"]
        self.v, self.tunggu = 0.0, m["tunggu"]
        self.theta, self.ngebut_amt = 0.0, 0.0
        self.h, self.vh, self.jeda = 0.0, 0.0, 0.0           # tinggi loncat, kecepatan vertikal, jeda
        self.klakson_cd, self.bubble_t = 0.0, 0.0
        self.pitch, self.deg_per_frame = 0.0, 0.0
        self.asap.reset()
        self.bubble.sembunyi()

    def maju(self, dt, ngebut, orang):
        m = MOTOR
        if self.tunggu > 0:
            self.tunggu -= dt
        else:
            target = m["kec"] * (m["kali_ngebut"] if ngebut else 1.0)
            self.v = halus(self.v, target, dt, 2.5)
            self.x += m["arah"] * self.v * dt                 # TRANSLASI
            self.theta += self.v * dt / r_roda                # ROTASI roda: sudut = jarak / jari-jari
        self.deg_per_frame = np.rad2deg(self.v * dt / r_roda)
        self.ngebut_amt = halus(self.ngebut_amt, 1.0 if ngebut else 0.0, dt, 4)

        # --- loncat (jumping) saat ngebut ---
        self.jeda -= dt
        if ngebut and self.h <= 0 and self.jeda <= 0 and self.v > 0.6 * m["kec"]:
            self.vh, self.jeda = m["loncat_v"], m["jeda_loncat"]
            self.h = 0.01
        if self.h > 0:
            self.vh -= m["gravitasi"] * dt
            self.h += self.vh * dt
            if self.h <= 0:
                self.h, self.vh = 0.0, 0.0
        # --- kemiringan (ROTASI badan terhadap roda belakang): wheelie + saat di udara ---
        wheelie = -np.deg2rad(m["wheelie"]) * self.ngebut_amt
        udara = -np.deg2rad(12) * np.clip(self.vh / m["loncat_v"], -1, 1) if self.h > 0 else 0.0
        self.pitch = halus(self.pitch, wheelie + udara, dt, 12)

        # --- matriks motor: M = T . S . T(pivot) . R(pitch) . T(-pivot)   (pivot = roda belakang di tanah)
        getar = 0.9 * np.sin(2 * np.pi * 3.3 * time_sim[0]) if self.v > 1 and self.h <= 0 else 0.0
        sx_m = -1.0 if m["arah"] > 0 else 1.0                 # gambar asli menghadap kiri
        pv = (roda_belakang[0], 0.0)
        self.M = T(self.x, m["y"] + self.h + getar) @ S(sx_m, 1.0) @ T(*pv) @ R(self.pitch) @ T(-pv[0], -pv[1])
        self.badan.set_transform(Affine2D(self.M) + ax.transData)

        # --- roda: efek blur jika putaran per frame terlalu cepat (hindari efek "roda mundur") ---
        blur = float(np.clip((self.deg_per_frame - 12) / 14, 0, 1))
        for (px, py), bagian in zip(pusat_roda, self.roda):
            tf = Affine2D(self.M @ T(px, py) @ R(self.theta)) + ax.transData
            for a in bagian:
                a.set_transform(tf)
            kabur, spoke, tanda = bagian[3], bagian[4], bagian[7]
            kabur.set_alpha(0.6 * blur); spoke.set_alpha(1 - 0.8 * blur); tanda.set_alpha(1 - 0.9 * blur)

        # --- bayangan tetap di tanah, mengecil saat motor di udara ---
        self.bayangan.center = (self.x + 2, m["y"] - 3)
        self.bayangan.width = m["lebar"] * 0.95 * (1 - 0.45 * min(self.h / 50, 1))
        self.bayangan.set_alpha(0.30 * (1 - 0.5 * min(self.h / 50, 1)))

        # --- garis kecepatan ---
        aktif = (self.v > 5) and (-150 < self.x < W + 150)
        kuat = np.clip((self.v - 120) / 250, 0, 1)
        for i, g in enumerate(self.garis):
            yy = m["y"] + 20 + i * 24 + self.h
            pj = (25 + 10 * ((i * 3) % 4)) * (1 + 1.2 * self.ngebut_amt)
            xb = self.x - m["arah"] * (m["lebar"] * 0.52)
            g.set_data([xb, xb - m["arah"] * pj], [yy, yy])
            g.set_alpha(0.55 * kuat if aktif else 0.0)

        # --- asap knalpot (posisi knalpot dihitung dengan matriks motor) ---
        if self.v > 5 and -100 < self.x < W + 100:
            ex, ey, _ = self.M @ np.array([knalpot[0], knalpot[1], 1.0])
            self.asap.pancar(ex, ey, -m["arah"], self.ngebut_amt > 0.5)
        self.asap.maju(dt)

        # --- klakson "Tin tin!" saat ngebut dekat orang ---
        self.klakson_cd -= dt
        if ngebut and self.ngebut_amt > 0.5 and self.klakson_cd <= 0:
            dekat = [o for o in orang if o.tunggu <= 0 and o.henti <= 0 and
                     0 < (self.x - o.x) * -m["arah"] < m["jarak_klakson"]]
            if dekat:
                self.klakson_cd, self.bubble_t = 1.2, 1.3
                for o in orang:
                    if o.tunggu <= 0 and abs(o.x - self.x) < JARAK_REAKSI:
                        o.berhenti_menoleh(["Eh!", "Wah!", "Hei!"][orang.index(o) % 3])
        if self.bubble_t > 0:
            self.bubble_t -= dt
            self.bubble.tampil("Tin tin!", self.x - m["arah"] * 5, m["y"] + self.h + mh * kmot + 6)
        else:
            self.bubble.sembunyi()

        # --- keluar layar -> muncul lagi dari sisi lain ---
        batas = -0.6 * m["lebar"] - 30 if m["arah"] < 0 else W + 0.6 * m["lebar"] + 30
        if (m["arah"] < 0 and self.x < batas) or (m["arah"] > 0 and self.x > batas):
            self.x = (W + 0.6 * m["lebar"]) if m["arah"] < 0 else -0.6 * m["lebar"]
            self.tunggu = 1.0

# ---------------------------------------------------------------- BURUNG
class Burung:
    def __init__(self, frames, skala, fps_sayap, z, lintasan, tukik=False, geser_frame=0):
        self.frames, self.skala, self.fps, self.lintasan = frames, skala, fps_sayap, lintasan
        self.tukik, self.geser = tukik, geser_frame
        self.im = ax.imshow(frames[0], extent=(-bax, bw - bax, bay - bh, bay), zorder=z)
        self.sx = 1.0

    def maju(self, t):
        x, y, g, miring_lembut = self.lintasan(t)
        h = 1e-3
        x2, y2, _, _ = self.lintasan(t + h); x1, y1, _, _ = self.lintasan(t - h)
        vx, vy = (x2 - x1) / (2 * h), (y2 - y1) / (2 * h)
        sx = float(np.clip(vx / 70.0, -1, 1))                     # REFLEKSI halus saat berbalik arah
        sx = np.sign(sx or 1.0) * max(abs(sx), 0.18)
        if miring_lembut is None:                                  # burung 2: miring mengikuti arah lintasan
            theta = np.clip(np.arctan2(vy, abs(vx) + 80), -0.95, 0.95) * np.sign(sx)
        else:                                                      # burung 1: miring lembut
            theta = miring_lembut * sx
        idx = int(t * self.fps + self.geser) % len(self.frames)
        if self.tukik and g > 0.35:
            idx = IDX_TUKIK                                       # sayap terlipat saat menukik
        self.im.set_data(self.frames[idx])
        M = T(x, y) @ R(theta) @ S(self.skala * sx, self.skala)
        self.im.set_transform(Affine2D(M) + ax.transData)
        self.sx, self.idx, self.g = sx, idx, g

T_B = N_FRAME / FPS                                              # periode jalur burung = durasi video
w_b = 2 * np.pi / T_B

def lintasan1(t):
    b = BURUNG1
    x = b["pusat_x"] - b["amp_x"] * np.cos(w_b * t)
    y = b["y"] + b["amp_y"] * np.sin(2 * w_b * t)
    return x, y, 0.0, np.deg2rad(b["miring"]) * np.cos(2 * w_b * t)

def lintasan2(t):
    b = BURUNG2
    x = b["pusat_x"] + b["amp_x"] * np.cos(w_b * t + b["fase"])
    y = b["y"] + b["amp_y"] * np.sin(3 * w_b * t + 1.0)
    g = 0.0
    for td in b["waktu_tukik"]:                                   # MENUKIK: lembah gaussian periodik
        d = ((t - td + T_B / 2) % T_B) - T_B / 2
        g = max(g, float(np.exp(-(d / b["lebar_tukik"]) ** 2)))
    return x, y - b["dalam_tukik"] * g, g, None

burung_a = [ganti_warna_badan_burung(f, BURUNG2["warna_badan"]) for f in frame_burung]
burung1 = Burung(frame_burung, BURUNG1["skala"], BURUNG1["fps_sayap"], 90, lintasan1)
burung2 = Burung(burung_a, BURUNG2["skala"], BURUNG2["fps_sayap"], 91, lintasan2, tukik=True, geser_frame=3)

# ---------------------------------------------------------------- objek adegan
orang = [Orang(c) for c in ORANG]
motor = Motor()
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

# ---------------------------------------------------------------- HUD
gaya = dict(family="monospace", fontsize=8, zorder=200, va="top", multialignment="left")
hud_kiri = ax.text(8, H - 8, "", ha="left", color="#7CFFB2",
                   bbox=dict(boxstyle="round,pad=0.5", fc="#0b1320", ec="#00d4ff", lw=1.5, alpha=0.88), **gaya)
hud_kanan = ax.text(W - 8, H - 8, "", ha="right", color="#ffd166",
                    bbox=dict(boxstyle="round,pad=0.5", fc="#0b1320", ec="#ffd166", lw=1.5, alpha=0.88), **gaya)
ax.text(W / 2, H - 10, "Mini Project: Animasi 2D", ha="center", va="top", fontsize=11,
        fontweight="bold", color="white", zorder=200,
        bbox=dict(boxstyle="round", fc="#1f3a93", ec="none", alpha=0.88))

# ---------------------------------------------------------------- kontrol
ctl = dict(kec_idx=1, motor=False, orang=[False, False, False])   # orang[0], orang[1] bisa ditekan
time_sim = [0.0]
waktu = dict(t=time.perf_counter(), fps=0.0, n=0)
tombol = {}

def kec_anim():
    return SPEED_ANIM[ctl["kec_idx"]]

def segarkan_tombol():
    if SIMPAN:
        return
    def warna(b, aktif, label):
        b.label.set_text(label)
        b.color = "#ff8a80" if aktif else "#e0e0e0"
        b.hovercolor = "#ff5252" if aktif else "#c8e6c9"
        b.ax.set_facecolor(b.color)
    warna(tombol["motor"], ctl["motor"], "Motor: NGEBUT!" if ctl["motor"] else "Motor NGEBUT")
    warna(tombol["o1"], ctl["orang"][0], "Orang 1: LARI!" if ctl["orang"][0] else "Orang 1 LARI")
    warna(tombol["o2"], ctl["orang"][1], "Orang 2: LARI!" if ctl["orang"][1] else "Orang 2 LARI")
    tombol["info"].set_text(f"Kecepatan animasi: x{kec_anim():.1f}")
    fig.canvas.draw_idle()

def ubah_kec(arah):
    ctl["kec_idx"] = int(np.clip(ctl["kec_idx"] + arah, 0, len(SPEED_ANIM) - 1)); segarkan_tombol()
def toggle(kunci, i=None):
    if i is None:
        ctl[kunci] = not ctl[kunci]
    else:
        ctl[kunci][i] = not ctl[kunci][i]
    segarkan_tombol()
def reset(_=None):
    time_sim[0] = 0.0; waktu["n"] = 0
    for o in orang: o.reset()
    motor.reset()
    ctl.update(kec_idx=1, motor=False, orang=[False, False, False]); segarkan_tombol()

if not SIMPAN:
    lebar_b, jarak, y_b, tinggi_b = 0.15, 0.0165, 8 / (H + PANEL), 30 / (H + PANEL)
    def buat(i, label, fungsi):
        b = Button(fig.add_axes([0.01 + i * (lebar_b + jarak), 24 / (H + PANEL), lebar_b, tinggi_b]), label)
        b.label.set_fontsize(8); b.on_clicked(fungsi); return b
    tombol["lambat"] = buat(0, "Animasi  -", lambda e: ubah_kec(-1))
    tombol["cepat"] = buat(1, "Animasi  +", lambda e: ubah_kec(+1))
    tombol["motor"] = buat(2, "Motor NGEBUT", lambda e: toggle("motor"))
    tombol["o1"] = buat(3, "Orang 1 LARI", lambda e: toggle("orang", 0))
    tombol["o2"] = buat(4, "Orang 2 LARI", lambda e: toggle("orang", 1))
    tombol["reset"] = buat(5, "Reset", reset)
    tombol["info"] = fig.text(0.5, 15 / (H + PANEL), "", ha="center", fontsize=8, color="#333")
    fig.text(0.5, 0.006, "Keyboard: +/- animasi | M motor | O orang 1 | P orang 2 | R reset | Spasi jeda",
             ha="center", fontsize=7, color="#666")
    segarkan_tombol()

def terapkan_demo(t):
    """Mode simpan: tekan tombol otomatis sesuai jadwal DEMO."""
    di = lambda daftar: any(a <= t < b for a, b in daftar)
    ctl["motor"] = di(DEMO["motor"])
    ctl["orang"][0] = di(DEMO["orang1"])
    ctl["orang"][1] = di(DEMO["orang2"])

# ---------------------------------------------------------------- update tiap frame
def update(frame):
    if SIMPAN:
        terapkan_demo(frame / FPS)
        dt = 1.0 / FPS
    else:
        dt = kec_anim() / FPS                      # tombol Animasi +/- mengubah laju waktu simulasi
    time_sim[0] += dt
    t = time_sim[0]
    waktu["n"] += 1

    for i, o in enumerate(orang):
        o.maju(dt, ctl["orang"][i] if i < 2 else False, motor)
    motor.maju(dt, ctl["motor"], orang)
    burung1.maju(t); burung2.maju(t)

    if SIMPAN:
        fps_txt = f"{FPS}"
    else:
        now = time.perf_counter()
        if waktu["n"] > 1:
            waktu["fps"] = 0.9 * waktu["fps"] + 0.1 / max(now - waktu["t"], 1e-6)
        waktu["t"] = now
        fps_txt = f"{FPS} (aktual {waktu['fps']:.1f})"
    status_motor = "NGEBUT" if motor.ngebut_amt > 0.5 else "NORMAL"
    hud_kiri.set_text(
        "== MINI PROJECT 2D ==\n"
        f"Frame  : {waktu['n']}\n"
        f"Waktu  : {t:5.1f} s\n"
        f"Animasi: x{kec_anim() if not SIMPAN else 1.0:.1f}   FPS {fps_txt}\n"
        f"Motor  : {status_motor} {motor.v:3.0f} px/s\n"
        f"Orang 1: {orang[0].status}\n"
        f"Orang 2: {orang[1].status}\n"
        f"Burung2: {'MENUKIK' if burung2.g > 0.35 else 'TERBANG'}")
    hud_kanan.set_text(
        "== TRANSFORMASI ==\n"
        "Translasi : orang, burung, motor\n"
        f"Rotasi    : roda {np.rad2deg(motor.theta):7.0f} deg\n"
        f"            motor {np.rad2deg(motor.pitch):+5.1f} deg\n"
        f"Scaling   : orang 3 = {orang[2].s:.2f}x\n"
        f"Refleksi  : burung1 sx = {burung1.sx:+.2f}\n"
        f"            orang menoleh/balik arah")
    return []

# ---------------------------------------------------------------- jalankan
if SIMPAN:
    ani = animation.FuncAnimation(fig, update, frames=N_FRAME, interval=1000 / FPS, blit=False, repeat=False)
    if "mp4" in sys.argv:
        out = os.path.join(folder, "hasil_mini_project_v2.mp4")
        ani.save(out, writer=animation.FFMpegWriter(fps=FPS, bitrate=4500))
    else:
        out = os.path.join(folder, "hasil_mini_project_v2.gif")
        ani.save(out, writer="pillow", fps=FPS)
    print("Tersimpan:", out)
else:
    ani = animation.FuncAnimation(fig, update, frames=count(), interval=1000 / FPS,
                                  blit=False, cache_frame_data=False)
    jeda = {"on": False}
    def tombol_keyboard(e):
        k = (e.key or "").lower()
        if k == " ":
            (ani.event_source.start if jeda["on"] else ani.event_source.stop)(); jeda["on"] = not jeda["on"]
        elif k in ("+", "="): ubah_kec(+1)
        elif k in ("-", "_"): ubah_kec(-1)
        elif k == "m": toggle("motor")
        elif k == "o": toggle("orang", 0)
        elif k == "p": toggle("orang", 1)
        elif k == "r": reset()
    fig.canvas.mpl_connect("key_press_event", tombol_keyboard)
    plt.show()