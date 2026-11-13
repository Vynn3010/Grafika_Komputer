"""
potong_aset.py - memotong gambar sprite menjadi frame-frame PNG transparan.

Input  (folder asli/) : latar.png, orang_jalan.png, burung.png, motor.png
Output (folder aset/) : latar.png
                        jalan_00..jalan_18.png   (19 frame orang berjalan)
                        burung_0..burung_8.png   (9 frame burung terbang)
                        motor_badan.png          (motor + pengendara TANPA roda)
Roda motor digambar lewat kode di program utama, sehingga bisa diputar.
Butuh: pip install pillow numpy scipy
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

folder = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ASLI = os.path.join(folder, "asli")
ASET = os.path.join(folder, "aset")
os.makedirs(ASET, exist_ok=True)

def buka(nama):
    return np.array(Image.open(os.path.join(ASLI, nama)).convert("RGB"))

def simpan(arr_rgb, alpha, nama):
    a = np.dstack([arr_rgb, np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    Image.fromarray(a, "RGBA").save(os.path.join(ASET, nama))

def alpha_halus(mask, sigma=0.7):
    a = ndi.gaussian_filter(mask.astype(float), sigma)
    return np.clip((a - 0.5) * 2 + 0.5, 0, 1)

def bersihkan(rgb, mask):
    """Ganti warna piksel tepi (yang tercampur putih) dengan warna piksel terdekat di dalam objek."""
    dalam = ndi.binary_erosion(mask, iterations=1)
    if not dalam.any():
        return rgb
    _, (iy, ix) = ndi.distance_transform_edt(~dalam, return_indices=True)
    hasil = rgb.copy()
    tepi = mask & ~dalam
    hasil[tepi] = rgb[iy[tepi], ix[tepi]]
    return hasil

# ------------------------------------------------------------------ latar
Image.open(os.path.join(ASLI, "latar.png")).convert("RGB").save(os.path.join(ASET, "latar.png"))

# ------------------------------------------------------------------ orang berjalan
sheet = buka("orang_jalan.png")
fg = sheet.min(2) < 232
lab, n = ndi.label(ndi.binary_closing(fg, iterations=1))
kotak = []
for i, sl in enumerate(ndi.find_objects(lab)):
    if (lab[sl] == i + 1).sum() < 150:
        continue
    kotak.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop, i + 1))
kotak.sort(key=lambda r: (r[0] // 140, r[2]))          # baris atas dulu, kiri -> kanan

frames = []
for (y0, y1, x0, x1, idl) in kotak:
    m = ndi.binary_fill_holes(lab[y0:y1, x0:x1] == idl)
    rgb = sheet[y0:y1, x0:x1]
    kepala = m[:32]                                    # 32 baris teratas = kepala
    ys, xs = np.nonzero(kepala)
    frames.append((rgb, m, xs.mean()))                 # titik sejajar = pusat kepala
kiri = max(c for _, _, c in frames)
kanan = max(m.shape[1] - c for _, m, c in frames)
Wc, Hc = int(np.ceil(kiri + kanan)) + 4, max(m.shape[0] for _, m, _ in frames)
for i, (rgb, m, c) in enumerate(frames):
    kanvas_rgb = np.full((Hc, Wc, 3), 255, np.uint8)
    kanvas_m = np.zeros((Hc, Wc), bool)
    ox = int(round(kiri - c)) + 2
    oy = Hc - m.shape[0]                               # sejajarkan telapak kaki di bawah
    kanvas_rgb[oy:, ox:ox + m.shape[1]] = rgb
    kanvas_m[oy:, ox:ox + m.shape[1]] = m
    simpan(bersihkan(kanvas_rgb, kanvas_m), alpha_halus(kanvas_m), f"jalan_{i:02d}.png")
with open(os.path.join(ASET, "jalan_info.txt"), "w") as f:      # lebar, tinggi, x titik acuan (pusat kepala)
    f.write(f"{Wc} {Hc} {kiri + 2:.2f} {len(frames)}\n")
print("orang berjalan :", len(frames), "frame, ukuran", Wc, "x", Hc)

# ------------------------------------------------------------------ burung terbang
sheet = buka("burung.png")
fg = sheet.min(2) < 235
fg[262:, :] = False                                    # buang watermark
lab, n = ndi.label(ndi.binary_closing(fg, iterations=1))
kotak = []
for i, sl in enumerate(ndi.find_objects(lab)):
    m = lab[sl] == i + 1
    if m.sum() < 400:
        continue
    y0, x0 = sl[0].start, sl[1].start
    full = np.zeros(fg.shape, bool); full[sl] = m
    yc = (sl[0].start + sl[0].stop) / 2
    if m.shape[1] > 120:                               # dua burung menempel -> pisah di x = 89
        a, b = full.copy(), full.copy()
        a[:, 89:] = False; b[:, :89] = False
        kotak += [(yc, a), (yc, b)]
    else:
        kotak.append((yc, full))
kotak.sort(key=lambda t: (int(t[0] // 80), np.nonzero(t[1])[1].min()))
parts = []
for yc, full in kotak:
    full = ndi.binary_fill_holes(full)
    ys, xs = np.nonzero(full)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb = sheet[y0:y1, x0:x1]; m = full[y0:y1, x0:x1]
    kuning = (rgb[..., 0] > 215) & (rgb[..., 1] > 165) & (rgb[..., 2] < 120) & m
    yy, xx = np.nonzero(kuning)
    sel = xx >= xx.max() - 8                           # paruh = kuning paling kanan
    parts.append((rgb, m, xx[sel].mean(), yy[sel].mean()))
L = max(p[2] for p in parts); R = max(p[1].shape[1] - p[2] for p in parts)
A = max(p[3] for p in parts); B = max(p[1].shape[0] - p[3] for p in parts)
Wc, Hc = int(np.ceil(L + R)) + 4, int(np.ceil(A + B)) + 4
for i, (rgb, m, bx, by) in enumerate(parts):
    kr = np.full((Hc, Wc, 3), 255, np.uint8); km = np.zeros((Hc, Wc), bool)
    ox, oy = int(round(L - bx)) + 2, int(round(A - by)) + 2
    kr[oy:oy + m.shape[0], ox:ox + m.shape[1]] = rgb
    km[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
    simpan(bersihkan(kr, km), alpha_halus(km), f"burung_{i}.png")
with open(os.path.join(ASET, "burung_info.txt"), "w") as f:     # lebar, tinggi, x & y titik acuan (paruh)
    f.write(f"{Wc} {Hc} {L + 2:.2f} {A + 2:.2f} {len(parts)}\n")
print("burung         :", len(parts), "frame, ukuran", Wc, "x", Hc, "(titik sejajar = paruh)")

# ------------------------------------------------------------------ motor (tanpa roda)
img = buka("motor.png")
H, W = img.shape[:2]
putih = img.min(2) >= 242
lab, n = ndi.label(putih)
tepi = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
latar_mask = np.isin(lab, list(tepi))
# celah putih tertutup yang besar (antara tiang depan & kaki, antara betis & bodi) juga bagian latar
luas = ndi.sum(putih, lab, range(1, n + 1))
for i, ar in enumerate(luas, 1):
    if i not in tepi and ar > 3000:
        latar_mask |= (lab == i)
fgm = ~latar_mask
# buang roda: lingkaran roda & warna abu/hitam (saturasi rendah); bodi merah/oranye/biru tetap
RODA = [(97, 643, 88), (611, 645, 88)]                 # (pusat x, pusat y, radius ban) pada gambar asli
hsv = np.array(Image.fromarray(img).convert("HSV")).astype(float)
sat = hsv[..., 1] / 255
yy, xx = np.mgrid[:H, :W]
roda_mask = np.zeros((H, W), bool)
for cx, cy, r in RODA:
    roda_mask |= ((xx - cx) ** 2 + (yy - cy) ** 2 <= (r + 3) ** 2)
buang = roda_mask & (sat < 0.40)
badan = fgm & ~buang
lab2, n2 = ndi.label(badan)
besar = np.argmax(ndi.sum(badan, lab2, range(1, n2 + 1))) + 1
badan = lab2 == besar                                  # buang serpihan lepas
ys, xs = np.nonzero(badan)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
simpan(bersihkan(img[y0:y1, x0:x1], badan[y0:y1, x0:x1]), alpha_halus(badan[y0:y1, x0:x1], 0.6), "motor_badan.png")
print("motor          : crop (x0,y0) =", (x0, y0), "ukuran", x1 - x0, "x", y1 - y0)
with open(os.path.join(ASET, "motor_info.txt"), "w") as f:     # koordinat roda relatif terhadap crop
    f.write(f"{x1 - x0} {y1 - y0}\n")
    for cx, cy, r in RODA:
        f.write(f"{cx - x0} {cy - y0} {r}\n")
print("selesai ->", ASET)
