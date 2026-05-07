import fitz
import imagehash
from PIL import Image
import matplotlib.pyplot as plt
import io
import tkinter as tk
from tkinter import filedialog

def show_and_hash_first_image_page1(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]

    images = page.get_images(full=True)
    if not images:
        print("❌ TYPE 1: TIDAK ADA GAMBAR")
        return None

    xref = images[0][0]
    pix = fitz.Pixmap(doc, xref)

    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    img = Image.open(io.BytesIO(pix.tobytes("png")))

    # TAMPILKAN GAMBAR
    plt.imshow(img)
    plt.title("Gambar pertama (yang di-hash)")
    plt.axis("off")
    plt.show()

    h = str(imagehash.phash(img))
    print("✅ HASH GAMBAR:", h)

    return h

# === START PROGRAM ===
root = tk.Tk()
root.withdraw()  # sembunyikan window utama

pdf_path = filedialog.askopenfilename(
    title="Pilih file PDF faktur",
    filetypes=[("PDF Files", "*.pdf")]
)

if not pdf_path:
    print("❌ Tidak ada file dipilih")
else:
    print("📄 File dipilih:", pdf_path)
    show_and_hash_first_image_page1(pdf_path)
