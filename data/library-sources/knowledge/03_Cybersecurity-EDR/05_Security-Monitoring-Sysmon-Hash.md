---
title: Security Monitoring dengan Sysmon — Hash, AI Analisis Log, Privacy
kategori: Cybersecurity & EDR
tags: [sysmon, hash, SHA256, AI-analisis, log-monitoring, privacy, sanitization, human-in-the-loop, virtual-environment]
---

# Security Monitoring dengan Sysmon

## Fungsi & Kegunaan Hash (SHA256)

### Apa Itu Hash?

**Hash** adalah nilai unik yang dihasilkan dari proses matematis terhadap isi sebuah file. Bayangkan seperti **sidik jari digital** — setiap file punya hash yang berbeda.

```
File: powershell.exe
Hash SHA256: 0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46
```

---

### 6 Fungsi Utama Hash dalam Security

| # | Fungsi | Penjelasan | Contoh Kasus |
|---|--------|------------|--------------|
| **1** | **Verifikasi Integritas File** | Memastikan file belum diubah/dimodifikasi | File sistem Windows yang tiba-tiba hash-nya berubah = kemungkinan diinfeksi malware |
| **2** | **Deteksi Malware Known** | Cocokkan hash dengan database malware | Hash match dengan ransomware di VirusTotal = ALERT! |
| **3** | **Identifikasi File** | Mengenali file meski namanya diubah | `svchost.exe` palsu di folder Temp bisa dikenali dari hash yang berbeda |
| **4** | **Tracking Versi File** | Monitor perubahan versi file | Update resmi Microsoft akan mengubah hash secara legitimate |
| **5** | **Allowlist/Blocklist** | Daftar file yang diizinkan/diblokir | Hanya file dengan hash tertentu yang boleh jalan |
| **6** | **Forensik Digital** | Bukti investigasi insiden security | Hash digunakan sebagai evidence di pengadilan |

---

### Contoh Implementasi di Script

```python
# Database hash malware known
MALWARE_HASHES = [
    "ABC123...",  # Ransomware sample
    "DEF456...",  # Trojan sample
]

# Database hash file legitimate
ALLOWED_HASHES = [
    "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46",  # PowerShell resmi
    "CCE21C0E8710E304273E98AC4B2B0F5ACEB639ACBCD2343CBAA5C4E81619C45B",  # Python resmi
]

def verify_hash(file_hash, file_path):
    if file_hash in MALWARE_HASHES:
        return "CRITICAL: Known malware detected!"
    elif file_hash in ALLOWED_HASHES:
        return "VERIFIED: Legitimate file"
    else:
        return "UNKNOWN: Needs investigation"
```

---

### Limitasi Hash

| Limitasi | Penjelasan | Mitigasi |
|----------|------------|----------|
| **Fileless Malware** | Malware di memory tidak punya file -> tidak ada hash | Gabung dengan monitoring behavior |
| **Hash Collision** | 2 file berbeda punya hash sama (sangat jarang) | Pakai multiple algorithm (MD5 + SHA256) |
| **File Modifikasi Kecil** | 1 bit berubah = hash berubah total | Update database hash berkala |
| **Tidak Deteksi Intent** | File legitimate bisa dipakai untuk tujuan jahat | Analisis context & behavior |

---

### Cara Cek Hash Manual

```powershell
# PowerShell command
Get-FileHash "C:\Windows\System32\powershell.exe" -Algorithm SHA256

# Online verification
# Kunjungi: virustotal.com -> paste hash -> lihat hasil deteksi
```

---

## Peran AI dalam Analisis Log

### Kenapa AI Cocok untuk Analisis Log?

| Keunggulan AI | Penjelasan |
|---------------|------------|
| **Pattern Recognition** | AI bisa deteksi pola yang manusia mungkin lewatkan |
| **Speed** | Proses ribuan event per detik |
| **Context Understanding** | AI paham hubungan parent-child process |
| **Learning** | AI bisa belajar dari data baru (machine learning) |

---

### Kemampuan AI dalam Analisis Sysmon

#### 1. Memahami Log Terstruktur

```json
{
  "EventID": 1,
  "Image": "powershell.exe",
  "ParentImage": "winword.exe",
  "CommandLine": "powershell -enc JAB..."
}
```

**AI Analysis:** Mencurigakan! Word tidak biasa spawn PowerShell dengan encoded command.

#### 2. Pattern Recognition untuk Anomaly Detection

| Pola Normal | Pola Anomali |
|-------------|--------------|
| `explorer.exe` -> `chrome.exe` | `winword.exe` -> `powershell.exe` |
| Path: `C:\Windows\System32\` | Path: `C:\Users\...\AppData\Local\Temp\` |
| Command: jelas & readable | Command: encoded/obfuscated |

#### 3. Konteks Parent-Child Process

```
Normal:
services.exe -> svchost.exe -> RuntimeBroker.exe

Mencurigakan:
chrome.exe -> cmd.exe -> powershell.exe
```

---

### Privacy & Security Warning

**PENTING:** Jangan kirim log mentah ke AI publik!

| Data Sensitif | Risiko | Solusi |
|---------------|--------|--------|
| Username | Identitas terungkap | Replace dengan `[USER]` |
| Hostname | Info infrastruktur | Replace dengan `[HOST]` |
| IP Address | Network topology | Replace dengan `[IP]` |
| File Path | Struktur sistem | Sanitize sensitive paths |
| Hash | Bisa di-reverse lookup | Hanya kirim hash mencurigakan |

**Contoh Sanitization:**
```python
def sanitize_log(log_entry):
    log_entry = log_entry.replace("LAPTOP-OJKPVJ0R", "[HOSTNAME]")
    log_entry = log_entry.replace("user", "[USERNAME]")
    log_entry = log_entry.replace("C:\\Users\\user", "C:\\Users\\[USER]")
    return log_entry
```

---

### Ide Integrasi AI ke Script

```python
# Filter event sebelum kirim ke AI (hemat cost & privacy)
def should_send_to_ai(event):
    suspicious_indicators = [
        'powershell -enc',
        'certutil -decode',
        'bitsadmin /transfer',
        'AppData\\Local\\Temp',
        'Downloads\\'
    ]
    
    for indicator in suspicious_indicators:
        if indicator in event.get('CommandLine', '') or \
           indicator in event.get('Image', ''):
            return True
    return False

# Hanya kirim event mencurigakan
if should_send_to_ai(event):
    sanitized = sanitize_log(str(event))
    ai_response = call_ai_api(sanitized)
```

---

### Human-in-the-Loop Concept

```
+-------------+    +-------------+    +-------------+
|   Sysmon    | -> |     AI      | -> |   Human     |
|   (Logs)    |    |  (Analysis) |    | (Decision)  |
+-------------+    +-------------+    +-------------+
       |                  |                  |
  Generate           Flag suspicious    Confirm/Reject
  events             events             & Take action
```

**Kenapa Human-in-the-Loop Penting?**
- AI bisa **false positive** (alert padahal aman)
- AI bisa **false negative** (lewatkan threat)
- Human punya **context bisnis** yang AI tidak tahu
- **Accountability** — keputusan akhir tetap manusia

---

## Miscellaneous (Lain-Lain)

### Penggunaan Virtual Environment (`.venv`)

**Apa Itu Virtual Environment?**
Ruang kerja terisolasi untuk project Python tertentu.

**Kenapa Pakai `.venv`?**

| Manfaat | Penjelasan |
|---------|------------|
| **Isolasi Dependency** | Library project A tidak conflict dengan project B |
| **Version Control** | Bisa pakai Python versi berbeda per project |
| **Reproducibility** | Project bisa dijalankan di mesin lain dengan setup sama |
| **Clean Uninstall** | Hapus `.venv` = hapus semua dependency project |

**Cara Kerja di Project Ini:**
```
d:\Raymond\KDS\
+-- .venv/                    # Virtual environment
|   +-- Scripts/
|   |   +-- python.exe       # Python interpreter lokal
|   |   +-- activate.bat     # Activate untuk CMD
|   |   +-- Activate.ps1     # Activate untuk PowerShell
|   +-- Lib/
|       +-- site-packages/   # Library yang diinstall (pywin32, dll)
+-- SYS data/
|   +-- sysmon_reader.py     # Script utama
+-- ...
```

**Command Activation:**
```powershell
# PowerShell
& d:/Raymond/KDS/.venv/Scripts/Activate.ps1

# CMD
d:\Raymond\KDS\.venv\Scripts\activate.bat
```

---

### Path Instalasi & Lokasi Project

| Komponen | Path | Keterangan |
|----------|------|------------|
| **Python Core** | `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\` | Instalasi Python 3.14 (64-bit) |
| **Virtual Env** | `d:\Raymond\KDS\.venv\` | Virtual environment untuk project KDS |
| **Script Location** | `d:\Raymond\KDS\SYS data\sysmon_reader.py` | Script monitoring Sysmon |
| **Sysmon Temp** | `C:\Users\user\AppData\Local\Temp\Sysmon\` | Folder temporary Sysmon installer |

**Struktur Command Execution:**
```
Python Manager (WindowsApps)
    +-- Python Core (pythoncore-3.14-64)
        +-- Virtual Environment (.venv)
            +-- Script (sysmon_reader.py)
```

---

### Waktu Sistem (Terdeteksi Tahun 2026)

**Observasi dari Log:**
```
UtcTime: 2026-03-08 04:09:02.741
```

**Kemungkinan Penyebab:**

| Penyebab | Penjelasan |
|----------|------------|
| **System Time Setting** | Jam sistem diset ke masa depan (testing purpose?) |
| **Timezone Issue** | Konversi timezone tidak tepat |
| **Future Date** | Memang diset untuk testing/scenario tertentu |

**Impact pada Monitoring:**
- Alert timestamp mungkin tidak akurat
- Korelasi event dengan real-time jadi sulit
- Untuk learning/testing = tidak masalah

**Best Practice:**
```python
# Selalu gunakan UTC untuk logging
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
```

---

### Informasi Sistem dari Log

| Field | Nilai | Keterangan |
|-------|-------|------------|
| **Hostname** | `LAPTOP-OJKPVJ0R` | Nama komputer/laptop |
| **Username** | `user` | Account user yang menjalankan script |
| **User Domain** | `LAPTOP-OJKPVJ0R\user` | Local user (bukan domain) |
| **Integrity Level** | `High` / `System` | Level privilege proses |
| **Session ID** | `0` / `1` | Session 0 = System, Session 1 = User |

**Security Implication:**
```
NT AUTHORITY\SYSTEM    -> Highest privilege (kernel level)
LAPTOP-OJKPVJ0R\user   -> Standard user privilege
NT AUTHORITY\LOCAL SERVICE -> Service account (limited)
```

---

## Glossary (Istilah Teknis)

| Istilah | Definisi |
|---------|----------|
| **Hash** | Nilai unik hasil fungsi kriptografi dari data/file. Perubahan 1 bit pada file akan menghasilkan hash yang completamente berbeda. |
| **SHA256** | Secure Hash Algorithm 256-bit. Standar kriptografi untuk menghasilkan hash 64 karakter hexadecimal. |
| **Hash Collision** | Kondisi dimana 2 file berbeda menghasilkan hash yang sama. Sangat jarang terjadi pada SHA256. |
| **Fileless Malware** | Malware yang berjalan di memory tanpa menulis file ke disk, sehingga tidak punya hash untuk dideteksi. |
| **Allowlist** | Daftar file/process yang diizinkan untuk berjalan. Semua yang tidak ada di daftar akan diblokir. |
| **Blocklist** | Daftar file/process yang diblokir. Semua yang tidak ada di daftar diizinkan berjalan. |
| **Parent-Child Process** | Hubungan hierarki antar proses. Parent adalah proses yang memanggil/membuat child process. |
| **Anomaly Detection** | Teknik mendeteksi pola yang menyimpang dari baseline normal. |
| **False Positive** | Alert yang muncul padahal tidak ada threat (alarm palsu). |
| **False Negative** | Threat yang tidak terdeteksi oleh sistem (lolos dari radar). |
| **Human-in-the-Loop** | Konsep dimana manusia tetap terlibat dalam pengambilan keputusan meskipun ada otomatisasi AI. |
| **Virtual Environment** | Lingkungan Python terisolasi untuk mengelola dependency per project tanpa conflict. |
| **Integrity Level** | Level keamanan Windows yang menentukan akses proses ke resource sistem (Low, Medium, High, System). |
| **Session ID** | Identifier untuk session login. Session 0 untuk service/system, Session 1+ untuk user interactive. |
| **Sanitization** | Proses membersihkan data sensitif sebelum dibagikan/diproses oleh pihak ketiga. |
| **UTC** | Coordinated Universal Time. Standar waktu global yang tidak terpengaruh timezone lokal. |
| **Forensik Digital** | Ilmu investigasi insiden security dengan mengumpulkan dan menganalisis bukti digital. |
| **Obfuscated** | Kode/command yang sengaja dibuat sulit dibaca untuk menyembunyikan intent asli. |

---

## Checklist Pemahaman

- [ ] Memahami konsep hash dan SHA256
- [ ] Mengerti 6 fungsi utama hash dalam security
- [ ] Paham limitasi hash (fileless malware, collision)
- [ ] Mengerti kemampuan AI dalam analisis log
- [ ] Paham pentingnya sanitization data sebelum kirim ke AI
- [ ] Mengerti konsep human-in-the-loop
- [ ] Paham manfaat virtual environment
- [ ] Mengerti struktur path instalasi Python di sistem
- [ ] Paham implikasi waktu sistem yang tidak akurat
- [ ] Mengerti informasi sistem yang terungkap di log

---

**Catatan:** Dokumen ini dibuat untuk keperluan pembelajaran dan referensi pribadi. Update berkala seiring perkembangan knowledge.

**Terakhir Update:** 2026-03-08  
**Author:** Raymond (LAPTOP-OJKPVJ0R\user)
