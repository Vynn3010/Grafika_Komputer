import matplotlib.pyplot as plt

plt.figure(figsize=(8, 6))

def kotak(x, y, w, h):
    """Mengembalikan 4 titik persegi panjang dari pojok kiri bawah."""
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

def isi(titik, warna, tepi='black'):
    x = [p[0] for p in titik] + [titik[0][0]]
    y = [p[1] for p in titik] + [titik[0][1]]
    plt.fill(x, y, color=warna)
    plt.plot(x, y, color=tepi, linewidth=2)

# Cerobong (digambar dulu supaya tertutup atap)
isi(kotak(6.6, 4.5, 0.8, 2.0), 'darkred')

# Badan rumah (4 sudut)
isi(kotak(2, 0, 6, 4), 'white')

# Atap (3 titik)
isi([(1.8, 3.8), (5, 7), (8.2, 3.8)], 'darkred')

# Pintu
isi(kotak(4.5, 0, 1.1, 2.4), 'darkred')
plt.scatter(4.8, 0.9, color='yellow', s=40, zorder=5)  # gagang pintu

# Jendela (dengan palang tengah)
def jendela(x, y, w=1.0, h=1.0):
    isi(kotak(x, y, w, h), 'yellow')
    plt.plot([x + w/2, x + w/2], [y, y + h], color='black', linewidth=1.5)
    plt.plot([x, x + w], [y + h/2, y + h/2], color='black', linewidth=1.5)

jendela(2.8, 1.4)   # kiri
jendela(6.4, 1.4)   # kanan
jendela(4.5, 4.2)   # atas (di loteng)

# Tampilan
plt.xlim(0, 10)
plt.ylim(0, 8)
plt.xticks(range(0, 11, 1))
plt.yticks(range(0, 9, 1))
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Rumah dari Koordinat')
plt.grid(True, linestyle='--', alpha=0.4)
plt.show()