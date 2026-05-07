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
final_df_global = None

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

# ================== HELPER FUNCTIONS ==================
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

# ================== DETEKSI JENIS DOKUMEN ==================
def deteksi_jenis_dokumen(teks):
    lines = teks.splitlines()
    for i, baris in enumerate(lines):
        if "UNIFIKASI BERFORMAT STANDAR" in baris:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().replace(" ", "")
                if next_line == "BPPU":
                    return "BPPU"
        if "PASAL 21 YANG BERSIFAT FINAL" in baris:
            kata_terakhir = baris.strip().split()[-1]
            if kata_terakhir == "BP21":
                return "BP21"
    return None

# ================== EKSTRAK BPPU ==================
def ekstrak_bppu(teks):
    lines = teks.splitlines()
    
    # Nomor Bukti Potong, Masa Pajak, Sifat, Status
    nomor_bukti = masa_pajak = sifat_bukti = status_bukti = ""
    for i, baris in enumerate(lines):
        if "A. IDENTITAS WAJIB PAJAK YANG DIPOTONG DAN/ATAU DIPUNGUT PPh ATAU PENERIMA PENGHASILAN" in baris:
            if i > 0:
                prev_line = lines[i - 1].strip()
                parts = prev_line.split()
                if len(parts) >= 4:
                    nomor_bukti = parts[0]
                    masa_pajak = parts[1]
                    sifat_bukti = " ".join(parts[2:-1])
                    status_bukti = parts[-1]
            break
    
    # Konversi masa pajak
    masa_pajak_obj = ubah_tanggal(masa_pajak)
    
    # Kode Objek Pajak
    kode_objek = ""
    for i, baris in enumerate(lines):
        if "B.3 B.4 B.5 B.6 B.7" in baris:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                kode_objek = next_line.split()[0]
            break
    
    # DPP dan PPH
    dpp = pph = ""
    for i, baris in enumerate(lines):
        if "B.8 Dokumen Dasar Bukti" in baris:
            if i >= 2:
                target_line = lines[i - 2].strip()
                # Hilangkan semua teks, ambil hanya angka
                angka_semua = re.findall(r'\d[\d\.]*', target_line)
                if len(angka_semua) >= 3:
                    dpp = angka_semua[-3]
                    pph = angka_semua[-1]
            break
    
    # NPWP Pemotong
    npwp_pemotong = ""
    for baris in lines:
        if "C.1 NPWP / NIK :" in baris:
            npwp_pemotong = baris.split(":")[-1].strip()
            break
    
    # Nama Pemotong
    nama_pemotong = ""
    for i, baris in enumerate(lines):
        if "C.3 NAMA PEMOTONG DAN/ATAU PEMUNGUT" in baris:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if "PPh:" in next_line:
                    nama_pemotong = next_line.split(":")[-1].strip()
            break
    
    # Tanggal Bukti Potong
    tanggal_bukti = ""
    for baris in lines:
        if "C.4 TANGGAL :" in baris:
            tanggal_bukti = baris.split(":")[-1].strip()
            break
    
    tanggal_bukti_obj = ubah_tanggal(tanggal_bukti)
    
    return {
        'JENIS DOKUMEN': 'BPPU',
        'NOMOR BUKTI POTONG': nomor_bukti,
        'MASA PAJAK': masa_pajak_obj,
        'SIFAT BUKTI POTONG': sifat_bukti,
        'STATUS BUKTI POTONG': status_bukti,
        'KODE OBJEK PAJAK': kode_objek,
        'DPP': bersihkan_angka(dpp),
        'PPH YANG DIPOTONG': bersihkan_angka(pph),
        'NPWP PEMOTONG': npwp_pemotong,
        'NAMA PEMOTONG': nama_pemotong,
        'TANGGAL BUKTI POTONG': tanggal_bukti_obj
    }

# ================== EKSTRAK BP21 ==================
def ekstrak_bp21(teks):
    lines = teks.splitlines()
    
    # Nomor Bukti Potong, Masa Pajak, Sifat, Status
    nomor_bukti = masa_pajak = sifat_bukti = status_bukti = ""
    for i, baris in enumerate(lines):
        if "NOMOR BUKTI PEMOTONGAN MASA PAJAK SIFAT PEMOTONGAN STATUS BUKTI PEMOTONGAN" in baris:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                parts = next_line.split()
                if len(parts) >= 4:
                    nomor_bukti = parts[0]
                    masa_pajak = parts[1]
                    sifat_bukti = " ".join(parts[2:-1])
                    status_bukti = parts[-1]
            break
    
    # Konversi masa pajak
    masa_pajak_obj = ubah_tanggal(masa_pajak)
    
    # Kode Objek Pajak
    kode_objek = ""
    for i, baris in enumerate(lines):
        if "B.2 B.3 B.4 B.5 B.6 B.7" in baris:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                kode_objek = next_line.split()[0]
            break
    
    # DPP dan PPH
    dpp = pph = ""
    for i, baris in enumerate(lines):
        if "B.8 Dokumen Referensi Jenis Dokumen" in baris or "B.8 Dokumen Referensi" in baris:
            if i >= 1:
                target_line = lines[i - 1].strip()
                # Hilangkan semua teks, ambil hanya angka
                angka_bersih = re.sub(r'[A-Za-z\s]+', ' ', target_line)
                angka_semua = angka_bersih.split()
                if len(angka_semua) >= 4:
                    dpp = angka_semua[0]
                    pph = angka_semua[-1]
            break
    
    # NPWP Pemotong
    npwp_pemotong = ""
    for baris in lines:
        if "C.1 NPWP/NIK :" in baris:
            npwp_pemotong = baris.split(":")[-1].strip()
            break
    
    # Nama Pemotong
    nama_pemotong = ""
    for baris in lines:
        if "C.3 Nama Pemotong :" in baris:
            nama_pemotong = baris.split(":")[-1].strip()
            break
    
    # Tanggal Bukti Potong
    tanggal_bukti = ""
    for baris in lines:
        if "C.4 Tanggal :" in baris:
            tanggal_bukti = baris.split(":")[-1].strip()
            break
    
    tanggal_bukti_obj = ubah_tanggal(tanggal_bukti)
    
    return {
        'JENIS DOKUMEN': 'BP21',
        'NOMOR BUKTI POTONG': nomor_bukti,
        'MASA PAJAK': masa_pajak_obj,
        'SIFAT BUKTI POTONG': sifat_bukti,
        'STATUS BUKTI POTONG': status_bukti,
        'KODE OBJEK PAJAK': kode_objek,
        'DPP': bersihkan_angka(dpp),
        'PPH YANG DIPOTONG': bersihkan_angka(pph),
        'NPWP PEMOTONG': npwp_pemotong,
        'NAMA PEMOTONG': nama_pemotong,
        'TANGGAL BUKTI POTONG': tanggal_bukti_obj
    }

# ================== EKSTRAK PDF ==================
def ekstrak_pdf(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""
    
    jenis_dokumen = deteksi_jenis_dokumen(pdf_text)
    
    if jenis_dokumen == "BPPU":
        data = ekstrak_bppu(pdf_text)
    elif jenis_dokumen == "BP21":
        data = ekstrak_bp21(pdf_text)
    else:
        raise ValueError("Jenis dokumen tidak dikenali")
    
    return pd.DataFrame([data])

# ================== PROSES MULTI-PDF ==================
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
            # Deteksi sel kosong
            kosong_rows = df[df.apply(lambda x: x.isnull() | x.astype(str).str.strip().eq('')).any(axis=1)]
            if not kosong_rows.empty:
                baris_error = (kosong_rows.index + 2).tolist()
                gagal_files.append((os.path.basename(f), f"Baris {baris_error} kosong"))
            dfs.append(df)
        except Exception as e:
            gagal_files.append((os.path.basename(f), str(e)))

    if dfs:
        global final_df_global
        final_df_global = pd.concat(dfs, ignore_index=True)

        berhasil = len(selected_files) - len(gagal_files)
        pesan = f"✅ Terdapat {berhasil} PDF yang berhasil diproses."
        if gagal_files:
            pesan += "\n\n⚠ Beberapa file gagal diproses:\n"
            for fname, error in gagal_files:
                pesan += f"- {fname}: {error}\n"

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

            # Format kolom (disesuaikan karena ada kolom baru di depan)
            for cell in sheet['I']:  # NPWP PEMOTONG (sebelumnya H)
                cell.number_format = '@'
            for cell in sheet['G']:  # DPP (sebelumnya F)
                cell.number_format = '#,##0'
            for cell in sheet['H']:  # PPH YANG DIPOTONG (sebelumnya G)
                cell.number_format = '#,##0'
            for cell in sheet['C']:  # MASA PAJAK (sebelumnya B)
                cell.number_format = 'DD/MM/YYYY'
            for cell in sheet['K']:  # TANGGAL BUKTI POTONG (sebelumnya J)
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