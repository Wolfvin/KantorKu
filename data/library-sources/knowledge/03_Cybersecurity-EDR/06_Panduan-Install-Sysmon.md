---
title: Panduan Install Sysmon dari NOL (Terminal Only)
kategori: Cybersecurity & EDR
tags: [sysmon, install, PowerShell, SwiftOnSecurity, Windows, event-log, troubleshooting]
---

# Panduan Lengkap Install Sysmon dari NOL (Terminal Only)

## Prerequisites (Sebelum Mulai)

| Requirement | Status |
|-------------|--------|
| OS | Windows 10/11 (64-bit) |
| Hak Akses | **Administrator** (WAJIB) |
| Internet | Untuk download file |
| Folder Temp | `C:\Users\user\AppData\Local\Temp` |

---

## Terminal yang Digunakan: PowerShell (Admin)

> **Kenapa PowerShell?**
> - Built-in di Windows (tidak perlu install)
> - Support download file via `Invoke-WebRequest`
> - Bisa jalankan executable dengan parameter kompleks
> - Output lebih terstruktur untuk scripting

---

## STEP 1: Buka PowerShell sebagai Administrator

### Cara 1: Lewat Start Menu

```
1. Klik Start / Tekan tombol Windows
2. Ketik: PowerShell
3. Klik kanan "Windows PowerShell" -> "Run as administrator"
4. Klik "Yes" jika muncul UAC prompt
```

### Cara 2: Lewat Run Dialog

```
1. Tekan: Windows + R
2. Ketik: powershell
3. Tekan: Ctrl + Shift + Enter (untuk run as admin)
```

### Verifikasi Admin Rights:

```powershell
# Jalankan command ini untuk pastikan sudah admin
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```
**Output harus:** `True`

---

## STEP 2: Download Sysmon dari Microsoft (Official)

```powershell
# 1. Buat folder kerja di Temp
mkdir -Force "$env:TEMP\SysmonInstall"
cd "$env:TEMP\SysmonInstall"

# 2. Download Sysmon ZIP dari Microsoft Sysinternals
Invoke-WebRequest -Uri "https://download.sysinternals.com/files/Sysmon.zip" -OutFile "$env:TEMP\SysmonInstall\Sysmon.zip"

# 3. Extract file ZIP
Expand-Archive -Path "$env:TEMP\SysmonInstall\Sysmon.zip" -DestinationPath "$env:TEMP\SysmonInstall" -Force

# 4. Verifikasi file sudah ada
dir "$env:TEMP\SysmonInstall\sysmon64.exe"
```

**Output yang diharapkan:**
```
    Directory: C:\Users\user\AppData\Local\Temp\SysmonInstall

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         3/8/2026   11:00 AM         1.2 MB sysmon64.exe
```

---

## STEP 3: Download Konfigurasi SwiftOnSecurity (Recommended)

Konfigurasi dari [SwiftOnSecurity](https://github.com/SwiftOnSecurity/sysmon-config) adalah **best practice** untuk deteksi threat.

```powershell
# Download konfigurasi XML dari GitHub
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml" -OutFile "$env:TEMP\SysmonInstall\sysmon-config.xml"

# Verifikasi file config
dir "$env:TEMP\SysmonInstall\sysmon-config.xml"
```

> **Kenapa pakai SwiftOnSecurity config?**
> - Sudah filter event noise (kurangi log sampah)
> - Fokus pada indikator compromise (IOC)
> - Updated rutin oleh komunitas security
> - Kompatibel dengan SIEM populer

---

## STEP 4: Instal Sysmon dengan Konfigurasi

```powershell
# Pastikan masih di folder SysmonInstall
cd "$env:TEMP\SysmonInstall"

# Instal Sysmon dengan konfigurasi SwiftOnSecurity
.\sysmon64.exe -i sysmon-config.xml -accepteula
```

**Output sukses:**
```
System Monitor v15.15 - System activity monitor
By Mark Russinovich and Thomas Garnier
Copyright (C) 2014-2024 Microsoft Corporation
...
Sysmon installed.
Sysmon driver installed.
Configuration file validated.
Starting SysmonDrv.
SysmonDrv started.
Starting Sysmon64.
Sysmon64 started.
```

---

## STEP 5: Verifikasi Instalasi

```powershell
# 1. Cek service Sysmon berjalan
Get-Service Sysmon64

# Output harus: Status = Running
```

```powershell
# 2. Cek Event Log sudah terdaftar
Get-WinEvent -ListLog "Microsoft-Windows-Sysmon/Operational" -ErrorAction SilentlyContinue

# Output harus ada RecordCount > 0
```

```powershell
# 3. Cek konfigurasi aktif
.\sysmon64.exe -c

# Output: Menampilkan config XML yang sedang aktif
```

```powershell
# 4. Test baca event (harus ada output)
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 1 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, Message
```

---

## STEP 6: Test Generate Event (Opsional tapi Disarankan)

```powershell
# 1. Buka Notepad (trigger Event ID 1: ProcessCreate)
notepad.exe

# 2. Tutup Notepad (trigger Event ID 5: ProcessTerminate)
# (klik X atau Ctrl+W)

# 3. Cek apakah event terekam
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 2 | 
Select-Object TimeCreated, Id, @{N='Process';E={$_.Message -match 'Image: (.+?)\r' | Out-Null; $matches[1]}} | 
Format-Table -AutoSize
```

**Output contoh:**
```
TimeCreated           Id Process
-----------          -- -------
3/8/2026 11:30:15 AM   1 C:\Windows\System32\notepad.exe
3/8/2026 11:30:20 AM   5 C:\Windows\System32\notepad.exe
```

---

## Ringkasan Command (Copy-Paste Semua)

```powershell
# === COPY DARI SINI ===

# 1. Buka PowerShell sebagai Administrator dulu!

# 2. Setup folder & download Sysmon
mkdir -Force "$env:TEMP\SysmonInstall"
cd "$env:TEMP\SysmonInstall"
Invoke-WebRequest -Uri "https://download.sysinternals.com/files/Sysmon.zip" -OutFile "$env:TEMP\SysmonInstall\Sysmon.zip"
Expand-Archive -Path "$env:TEMP\SysmonInstall\Sysmon.zip" -DestinationPath "$env:TEMP\SysmonInstall" -Force

# 3. Download konfigurasi SwiftOnSecurity
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml" -OutFile "$env:TEMP\SysmonInstall\sysmon-config.xml"

# 4. Instal Sysmon dengan config
.\sysmon64.exe -i sysmon-config.xml -accepteula

# 5. Verifikasi
Get-Service Sysmon64
Get-WinEvent -ListLog "Microsoft-Windows-Sysmon/Operational" -ErrorAction SilentlyContinue

# === SAMPAI SINI ===
```

---

## Troubleshooting (Kalau Error)

| Error | Solusi |
|-------|--------|
| `Access denied` | Pastikan run PowerShell sebagai **Administrator** |
| `File in use` | Restart PC, lalu coba install lagi |
| `Driver failed to start` | Cek Secure Boot / antivirus blokir driver |
| `Config validation failed` | Download ulang XML, pastikan tidak korup |
| `Event Log not found` | Jalankan: `wevtutil sl "Microsoft-Windows-Sysmon/Operational" /e:true` |

---

## Cara Update / Reinstall Sysmon

```powershell
# 1. Uninstall versi lama
.\sysmon64.exe -u

# 2. Install ulang dengan config terbaru
.\sysmon64.exe -i sysmon-config.xml -accepteula
```

---

## Cara Uninstall Sysmon (Jika Perlu)

```powershell
# Uninstall lengkap
.\sysmon64.exe -u -force

# Hapus folder install (opsional)
Remove-Item "$env:TEMP\SysmonInstall" -Recurse -Force
```

---

## Checklist Final

| Step | Command | Status |
|------|---------|--------|
| Buka PowerShell Admin | `Run as administrator` | Wajib |
| Download Sysmon | `Invoke-WebRequest ... Sysmon.zip` | |
| Extract file | `Expand-Archive ...` | |
| Download config | `Invoke-WebRequest ... sysmon-config.xml` | |
| Install dengan config | `.\sysmon64.exe -i sysmon-config.xml -accepteula` | |
| Verifikasi service | `Get-Service Sysmon64` | |
| Verifikasi Event Log | `Get-WinEvent -ListLog "*Sysmon*"` | |
| Test event | `notepad.exe` -> tutup -> cek log | |

---

## Tips Tambahan

1. **Simpan file config lokal** untuk backup:
   ```powershell
   Copy-Item "$env:TEMP\SysmonInstall\sysmon-config.xml" "D:\Backup\sysmon-config.xml"
   ```

2. **Jadwal update config** (opsional):
   ```powershell
   # Buat scheduled task untuk update config bulanan
   # (bisa ditambahkan nanti kalau perlu)
   ```

3. **Monitor log size** agar tidak penuh:
   ```powershell
   # Cek ukuran log
   Get-WinEvent -ListLog "Microsoft-Windows-Sysmon/Operational" | Select-Object LogName, @{N='SizeMB';E={$_.FileSize/1MB}}
   ```

---

## Setelah Install: Jalankan Script Python Kamu

Sekarang Sysmon sudah siap! Jalankan script monitoring kamu:

```powershell
# Masih di PowerShell Admin
python "d:\Raymond\KDS\SYS data\sysmon_reader.py"
```

Harusnya sekarang muncul event Sysmon yang **valid dan terfilter** berkat konfigurasi SwiftOnSecurity!

---

**Ringkasan:**
- Terminal: **PowerShell (Run as Administrator)**
- Download: Microsoft Sysinternals + SwiftOnSecurity config
- Install: `.\sysmon64.exe -i sysmon-config.xml -accepteula`
- Verifikasi: `Get-Service` + `Get-WinEvent`
