import customtkinter as ctk
from tkinter import filedialog, messagebox
import webbrowser
import os
import re
import PyPDF2
import pandas as pd
from datetime import datetime

# ================== SETUP GUI ==================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("BUPOT EXTRACTOR")
app.geometry("900x650")
app.configure(fg_color="#0B1120")

selected_files = []
final_df_global = None   # ⬅️ data hanya di RAM

# ================= SCROLLABLE CONTAINER =================
container = ctk.CTkScrollableFrame(app, fg_color="transparent")
container.pack(fill="both", expand=True)

# ================= HEADER =================
header = ctk.CTkFrame(container, fg_color="transparent")
header.pack(fill="x", pady=15)

logo = ctk.CTkLabel(header, text="⬢  TAC ENGINE", font=("Arial", 20, "bold"), text_color="#38BDF8")
logo.pack(side="left", padx=20)

title_frame = ctk.CTkFrame(header, fg_color="transparent")
title_frame.pack(side="left")

ctk.CTkLabel(title_frame, text="BUPOT EXTRACTOR", font=("Arial", 26, "bold")).pack(anchor="w")
ctk.CTkLabel(title_frame, text="Smart Tax Document Reader", text_color="gray").pack(anchor="w")

# ================= UPLOAD PANEL =================
upload_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=2, border_color="#22D3EE")
upload_frame.pack(padx=40, pady=10, fill="x")

ctk.CTkLabel(upload_frame, text="Upload Bukti Potong (PDF)").pack(pady=(15,5))

def pilih_file():
    global selected_files
    files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
    if files:
        selected_files = list(files)
        tampilkan_file()
        status_label.configure(text=f"{len(selected_files)} file siap diproses")

ctk.CTkButton(
    upload_frame,
    text="PILIH FILE PDF",
    fg_color="#22D3EE",
    hover_color="#67E8F9",
    text_color="black",
    corner_radius=30,
    height=40,
    command=pilih_file
).pack(pady=10)

# ================= FILE LIST =================
file_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20)
file_frame.pack(padx=40, pady=10, fill="both", expand=True)

file_listbox = ctk.CTkTextbox(file_frame, height=150)
file_listbox.pack(padx=15, pady=15, fill="both", expand=True)

def tampilkan_file():
    file_listbox.delete("1.0", "end")
    for f in selected_files:
        file_listbox.insert("end", f"✔ {os.path.basename(f)}\n")

# ================== FUNGSIONAL PDF EKSTRAK ==================
bulan_map = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12
}

def ubah_tanggal(teks_tanggal):
    if not teks_tanggal:
        return ""
    teks_tanggal = teks_tanggal.strip().lower()
    match = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", teks_tanggal)
    if match:
        hari = int(match.group(1))
        bulan = bulan_map.get(match.group(2))
        tahun = int(match.group(3))
        if bulan:
            return datetime(tahun, bulan, hari)
    match = re.match(r"(\d{2})-(\d{4})", teks_tanggal)
    if match:
        bulan = int(match.group(1))
        tahun = int(match.group(2))
        return datetime(tahun, bulan, 1)
    return ""

def bersihkan_angka(teks_angka):
    if not teks_angka:
        return ""
    angka = re.sub(r"[^\d]", "", teks_angka)
    return int(angka) if angka else ""

def ambil_setelah_kata(teks, kata):
    hasil = []
    pola = rf'{re.escape(kata)}\s*(.*)'
    for baris in teks.splitlines():
        match = re.search(pola, baris, re.IGNORECASE)
        if match:
            hasil.append(match.group(1).strip())
    return hasil[0] if hasil else ""

# ================= REVISI: NOMOR, SIFAT & MASA PAJAK =================
def cari_nomor_bukti_potong(teks):
    lines = teks.splitlines()
    for i, baris in enumerate(lines):
        if "PEMUNGUTAN PPh PEMUNGUTAN" in baris:
            if i+1 < len(lines):
                bagian = lines[i+1].strip()
                match = re.match(r"(\S+)\s+(\S+)\s+(.+)\s+(\S+)$", bagian)
                if match:
                    nomor = match.group(1)
                    masa_pajak_raw = match.group(2)
                    sifat = match.group(3).strip()
                    status = match.group(4)
                    try:
                        bulan_str, tahun_str = masa_pajak_raw.split('-')
                        masa_pajak = datetime(int(tahun_str), int(bulan_str), 1)
                    except:
                        masa_pajak = masa_pajak_raw
                    return nomor, masa_pajak, sifat, status
    return "", "", "", ""

def ambil_kode_dpp_pph(teks):
    lines = teks.splitlines()
    target_line = ""
    for i, baris in enumerate(lines):
        if "B.8 Dokumen Dasar Bukti" in baris:
            if i >= 2:
                target_line = lines[i-2].strip()
            break

    kode_match = re.search(r"\d{2}-\d{3}-\d{2}", teks)
    kode_objek = kode_match.group(0) if kode_match else ""

    if not target_line:
        return kode_objek, "", ""

    angka_kotor = re.findall(r"[A-Za-z]*\d[\d\.]*", target_line)
    angka_bersih = [re.sub(r"[^\d\.]", "", x) for x in angka_kotor if re.search(r"\d", x)]

    dpp, pph = "", ""
    if len(angka_bersih) >= 3:
        dpp = angka_bersih[-3]
        pph = angka_bersih[-1]
    elif len(angka_bersih) == 2:
        dpp = angka_bersih[0]
        pph = angka_bersih[1]

    return kode_objek, dpp, pph

def ambil_nama_pemotong(teks):
    lines = teks.splitlines()
    for i, baris in enumerate(lines):
        if "C.3 NAMA PEMOTONG DAN/ATAU PEMUNGUT" in baris:
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                match = re.search(r"PPh\s*:\s*(.*)", next_line)
                if match:
                    return match.group(1).strip()
    return ""

def ambil_tanggal_ttd(teks):
    for baris in teks.splitlines():
        if "C.4 TANGGAL" in baris.upper():
            match = re.search(r"TANGGAL\s*:\s*(.*)", baris, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return ""

# ================= EKSTRAK PDF =================
def ekstrak_pdf(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""

    nomor_bukti, masa_pajak, sifat_bukti, status_bukti = cari_nomor_bukti_potong(pdf_text)
    kode_objek, dpp_text, pph_text = ambil_kode_dpp_pph(pdf_text)
    nama_pemotong = ambil_nama_pemotong(pdf_text)
    npwp_pemotong = ambil_setelah_kata(pdf_text, "C.1 NPWP / NIK :").strip()
    tanggal_bukti = ubah_tanggal(ambil_tanggal_ttd(pdf_text))

    return pd.DataFrame([{
        'NOMOR BUKTI POTONG': nomor_bukti,
        'MASA PAJAK': masa_pajak,
        'SIFAT BUKTI POTONG': sifat_bukti,
        'STATUS BUKTI POTONG': status_bukti,
        'KODE OBJEK PAJAK': kode_objek,
        'DPP': bersihkan_angka(dpp_text),
        'PPH YANG DIPOTONG': bersihkan_angka(pph_text),
        'NPWP PEMOTONG': npwp_pemotong,
        'NAMA PEMOTONG': nama_pemotong,
        'TANGGAL BUKTI POTONG': tanggal_bukti
    }])

# ================= PROSES MULTI-PDF DENGAN VALIDASI =================
def proses_data():
    if not selected_files:
        messagebox.showwarning("Peringatan", "Pilih file PDF dulu!")
        return

    status_label.configure(text="🔄 Memproses dokumen...")
    app.update()

    dfs = []
    gagal_files = []

    for f in selected_files:
        try:
            df = ekstrak_pdf(f)
            # ==== Perbaikan: deteksi sel kosong / spasi ====
            kosong_rows = df[df.apply(lambda x: x.isnull() | x.astype(str).str.strip().eq('')).any(axis=1)]
            if not kosong_rows.empty:
                baris_error = (kosong_rows.index + 2).tolist()
                gagal_files.append((os.path.basename(f), baris_error))
            dfs.append(df)
        except Exception as e:
            gagal_files.append((os.path.basename(f), "Gagal ekstrak"))

    if dfs:
        global final_df_global
        final_df_global = pd.concat(dfs, ignore_index=True)


        berhasil = len(selected_files) - len(gagal_files)
        pesan = f"✅ Terdapat {berhasil} PDF yang berhasil diproses."
        if gagal_files:
            pesan += "\n\n⚠ Beberapa file gagal diproses atau ada data kosong:\n"
            for fname, baris in gagal_files:
                pesan += f"- {fname}\n"

        status_label.configure(text=f"✅ Ekstraksi selesai! {berhasil} berhasil, {len(gagal_files)} bermasalah")
        messagebox.showinfo("Hasil Ekstraksi", pesan)
    else:
        status_label.configure(text="❌ Tidak ada PDF yang berhasil diekstrak!")
        messagebox.showerror("Error", "Tidak ada PDF yang berhasil diekstrak!")

ctk.CTkButton(
    container,
    text="⚡ PROSES SEKARANG",
    fg_color="#22C55E",
    hover_color="#4ADE80",
    corner_radius=30,
    height=45,
    command=proses_data
).pack(pady=12)

# ================= STATUS =================
status_label = ctk.CTkLabel(container, text="Status: Menunggu file...", text_color="gray")
status_label.pack()

# ================= DOWNLOAD =================
def download_excel():
    global final_df_global

    if final_df_global is None:
        messagebox.showerror("Error", "Data belum diproses!")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")]
    )

    if save_path:
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            final_df_global.to_excel(writer, index=False, sheet_name='Sheet1')
            sheet = writer.sheets['Sheet1']

            for cell in sheet['H']:
                cell.number_format = '@'
            for cell in sheet['F']:
                cell.number_format = '#,##0'
            for cell in sheet['G']:
                cell.number_format = '#,##0'
            for cell in sheet['B']:
                cell.number_format = 'DD/MM/YYYY'
            for cell in sheet['J']:
                cell.number_format = 'DD/MM/YYYY'

        messagebox.showinfo("Berhasil", "File Excel berhasil disimpan!")


ctk.CTkButton(
    container,
    text="⬇ DOWNLOAD HASIL EXCEL",
    fg_color="#A78BFA",
    hover_color="#C4B5FD",
    corner_radius=30,
    height=45,
    command=download_excel
).pack(pady=15)

# ================= PROMO PANEL =================
promo_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=2, border_color="#F59E0B")
promo_frame.pack(padx=40, pady=15, fill="x")

ctk.CTkLabel(
    promo_frame,
    text="Sambil nungguin laper ya? Pingin nyemil snack sambil kerjain ini?\nTunggu apa lagi sambil nungguin order di 🥰✨Kedai Ayam Warisan 81!!✨🥰",
    justify="center"
).pack(pady=10)

button_frame = ctk.CTkFrame(promo_frame, fg_color="transparent")
button_frame.pack()

ctk.CTkButton(button_frame, text="🛵 GoFood", fg_color="#EF4444",
              hover_color="#F87171",
              command=lambda: webbrowser.open("https://gofood.link/a/Mtv3P3L")).pack(side="left", padx=10, pady=10)

ctk.CTkButton(button_frame, text="🟢 GrabFood", fg_color="#10B981",
              hover_color="#34D399",
              command=lambda: webbrowser.open("https://r.grab.com/g/6-20260202_212151_1f6a2784162b40d5bd1c465b0e817b13_MEXMPS-6-C6NAVVMAVTDEFE")).pack(side="left", padx=10, pady=10)

def copy_nomor(event):
    app.clipboard_clear()
    app.clipboard_append("089671139111")
    messagebox.showinfo("Disalin", "Nomor berhasil disalin!")

wa_label = ctk.CTkLabel(promo_frame, text="📞 089671139111 (Klik untuk menyalin)", text_color="#22D3EE", cursor="hand2")
wa_label.pack(pady=(5,10))
wa_label.bind("<Button-1>", copy_nomor)

# ================= CREDIT =================
credit = ctk.CTkLabel(app, text="BY RAYMOND FO", text_color="gray")
credit.place(relx=0.98, rely=0.98, anchor="se")

app.mainloop()
