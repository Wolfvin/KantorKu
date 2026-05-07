---
title: OS-Level Monitoring & EDR — Kernel, Sysmon, Osquery, ETW
kategori: Cybersecurity & EDR
tags: [EDR, kernel, sysmon, osquery, ETW, system-call, monitoring, Python, AI-lokal, Ollama]
---

# OS-Level Monitoring & EDR: Panduan Pemula

## Ringkasan Eksekutif (TL;DR)

```
IDE INTI:
Daripada membongkar aplikasi satu-per-satu (ribet & berisiko),
pantau saja "jantung" sistem operasi: KERNEL.

Semua aplikasi WAJIB lewat kernel untuk:
- Akses file  - Koneksi jaringan  - Buat proses  - Ubah registry

Monitor kernel = Monitor SEMUA aplikasi sekaligus.
```

---

## Daftar Isi

1. Konsep Dasar: Kenapa OS Level?
2. Apa Itu EDR?
3. Tools Utama: The Big Three
4. Contoh Praktis: Sysmon + Python
5. Integrasi AI Lokal
6. Checklist Pemahaman
7. Ringkasan Per Bagian
8. Glossary

---

## Konsep Dasar: Kenapa OS Level?

### Analogi Sederhana

```
Bayangkan gedung perkantoran:

- Aplikasi = Karyawan di dalam ruangan
- Kernel = Satpam di lobi utama

Mau tahu siapa keluar-masuk?
Jangan intip tiap ruangan (RE aplikasi) -> ribet & dilarang
Cukup pantau lobi (kernel) -> legal & lengkap!
```

### System Calls = "Pintu Wajib"

Semua aplikasi, mau Excel, Chrome, atau malware, kalau mau:
- Baca/tulis file -> `NtCreateFile`, `NtWriteFile`
- Koneksi internet -> `NtConnect`, `NtSend`
- Buat proses baru -> `NtCreateProcess`
- Akses registry -> `NtSetValueKey`

**WAJIB** memanggil **System Call** ke Kernel Windows.

> **Insight:** Kernel adalah *single source of truth*. Tidak ada aplikasi yang bisa "loncat" lewat kernel.

### Keuntungan Monitoring OS Level

| Keuntungan | Penjelasan |
|------------|------------|
| Legal | Memantau sistem sendiri = hak penuh user |
| Stabil | Tidak bergantung pada versi aplikasi tertentu |
| Universal | Bekerja untuk SEMUA aplikasi (bahkan yang tidak dikenal) |
| Deteksi Perilaku | Fokus pada *apa yang dilakukan*, bukan *siapa aplikasinya* |
| Sulit Dielakkan | Malware pun harus panggil syscall (kecuali pakai teknik advanced) |

---

## Apa Itu EDR?

### Definisi Singkat

**EDR (Endpoint Detection and Response)** = Sistem keamanan yang:
1. **Mengumpulkan** data aktivitas endpoint (laptop/server)
2. **Mendeteksi** perilaku mencurigakan secara real-time
3. **Merespons** otomatis terhadap ancaman

### Alur Kerja EDR Sederhana

```
User/App Action --> Kernel/System Call --> Monitoring Tool (Sysmon/ETW/Osquery)
    --> Log/Event Data --> AI/Analysis Engine --> Normal? (catat saja) / Tidak Normal? (Alert + Response)
```

### Contoh Deteksi EDR

| Perilaku Mencurigakan | Kemungkinan Ancaman |
|----------------------|---------------------|
| `powershell.exe` spawn dari `winword.exe` | Macro malware / Office exploit |
| Proses akses `lsass.exe` memory | Credential dumping (Mimikatz) |
| Koneksi ke IP asing + encrypt data | Data exfiltration / ransomware |
| Registry run key dimodifikasi | Persistence mechanism |

---

## Tools Utama: The Big Three

### 1. Sysmon (System Monitor) — Rekomendasi Pemula

```
Asal: Microsoft Sysinternals (Gratis)
Cara Kerja: Driver kernel -> Windows Event Log
Output: Structured logs (Event ID based)
```

**Event ID Penting untuk Pemula:**

| Event ID | Nama | Contoh Penggunaan |
|----------|------|------------------|
| `1` | Process Creation | Deteksi aplikasi baru jalan |
| `3` | Network Connection | Lihat koneksi keluar/masuk |
| `11` | File Create | Pantau file mencurigakan dibuat |
| `13` | Registry Value Set | Deteksi perubahan konfigurasi |
| `22` | DNS Query | Lihat domain yang diakses |

**Install Cepat (Admin PowerShell):**
```powershell
# 1. Download Sysmon + config
# 2. Install dengan config terbaik
.\sysmon.exe -i -accepteula -c sysmonconfig-export.xml

# 3. Cek status
Get-Service sysmon  # Harus: Status = Running
```

**Lihat Log:**
- Buka `eventvwr.msc`
- Navigasi: `Applications and Services Logs` -> `Microsoft` -> `Windows` -> `Sysmon` -> `Operational`

---

### 2. Osquery: "SQL untuk Sistem Operasi"

```
Asal: Meta (Open Source)
Konsep: Query sistem seperti database SQL
Keunggulan: Output terstruktur (JSON/table), mudah diproses AI
```

**Contoh Query Praktis:**
```sql
-- Lihat semua proses yang sedang jalan
SELECT name, pid, path, cmdline FROM processes;

-- Lihat koneksi jaringan aktif
SELECT local_address, remote_address, pid, state 
FROM process_open_sockets 
WHERE remote_port != 0;

-- Deteksi proses yang jalan dari folder temp (mencurigakan!)
SELECT name, path FROM processes 
WHERE path LIKE '%Temp%' OR path LIKE '%AppData%';

-- Cek auto-start programs (persistence)
SELECT name, path FROM startup_items;
```

**Jalankan Query via CLI:**
```bash
osqueryi "SELECT name, pid FROM processes WHERE name LIKE '%powershell%';"
```

---

### 3. Windows ETW (Event Tracing for Windows)

```
Asal: Native Windows (Built-in)
Level: Lebih dalam dari Sysmon (bisa trace API calls)
Kompleksitas: Advanced
```

**Kapan Pakai ETW?**
- Butuh detail sangat granular (misal: trace fungsi spesifik)
- Performance monitoring real-time
- Tidak untuk pemula (butuh tools tambahan seperti `logman`, `tracerpt`, atau `ETWSharp`)

**Contoh Sederhana via PowerShell:**
```powershell
# Start trace session (butuh admin)
logman create trace MyTrace -o C:\trace.etl -p Microsoft-Windows-Kernel-Process
logman start MyTrace

# ... lakukan aktivitas ...

logman stop MyTrace
# Convert ke readable format
tracerpt C:\trace.etl -o output.xml
```

> **Tips Pemula:** Fokus ke **Sysmon** dulu. ETW bisa dipelajari nanti kalau sudah nyaman.

---

## Contoh Praktis: Sysmon + Python

### Skenario

> "Saya ingin script Python yang membaca log Sysmon secara real-time, lalu mengirim event mencurigakan ke AI lokal untuk dianalisis."

### Persiapan

```bash
# 1. Buat virtual environment (opsional tapi disarankan)
python -m venv .venv
.venv\Scripts\activate  # Windows

# 2. Install library yang dibutuhkan
pip install wmi pywin32 requests
```

### Script: `sysmon_monitor.py`

```python
import wmi
import time
import json
from datetime import datetime

# Konfigurasi: Event ID yang ingin dipantau
INTERESTING_EVENTS = ['1', '3', '11']  # Process, Network, File

def format_sysmon_event(event):
    """Format event Sysmon jadi dict yang rapi"""
    return {
        "timestamp": event.TargetInstance.EventTime,
        "event_id": event.TargetInstance.EventId,
        "computer": event.TargetInstance.Computer,
        "record_id": event.TargetInstance.RecordId,
        "message": event.TargetInstance.Message,  # Detail lengkap
        # Bisa parse message jadi field terpisah kalau mau lebih rapi
    }

def send_to_local_ai(event_data):
    """Kirim event ke Ollama (LLM lokal) untuk analisis"""
    prompt = f"""
    Kamu adalah asisten keamanan siber. Analisis log Sysmon berikut:
    
    Event ID: {event_data['event_id']}
    Waktu: {event_data['timestamp']}
    Detail: {event_data['message'][:500]}  # Potong biar tidak terlalu panjang
    
    Pertanyaan:
    1. Apakah ini aktivitas normal atau mencurigakan?
    2. Jika mencurigakan, apa kemungkinan ancamannya?
    3. Rekomendasi tindakan?
    
    Jawab singkat, pakai poin-poin.
    """
    
    # Contoh call ke Ollama (pastikan Ollama running di localhost:11434)
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",  # Ganti dengan model yang kamu pakai
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json().get('response', 'Gagal dapat respons AI')
    except Exception as e:
        return f"Error connect ke AI: {e}"

def monitor():
    print("Memulai Sysmon Monitor... (Ctrl+C untuk stop)")
    print(f"Memantau Event ID: {INTERESTING_EVENTS}\n")
    
    # Koneksi ke WMI namespace Sysmon
    c = wmi.WMI(namespace="root\\Microsoft\\Windows\\Sysmon")
    
    # Watcher: polling tiap 2 detik untuk event baru
    watcher = c.watch_for(
        raw_wql="SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'SysmonEvent'"
    )
    
    try:
        while True:
            event = watcher()  # Blocking: nunggu event baru
            
            # Filter hanya event yang kita minati
            if event.TargetInstance.EventId not in INTERESTING_EVENTS:
                continue
                
            # Format & tampilkan
            evt = format_sysmon_event(event)
            print(f"\n[{evt['event_id']}] {evt['timestamp']}")
            print(f"Preview: {evt['message'][:150]}...")
            
            # Kirim ke AI untuk analisis (opsional, bisa di-toggle)
            # Uncomment baris bawah kalau mau aktif:
            # print("Menganalisis dengan AI...")
            # analysis = send_to_local_ai(evt)
            # print(f"Hasil AI:\n{analysis}")
            
    except KeyboardInterrupt:
        print("\nMonitoring dihentikan oleh user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Pastikan: 1) Sysmon running, 2) Jalankan sebagai Admin")

if __name__ == "__main__":
    monitor()
```

### Cara Testing

```powershell
# 1. Jalankan script (sebagai Admin!)
python sysmon_monitor.py

# 2. Di terminal lain, trigger event:
ping google.com              # -> Harus muncul Event ID 3
notepad.exe                  # -> Harus muncul Event ID 1
echo "test" > C:\test.txt    # -> Harus muncul Event ID 11

# 3. Lihat output script: event baru muncul real-time!
```

---

## Integrasi AI Lokal

### Kenapa Harus Lokal?

```
Cloud API (OpenAI, dll):
   - Log kernel = data sensitif (proses, file, jaringan)
   - Risiko kebocoran privasi / compliance issue

Local LLM (Ollama, LM Studio, dll):
   - Data tetap di laptop Anda
   - Bisa jalan offline
   - Gratis & unlimited query
```

### Setup Ollama (5 Menit)

```powershell
# 1. Download & install: https://ollama.com

# 2. Pull model (pilih sesuai RAM):
ollama pull llama3          # ~4.7GB, balanced
# atau
ollama pull phi3            # ~2.3GB, ringan
# atau  
ollama pull mistral         # ~4.1GB, bagus untuk reasoning

# 3. Test cepat:
ollama run llama3 "Halo, kamu siap bantu analisis keamanan?"

# 4. API ready di: http://localhost:11434
```

### Prompt Engineering untuk Security Log

```python
# Template prompt yang efektif:
SECURITY_ANALYSIS_PROMPT = """
Kamu adalah SOC Analyst Level 1. Tugasmu: analisis log keamanan.

FORMAT LOG: {log_format}
LOG DATA:
{log_content}

INSTRUKSI:
1. Identifikasi ENTITAS: proses, user, IP, file, registry
2. Klasifikasi: Normal / Suspicious / Malicious
3. Jika suspicious/malicious:
   - Jelaskan WHY (indikator apa yang mencurigakan?)
   - Sebutkan POSSIBLE ATTACK (misal: lateral movement, C2, etc.)
   - Berikan RECOMMENDED ACTION (1-3 langkah praktis)
4. Gunakan bahasa Indonesia, poin-poin, maksimal 10 baris.

JAWABAN:
"""
```

---

## Checklist Pemahaman

Centang kalau sudah paham:

- [ ] **Konsep**: Saya mengerti kenapa kernel adalah "single source of truth"
- [ ] **EDR**: Saya bisa jelaskan EDR dengan analogi sendiri
- [ ] **Sysmon**: Saya sudah install & lihat log di Event Viewer
- [ ] **Event ID**: Saya hafal minimal 3 Event ID penting (1, 3, 11)
- [ ] **Python**: Script `sysmon_monitor.py` berhasil jalan di laptop saya
- [ ] **AI Lokal**: Ollama terinstall & bisa jawab query sederhana
- [ ] **Privasi**: Saya paham kenapa analisis log sensitif harus lokal
- [ ] **Next Step**: Saya tahu apa yang mau saya coba selanjutnya: _________

> **Tips:** Jangan centang asal! Coba praktekin dulu tiap poin.

---

## Ringkasan Per Bagian

### Konsep OS-Level Monitoring

```
- Kernel = pintu wajib semua aplikasi
- System Calls = jejak digital yang tidak bisa dihindari
- Monitor kernel = deteksi semua aplikasi, legal & stabil
```

### EDR Fundamentals

```
- EDR = Collect -> Detect -> Respond
- Fokus pada BEHAVIOR, bukan signature
- Contoh deteksi: process injection, suspicious network, registry persistence
```

### Tools Comparison

| Tool | Level | Pemula? | Output | Best For |
|------|-------|---------|--------|----------|
| **Sysmon** | Kernel -> Event Log | Sangat cocok | Structured logs | Mulai di sini! |
| **Osquery** | OS Abstraction | Cukup cocok | SQL/Table/JSON | Query fleksibel, AI-friendly |
| **ETW** | Kernel/API Trace | Advanced | Raw trace data | Deep forensic, performance |

### Python Integration

```
- Gunakan `wmi` untuk baca Sysmon via WMI
- Filter Event ID dulu sebelum kirim ke AI (hemat resource)
- Format log jadi JSON/poin sebelum ke LLM
- Selalu handle exception (Admin rights, service down, dll)
```

### AI Lokal Best Practice

```
- Pakai Ollama/LM Studio untuk privasi
- Pilih model sesuai RAM (phi3 untuk <8GB, llama3 untuk >=16GB)
- Craft prompt spesifik: role + format + instruksi jelas
- Batasi panjang input log (potong message kalau terlalu panjang)
```

---

## Glossary

| Istilah | Definisi Sederhana | Contoh |
|---------|-------------------|--------|
| **Kernel** | Inti sistem operasi; pengatur akses hardware & resource | Windows NT Kernel, Linux Kernel |
| **System Call (Syscall)** | Permintaan aplikasi ke kernel untuk layanan sistem | `NtCreateFile`, `NtConnect` |
| **EDR** | Endpoint Detection and Response: sistem deteksi ancaman berbasis perilaku | CrowdStrike, SentinelOne, atau homemade Sysmon+AI |
| **Sysmon** | Tool Microsoft untuk logging aktivitas sistem detail | Event ID 1 = proses baru dibuat |
| **Event ID** | Kode numerik yang mengidentifikasi jenis log di Windows | `3` = Network Connection |
| **WMI** | Windows Management Instrumentation: interface query info sistem | `Get-Service`, `SELECT * FROM Win32_Process` |
| **ETW** | Event Tracing for Windows: framework tracing performa & debug | Trace API calls, CPU usage |
| **Osquery** | Tool yang expose OS sebagai database SQL relasional | `SELECT * FROM processes WHERE name='powershell.exe'` |
| **LLM Lokal** | Large Language Model yang jalan di laptop sendiri, tanpa internet | Llama 3 via Ollama, Phi-3, Mistral |
| **Ollama** | Tool untuk download & run LLM lokal dengan mudah | `ollama run llama3` |
| **Persistence** | Teknik malware untuk tetap ada setelah reboot | Registry Run key, Scheduled Task |
| **Lateral Movement** | Pergerakan attacker dari satu mesin ke mesin lain dalam jaringan | Pass-the-Hash, SMB exploit |
| **C2 (Command & Control)** | Server yang dikontrol attacker untuk perintah malware | Domain `evil[.]com`, IP `1.2.3.4` |
| **IOC (Indicator of Compromise)** | Jejak digital yang menandakan serangan | Hash malware, IP mencurigakan, registry key aneh |

---

Last Updated: 2026-03-08  
Next Review: 2026-03-15 (cek progress checklist)

*Stay curious, stay legal, stay secure.*
