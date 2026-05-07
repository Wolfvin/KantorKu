import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import datetime
import os
import re
import webbrowser

# ================== SETUP GUI ==================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("SMART EXCEL AUTOCOMBINER")
app.geometry("900x650")
app.configure(fg_color="#0B1120")

selected_files = []
final_df_global = None  # ⬅️ Data hanya di RAM

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

ctk.CTkLabel(title_frame, text="SMART EXCEL AUTOCOMBINER", font=("Arial", 26, "bold")).pack(anchor="w")
ctk.CTkLabel(title_frame, text="Combine Multiple Excel Files with Auto Numbering", text_color="gray").pack(anchor="w")

# ================= UPLOAD PANEL =================
upload_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=2, border_color="#22D3EE")
upload_frame.pack(padx=40, pady=10, fill="x")

ctk.CTkLabel(upload_frame, text="Upload File Excel (.xlsx, .xls)").pack(pady=(15,5))

def pilih_file():
    global selected_files
    files = filedialog.askopenfilenames(
        filetypes=[("Excel Files", "*.xlsx *.xls")]
    )
    if files:
        selected_files = list(files)
        tampilkan_file()
        status_label.configure(text=f"{len(selected_files)} file siap digabungkan")

ctk.CTkButton(
    upload_frame,
    text="PILIH FILE EXCEL",
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
    for i, f in enumerate(selected_files, 1):
        file_listbox.insert("end", f"{i}. ✔ {os.path.basename(f)}\n")

# ================= HELPER FUNCTIONS =================
bulan_map = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12
}

def ubah_tanggal(teks_tanggal):
    """
    Mengkonversi berbagai format tanggal menjadi datetime object.
    
    Supported formats:
    - "03 Maret 2025" atau "3 Maret 2025" → 03/03/2025
    - "Desember 2025" atau "desember 2025" → 01/12/2025
    - "03-2025" → 01/03/2025
    - "01/11/2025" atau "2025-11-01" → auto-parse
    """
    if not teks_tanggal:
        return ""
    if isinstance(teks_tanggal, datetime):
        return teks_tanggal
    
    # Clean and normalize input
    teks_tanggal = str(teks_tanggal).strip().lower()
    
    # ✅ Format: "Desember 2025" atau "desember 2025" (BULAN TAHUN)
    # Pattern: bulan_nama + spasi + tahun (4 digit)
    match = re.match(r"([a-z]+)\s+(\d{4})", teks_tanggal)
    if match:
        bulan_nama = match.group(1)
        tahun = int(match.group(2))
        bulan = bulan_map.get(bulan_nama)
        if bulan:
            return datetime(tahun, bulan, 1)  # Tanggal selalu 01
    
    # ✅ Format: "03 Maret 2025" atau "3 Maret 2025" (HARI BULAN TAHUN)
    # Pattern: 1-2 digit + spasi + bulan_nama + spasi + tahun
    match = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", teks_tanggal)
    if match:
        hari = int(match.group(1))
        bulan_nama = match.group(2)
        tahun = int(match.group(3))
        bulan = bulan_map.get(bulan_nama)
        if bulan:
            return datetime(tahun, bulan, hari)
    
    # ✅ Format: "03-2025" (BULAN-TAHUN numeric)
    match = re.match(r"(\d{2})-(\d{4})", teks_tanggal)
    if match:
        bulan = int(match.group(1))
        tahun = int(match.group(2))
        return datetime(tahun, bulan, 1)  # Tanggal selalu 01
    
    # ✅ Format: "01/11/2025" atau "2025-11-01" (standard formats)
    try:
        return pd.to_datetime(teks_tanggal)
    except:
        pass
    
    return ""
# ================= FASE 1: GABUNGKAN DATA (PRESERVE AS STRING) =================
def combine_excel():
    """
    Fase 1: Gabungkan semua data Excel ke DataFrame di RAM
    CRITICAL: Read as STRING to preserve long numbers like NPWP!
    """
    global final_df_global
    
    if not selected_files:
        messagebox.showwarning("Peringatan", "Pilih file Excel dulu!")
        return

    status_label.configure(text="🔄 Menggabungkan data...")
    app.update()

    try:
        # ✅ CRITICAL: Read as STRING to preserve long numbers
        df_first = pd.read_excel(selected_files[0], dtype=str)
        headers = df_first.columns.tolist()
        
        # List untuk menyimpan semua data
        all_data = []
        
        # File pertama: ambil semua data
        for idx, row in df_first.iterrows():
            all_data.append(row.tolist())
        
        # File kedua dan seterusnya: skip header, ambil data saja
        for excel_file in selected_files[1:]:
            df = pd.read_excel(excel_file, dtype=str)  # ✅ Read as string
            for idx, row in df.iterrows():
                all_data.append(row.tolist())
        
        # Buat DataFrame final (keep as string!)
        final_df_global = pd.DataFrame(all_data, columns=headers)
        
        # ✅ Tambahkan kolom nomor urut di kolom pertama (A)
        final_df_global.insert(0, 'NO', range(1, len(final_df_global) + 1))
        
        # ✅ JANGAN convert tanggal di sini! Biarkan sebagai string!
        # Conversion akan dilakukan saat export
        
        status_label.configure(text=f"✅ Data berhasil digabungkan! Total: {len(final_df_global)} baris")
        messagebox.showinfo(
            "Berhasil", 
            f"Data berhasil digabungkan!\n\n"
            f"Total baris: {len(final_df_global)}\n"
            f"Total file: {len(selected_files)}\n\n"
            f"Klik 'DOWNLOAD EXCEL' untuk export dengan format!"
        )
    
    except Exception as e:
        status_label.configure(text="❌ Gagal menggabungkan file!")
        messagebox.showerror("Error", f"Gagal menggabungkan file:\n{str(e)}")

# ================= FASE 2: DOWNLOAD EXCEL (CONVERT & FORMAT) =================
def download_excel():
    """
    Fase 2: Export DataFrame ke Excel dengan format lengkap
    - Convert dates at export time
    - Force text format for NPWP columns
    - Number formatting for DPP/PPH
    """
    global final_df_global
    
    if final_df_global is None:
        messagebox.showerror("Error", "Data belum diproses!\n\nKlik 'GABUNGKAN SEKARANG' dulu!")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")],
        initialfile="Combined_Excel.xlsx"
    )
    
    if not save_path:
        status_label.configure(text="❌ Penyimpanan dibatalkan")
        return

    status_label.configure(text="🔄 Membuat file Excel...")
    app.update()

    try:
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            final_df_global.to_excel(writer, index=False, sheet_name='Sheet1')
            sheet = writer.sheets['Sheet1']
            
            # ================= STYLING =================
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # ================= HEADER ROW (ROW 1) =================
            for cell in sheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # ================= FORMAT COLUMNS =================
# ================= FORMAT COLUMNS =================
            # Kolom A (NO) - Center alignment
            for cell in sheet['A'][1:]:  # Skip header
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
            
            # Kolom B (MASA PAJAK) - Convert string to date + format
            for cell in sheet['B'][1:]:
                if cell.value:
                    # Convert string to datetime
                    converted_date = ubah_tanggal(cell.value)
                    if converted_date:
                        cell.value = converted_date
                        cell.number_format = 'DD/MM/YYYY'
                    # If conversion fails, keep as text
                cell.border = thin_border
            
            # ✅ Kolom C (NOMOR BUKTI POTONG) - Text format
            for cell in sheet['C'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom D (SIFAT) - Text format
            for cell in sheet['D'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom E (STATUS) - Text format
            for cell in sheet['E'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom F (KODE OBJEK PAJAK) - Text format
            for cell in sheet['F'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom G (DPP) - Number format dengan separator
            for cell in sheet['G'][1:]:
                if cell.value:
                    try:
                        if isinstance(cell.value, str):
                            cell.value = int(cell.value.replace(',', '').replace('.', ''))
                        cell.number_format = '#,##0'
                    except:
                        pass
                cell.border = thin_border
            
            # ✅ Kolom H (PPH YANG DIPOTONG) - Number format dengan separator
            for cell in sheet['H'][1:]:
                if cell.value:
                    try:
                        if isinstance(cell.value, str):
                            cell.value = int(cell.value.replace(',', '').replace('.', ''))
                        cell.number_format = '#,##0'
                    except:
                        pass
                cell.border = thin_border
            
            # ✅ Kolom I (NPWP PEMOTONG) - Text format (CRITICAL!)
            for cell in sheet['I'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom J (NAMA PEMOTONG) - Text format
            for cell in sheet['J'][1:]:
                cell.number_format = '@'
                cell.border = thin_border
            
            # ✅ Kolom K - Number format dengan separator
            for cell in sheet['K'][1:]:
                if cell.value:
                    try:
                        if isinstance(cell.value, str):
                            cell.value = int(cell.value.replace(',', '').replace('.', ''))
                        cell.number_format = '#,##0'
                    except:
                        pass
                cell.border = thin_border
            
            # ✅ Kolom L - Number format dengan separator
            for cell in sheet['L'][1:]:
                if cell.value:
                    try:
                        if isinstance(cell.value, str):
                            cell.value = int(cell.value.replace(',', '').replace('.', ''))
                        cell.number_format = '#,##0'
                    except:
                        pass
                cell.border = thin_border
            
            # ✅ Kolom M sampai V - Text format dengan border
            for col in ['M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V']:
                for cell in sheet[col][1:]:
                    cell.number_format = '@'
                    cell.border = thin_border
            
            # ================= AUTO-ADJUST WIDTH =================
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                
                # Set width (min 10, max 50)
                adjusted_width = min(max(max_length + 2, 10), 50)
                sheet.column_dimensions[column_letter].width = adjusted_width
        
        status_label.configure(text="✅ File Excel berhasil disimpan!")
        messagebox.showinfo(
            "Berhasil", 
            f"File Excel berhasil disimpan!\n\n"
            f"Lokasi: {save_path}\n"
            f"Total baris: {len(final_df_global)}"
        )
    
    except Exception as e:
        status_label.configure(text="❌ Gagal menyimpan file!")
        messagebox.showerror("Error", f"Gagal menyimpan file:\n{str(e)}")
# ================= BUTTONS =================
ctk.CTkButton(
    container,
    text="⚡ GABUNGKAN SEKARANG",
    fg_color="#22C55E",
    hover_color="#4ADE80",
    corner_radius=30,
    height=45,
    command=combine_excel
).pack(pady=12)

ctk.CTkButton(
    container,
    text="⬇ DOWNLOAD EXCEL",
    fg_color="#A78BFA",
    hover_color="#C4B5FD",
    corner_radius=30,
    height=45,
    command=download_excel
).pack(pady=5)

# ================= STATUS =================
status_label = ctk.CTkLabel(container, text="Status: Menunggu file...", text_color="gray")
status_label.pack(pady=10)

# ================= INFO PANEL =================
info_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=2, border_color="#818CF8")
info_frame.pack(padx=40, pady=15, fill="x")

ctk.CTkLabel(
    info_frame,
    text="ℹ️ Cara Kerja:",
    font=("Arial", 14, "bold"),
    text_color="#818CF8"
).pack(pady=(10,5))

ctk.CTkLabel(
    info_frame,
    text="1. Klik 'PILIH FILE EXCEL' → pilih multiple files (Ctrl+Click)\n"
         "2. Klik 'GABUNGKAN SEKARANG' → data digabung di RAM\n"
         "3. Klik 'DOWNLOAD EXCEL' → export dengan format lengkap\n\n"
         "Format otomatis:\n"
         "• Kolom A (NO): Nomor urut otomatis (1, 2, 3...)\n"
         "• Kolom B: Format tanggal DD/MM/YYYY (03-2025 → 01/03/2025)\n"
         "• Kolom F & G: Angka dengan separator ribuan (#,##0)\n"
         "• Kolom H: Text format (NPWP)\n"
         "• Kolom J: Format tanggal DD/MM/YYYY\n"
         "• Header berwarna biru + semua cell ada border",
    justify="left",
    text_color="gray"
).pack(padx=20, pady=(0,10))

# ================= PROMO PANEL =================
promo_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=20, border_width=2, border_color="#F59E0B")
promo_frame.pack(padx=40, pady=15, fill="x")

ctk.CTkLabel(
    promo_frame,
    text="Sambil nungguin laper ya? Pingin nyemil snack sambil kerjain ini?\n"
         "Tunggu apa lagi sambil nungguin order di 🥰✨Kedai Ayam Warisan 81!!✨🥰",
    justify="center"
).pack(pady=10)

button_frame = ctk.CTkFrame(promo_frame, fg_color="transparent")
button_frame.pack()

ctk.CTkButton(
    button_frame, 
    text="🛵 GoFood", 
    fg_color="#EF4444",
    hover_color="#F87171",
    command=lambda: webbrowser.open("https://gofood.link/a/Mtv3P3L")
).pack(side="left", padx=10, pady=10)

ctk.CTkButton(
    button_frame, 
    text="🟢 GrabFood", 
    fg_color="#10B981",
    hover_color="#34D399",
    command=lambda: webbrowser.open(
        "https://r.grab.com/g/6-20260202_212151_1f6a2784162b40d5bd1c465b0e817b13_MEXMPS-6-C6NAVVMAVTDEFE"
    )
).pack(side="left", padx=10, pady=10)

def copy_nomor(event):
    app.clipboard_clear()
    app.clipboard_append("089671139111")
    messagebox.showinfo("Disalin", "Nomor berhasil disalin!")

wa_label = ctk.CTkLabel(
    promo_frame, 
    text="📞 089671139111 (Klik untuk menyalin)", 
    text_color="#22D3EE", 
    cursor="hand2"
)
wa_label.pack(pady=(5,10))
wa_label.bind("<Button-1>", copy_nomor)

# ================= CREDIT =================
credit = ctk.CTkLabel(app, text="BY RAYMOND FO", text_color="gray")
credit.place(relx=0.98, rely=0.98, anchor="se")

app.mainloop()