---
title: Panduan Uninstall Sysmon (Terminal Only)
kategori: Cybersecurity & EDR
tags: [sysmon, uninstall, PowerShell, Windows, removal]
---

# Panduan Uninstall Sysmon (Terminal Only)

## Terminal yang Digunakan

**PowerShell (Run as Administrator)**

---

## Langkah Uninstall Sysmon

### Step 1: Buka PowerShell sebagai Administrator

```
Klik kanan PowerShell -> Run as Administrator
```

### Step 2: Pindah ke Folder Sysmon

```powershell
cd "$env:TEMP\Sysmon"
```

### Step 3: Uninstall Sysmon

```powershell
.\sysmon64.exe -u
```

### Step 4: Jika Error, Pakai Force Uninstall

```powershell
.\sysmon64.exe -u force
```

### Step 5: Hapus File Sysmon (Opsional)

```powershell
cd ..
Remove-Item -Path "Sysmon" -Recurse -Force
Remove-Item -Path "Sysmon.zip" -Force
```

### Step 6: Verifikasi Sysmon Sudah Terhapus

```powershell
Get-Service Sysmon
```

**Kalau sukses, outputnya:**
```
Get-Service : Cannot find any service with service name 'Sysmon'.
```

---

## Checklist Uninstall

| Langkah | Command | Status |
|---------|---------|--------|
| 1 | Buka PowerShell (Admin) | |
| 2 | `cd "$env:TEMP\Sysmon"` | |
| 3 | `.\sysmon64.exe -u` | |
| 4 | `.\sysmon64.exe -u force` (jika perlu) | |
| 5 | Hapus folder Sysmon | |
| 6 | `Get-Service Sysmon` (verifikasi) | |

---

## Catatan

- **Wajib Run as Administrator**
- **Jika masih ada error**, restart komputer dulu, lalu ulangi Step 3
- **Event Log tetap ada** di sistem (tidak terhapus otomatis)
