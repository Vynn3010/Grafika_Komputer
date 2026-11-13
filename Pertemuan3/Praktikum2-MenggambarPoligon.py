import matplotlib.pyplot as plt

# Titik-titik poligon
segitiga  = [(1, 1), (4, 1), (2.5, 4)]
persegi   = [(6, 1), (8, 1), (8, 3), (6, 3)]
segi_lima = [(1, 5), (2, 7), (4, 7), (5, 5), (3, 4)]

# Pisahkan x dan y
def get_xy(titik):
    x = [p[0] for p in titik]
    y = [p[1] for p in titik]
    return x, y

plt.figure(figsize=(8, 6))

# Gambar poligon: isian + garis tepi (titik pertama diulang agar tertutup)
def gambar(titik, warna, nama, tx, ty):
    x, y = get_xy(titik)
    plt.fill(x, y, color=warna, alpha=0.3)
    plt.plot(x + [x[0]], y + [y[0]], color=warna, linewidth=2, marker='o')
    plt.text(tx, ty, nama, ha='center')

gambar(segitiga,  'red',   'Segitiga',  2.5, 4.3)
gambar(persegi,   'blue',  'Persegi',   7,   3.3)
gambar(segi_lima, 'green', 'Segi Lima', 3,   7.3)

# Atur tampilan
plt.xlim(0, 9)
plt.ylim(0, 8)
plt.xticks(range(0, 10, 1))
plt.yticks(range(0, 9, 1))
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Visualisasi Poligon dengan Python')
plt.grid(True, linestyle='--', alpha=0.7)
plt.show()