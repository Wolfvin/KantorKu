import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import PyPDF2
import pandas as pd
import webbrowser

# ================== SETUP GUI ==================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Smart PDF Renamer")
app.geometry("950x700")
app.configure(fg_color="#0A0F1F")

selected_files = []
hasil_excel_path = "rename_script.xlsx"

# ================= SCROLLABLE CONTAINER =================
container = ctk.CTkScrollableFrame(app, fg_color="transparent")
container.pack(fill="both", expand=True, padx=10, pady=10)

# ================= HEADER =================
header = ctk.CTkFrame(container, fg_color="#0F172A", corner_radius=15)
header.pack(fill="x", pady=15)

logo = ctk.CTkLabel(header, text="⬢", font=("Arial", 24, "bold"), text_color="#38BDF8")
logo.pack(side="left", padx=(20,10), pady=10)

title_frame = ctk.CTkFrame(header, fg_color="transparent")
title_frame.pack(side="left")

ctk.CTkLabel(title_frame, text="Smart PDF Renamer", font=("Arial", 26, "bold"), text_color="#E2E8F0").pack(anchor="w")
ctk.CTkLabel(title_frame, text="Auto Rename PDFs for CMD", text_color="#94A3B8").pack(anchor="w")

# ================= UPLOAD PANEL =================
upload_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=1, border_color="#1F2937")
upload_frame.pack(padx=40, pady=10, fill="x")

ctk.CTkLabel(upload_frame, text="Upload PDF Files", font=("Arial", 16, "bold")).pack(pady=(15,5))

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
file_frame = ctk.CTkFrame(container, fg_color="#0F172A", corner_radius=20)
file_frame.pack(padx=40, pady=10, fill="both", expand=True)

file_listbox = ctk.CTkTextbox(file_frame, height=150, fg_color="#0B1220")
file_listbox.pack(padx=15, pady=15, fill="both", expand=True)

def tampilkan_file():
    file_listbox.delete("1.0", "end")
    for f in selected_files:
        file_listbox.insert("end", f"✔ {os.path.basename(f)}\n")

# ================= PDF PARSING UTILS =================
def ambil_baris_setelah(teks, kata):
    lines = teks.splitlines()
    for i, line in enumerate(lines):
        if kata.lower() in line.lower() and i+1 < len(lines):
            return lines[i+1].strip()
    return ""

def get_month_prefix(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""

    baris = ambil_baris_setelah(pdf_text, "PEMUNGUTAN PPh PEMUNGUTAN")
    if baris:
        kata = baris.split()[1]  # misal 01-2025
        prefix = kata[:2]
        return prefix
    return "00"

def ekstrak_nama_file(pdf_path, urut):
    reader = PyPDF2.PdfReader(pdf_path)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text() or ""

    baris_bppu = ambil_baris_setelah(pdf_text, "UNIFIKASI BERFORMAT STANDAR")
    kata_bppu = baris_bppu.split()[0] if baris_bppu else "UNKNOWN"

    baris_25000 = ambil_baris_setelah(pdf_text, "PEMUNGUTAN PPh PEMUNGUTAN")
    kata_25000 = baris_25000.split()[0] if baris_25000 else "UNKNOWN"

    baris_nama = ambil_baris_setelah(pdf_text, "C.3 NAMA PEMOTONG DAN/ATAU PEMUNGUT")
    kata_nama = baris_nama.replace("PPh:", "").strip() if baris_nama else "UNKNOWN"

    kata_normal = baris_25000.split()[-1] if baris_25000 else "UNKNOWN"

    nama_file_baru = f"{urut:02d} {kata_bppu} - {kata_25000} - {kata_nama} ({kata_normal}).pdf"
    return nama_file_baru

# ================= MODE 1 – SORTER =================
def generate_sorter():
    if not selected_files:
        messagebox.showwarning("Peringatan", "Pilih file PDF dulu!")
        return

    status_label.configure(text="🔄 Generating sorter...")
    app.update()

    rename_lines = []
    for f in selected_files:
        try:
            prefix = get_month_prefix(f)  # ambil 2 digit bulan
            rename_lines.append(f'ren "{os.path.basename(f)}" "{prefix}&{os.path.basename(f)}"')
        except:
            rename_lines.append(f'# ERROR processing {os.path.basename(f)}')

    # Setiap rename per baris di Excel
    df = pd.DataFrame({'Sorter Script': rename_lines})
    df.to_excel(hasil_excel_path, index=False)

    status_label.configure(text="✅ Sorter script selesai dibuat!")
    messagebox.showinfo("Sukses", f"Excel sorter script siap!\n{hasil_excel_path}")

# ================= MODE 2 – FULL RENAME =================
def generate_full_rename():
    if not selected_files:
        messagebox.showwarning("Peringatan", "Pilih file PDF dulu!")
        return

    status_label.configure(text="🔄 Generating full rename...")
    app.update()

    rename_lines = []
    for idx, f in enumerate(selected_files, start=1):
        try:
            nama_baru = ekstrak_nama_file(f, idx)
            rename_lines.append(f'ren "{os.path.basename(f)}" "{nama_baru}"')
        except:
            rename_lines.append(f'# ERROR processing {os.path.basename(f)}')

    # Setiap rename per baris di Excel
    df = pd.DataFrame({'Full Rename Script': rename_lines})
    df.to_excel(hasil_excel_path, index=False)

    status_label.configure(text="✅ Full rename script selesai dibuat!")
    messagebox.showinfo("Sukses", f"Excel full rename script siap!\n{hasil_excel_path}")

# ================= BUTTONS =================
ctk.CTkButton(
    container,
    text="⚡ GENERATE SORTER (01&filename.pdf ...)",
    fg_color="#22C55E",
    hover_color="#4ADE80",
    corner_radius=30,
    height=45,
    command=generate_sorter
).pack(pady=8)

ctk.CTkButton(
    container,
    text="⚡ GENERATE FULL RENAME (01 BPPU ...)",
    fg_color="#2563EB",
    hover_color="#3B82F6",
    corner_radius=30,
    height=45,
    command=generate_full_rename
).pack(pady=8)

# ================= STATUS =================
status_label = ctk.CTkLabel(container, text="Status: Menunggu file...", text_color="#94A3B8")
status_label.pack()

# ================= DOWNLOAD =================
def download_excel():
    if not os.path.exists(hasil_excel_path):
        messagebox.showerror("Error", "File Excel belum dibuat!")
        return
    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel Files", "*.xlsx")])
    if save_path:
        import shutil
        shutil.copy(hasil_excel_path, save_path)
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
promo_frame.pack(padx=40, pady=20, fill="x")

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
credit = ctk.CTkLabel(container, text="BY RAYMOND FO", text_color="gray")
credit.pack(anchor="e", pady=(0,5))

app.mainloop()
