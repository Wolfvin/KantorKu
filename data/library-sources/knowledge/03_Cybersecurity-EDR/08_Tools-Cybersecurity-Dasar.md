---
title: Pengenalan Tools Cybersecurity Dasar — Nmap, Wireshark, Burp Suite, Yara, Ghidra
kategori: Cybersecurity & EDR
tags: [nmap, wireshark, burp-suite, yara, ghidra, network-scanner, packet-analyzer, reverse-engineering, OSINT]
---

# Pengenalan Tools Cybersecurity Dasar

> **Topik:** Nmap, Ghidra, Yara, Wireshark, Burp Suite
> **Level:** Pemula ke Menengah
> **Tujuan:** Belajar pribadi / Referensi cepat

---

## Checklist Pemahaman

- [ ] Paham fungsi utama masing-masing tools
- [ ] Tahu kapan menggunakan tools yang tepat
- [ ] Mengerti konteks legal & etika penggunaan
- [ ] Bisa menyebutkan 1 contoh praktis per tools
- [ ] Paham perbedaan kategori: *Network*, *Binary*, *Web*

---

## Ringkasan Eksekutif

| Tools | Kategori | Fungsi Utama | Level Kesulitan |
|-------|----------|-------------|-----------------|
| **Nmap** | Network Scanner | Discovery & port scanning | Pemula |
| **Wireshark** | Packet Analyzer | Capture & analisis traffic jaringan | Menengah |
| **Burp Suite** | Web Proxy | Testing keamanan aplikasi web | Menengah |
| **Yara** | Pattern Matcher | Identifikasi malware berbasis rule | Menengah |
| **Ghidra** | Reverse Engineering | Dekompilasi & analisis binary | Lanjut |

> **Quick Take:** Kelima tools ini adalah "kotak perkakas wajib" bagi *Security Analyst*. Masing-masing punya domain spesifik: jaringan, paket, web, malware, atau binary.

---

## Nmap (Network Mapper)

### Fungsi Utama

- **Network Discovery:** Menemukan device aktif dalam jaringan
- **Port Scanning:** Mengecek port mana yang terbuka/tertutup
- **Service Detection:** Mengidentifikasi versi service yang berjalan
- **OS Fingerprinting:** Menebak sistem operasi target

### Contoh Praktis (Konteks Security Monitoring)

```bash
# Scan dasar: cek host aktif & port terbuka
nmap -sV 192.168.1.100

# Scan stealth (tidak meninggalkan log besar)
nmap -sS -T4 target.com

# Deteksi OS + version + script default
nmap -A 192.168.1.0/24

# Export hasil ke format grep-friendly (untuk diproses Python)
nmap -oG scan_result.txt 192.168.1.100
```

### Integrasi Python (Untuk AI Agent)

```python
import nmap

def scan_target(ip):
    nm = nmap.PortScanner()
    nm.scan(ip, arguments='-sV -T4')
    
    for host in nm.all_hosts():
        print(f"Host: {host} ({nm[host].hostname()})")
        for proto in nm[host].all_protocols():
            ports = nm[host][proto].keys()
            for port in ports:
                print(f"  Port {port}: {nm[host][proto][port]['state']}")

# Contoh: Monitor device baru di jaringan lokal
scan_target('192.168.1.0/24')
```

### Peringatan Etika

- Legal: Scan jaringan milik sendiri / dengan izin tertulis
- Ilegal: Scan server orang lain tanpa izin (bisa kena UU ITE)

### Ringkasan Nmap

> Nmap adalah "mata" pertama dalam reconnaissance. Gunakan untuk memetakan attack surface sebelum analisis lebih dalam.

---

## Wireshark

### Fungsi Utama

- **Packet Capture:** Menangkap semua lalu lintas jaringan di interface
- **Protocol Analysis:** Mendekode ratusan protokol (HTTP, DNS, TLS, dll)
- **Filtering:** Menyaring paket dengan display filter yang powerful
- **Forensics:** Investigasi insiden keamanan berbasis network traffic

### Contoh Praktis (Konteks Sysmon Correlation)

```
# Display Filter Wireshark untuk investigasi:

# Lihat hanya traffic HTTP ke IP tertentu
http && ip.dst == 192.168.1.50

# Filter DNS query yang mencurigakan
dns.qry.name contains "evil"

# Lacak stream TCP dari process PID tertentu (butuh tshark + Sysmon correlation)
tcp.stream eq 123

# Export objek yang di-download via HTTP
File -> Export Objects -> HTTP
```

### Integrasi Python (via PyShark)

```python
import pyshark

def analyze_pcap(file_path):
    cap = pyshark.FileCapture(file_path, display_filter='http')
    
    suspicious_patterns = ['password', 'token', 'admin']
    
    for packet in cap:
        if hasattr(packet, 'http'):
            for pattern in suspicious_patterns:
                if pattern in str(packet.http).lower():
                    print(f"Potensi data sensitif terbocor: {pattern}")
                    print(f"   Source: {packet.ip.src} -> {packet.ip.dst}")
    cap.close()

# Cocok untuk analisis log network dari Sysmon Event ID 3
analyze_pcap('capture.pcapng')
```

### Peringatan Etika

- Legal: Capture traffic di jaringan sendiri / dengan izin
- Ilegal: Sniffing jaringan publik/WiFi orang lain tanpa izin

### Ringkasan Wireshark

> Wireshark adalah "rekorder" jaringan. Berguna untuk investigasi insiden, debugging aplikasi, atau mendeteksi anomali traffic.

---

## Burp Suite

### Fungsi Utama

- **Proxy Intercept:** Memotong & memodifikasi request/response HTTP(S)
- **Scanner:** Automated vulnerability scanning (XSS, SQLi, dll)
- **Repeater:** Mengulang request dengan modifikasi manual
- **Intruder:** Automated attack untuk fuzzing & brute-force

### Contoh Praktis (Konteks Web App Monitoring)

```
# Workflow deteksi hidden API endpoint:

1. Configure browser proxy -> 127.0.0.1:8080 (Burp)
2. Install CA certificate Burp di browser (untuk intercept HTTPS)
3. Jalankan aplikasi web, Burp akan capture semua request
4. Cari endpoint tidak terdokumentasi:
   - /api/internal/*
   - /debug/*
   - /admin/* (tanpa auth)
5. Gunakan Repeater untuk testing parameter manipulation
```

### Integrasi Python (via Burp Extensions API)

```python
# Contoh Burp Extension (Jython) untuk auto-flag suspicious request
from burp import IScannerCheck, IExtensionHelpers

class HiddenAPIDetector(IScannerCheck):
    def doPassiveScan(self, baseRequestResponse):
        helpers = self._callbacks.getHelpers()
        url = helpers.analyzeRequest(baseRequestResponse).getUrl().toString()
        
        # Flag endpoint yang mengandung kata kunci mencurigakan
        suspicious_keywords = ['internal', 'debug', 'backup', 'test']
        if any(kw in url.lower() for kw in suspicious_keywords):
            return [self._callbacks.applyMarkers(
                baseRequestResponse, None, 
                [helpers.bytesToString(baseRequestResponse.getResponse()).find('internal')]
            )]
        return None
```

### Peringatan Etika

- Legal: Testing aplikasi web milik sendiri / program bug bounty resmi
- Ilegal: Scanning website orang lain tanpa izin tertulis

### Ringkasan Burp Suite

> Burp adalah "laboratorium" untuk web security. Wajib untuk memahami bagaimana aplikasi web berkomunikasi dan di mana celahnya.

---

## Yara

### Fungsi Utama

- **Pattern Matching:** Mendeteksi malware berdasarkan signature/text/byte pattern
- **Rule-Based:** Menggunakan bahasa rule yang fleksibel
- **Cross-Platform:** Bisa scan file, memory, atau proses running
- **Threat Intelligence:** Berbagi rule deteksi dengan komunitas

### Contoh Praktis (Konteks Malware Detection di Sysmon Logs)

```yara
// Rule Yara: Deteksi potensi PowerShell-based malware
rule PowerShell_Suspicious_Download {
    meta:
        description = "Detects PowerShell downloading from suspicious TLD"
        author = "Raymond"
        date = "2026-01-09"
    
    strings:
        $ps1 = "powershell" nocase
        $download = "DownloadString" nocase
        $susp_tld = /https?:\/\/[^\s]+\.(tk|ml|ga|cf|gq)/
    
    condition:
        $ps1 and $download and $susp_tld
}
```

### Integrasi Python (Scan File dengan Yara)

```python
import yara

# Compile rule
rule = yara.compile(source='''
rule Suspicious_Process_Name {
    strings:
        $name = /svch0st|lsass\.exe|csrss\.exe/ nocase
    condition:
        $name
}
''')

# Scan file atau string (misal: dari Sysmon Event ID 1 - Process Create)
def scan_process_name(process_name):
    matches = rule.match(data=process_name)
    if matches:
        print(f"Nama process mencurigakan: {process_name}")
        for m in matches:
            print(f"   Rule matched: {m.rule}")
    return matches

# Contoh: Monitor process creation dari Sysmon
scan_process_name('C:\\Windows\\svch0st.exe')  # Typo intentional = suspicious
```

### Peringatan Etika

- Legal: Scan file milik sendiri / riset malware di lingkungan terisolasi
- Ilegal: Menyebar rule yang menargetkan software legal tanpa dasar

### Ringkasan Yara

> Yara adalah "sidik jari digital" untuk malware. Rule-based, fleksibel, dan komunitas-driven.

---

## Ghidra

### Fungsi Utama

- **Disassembler:** Mengubah binary machine code ke assembly
- **Decompiler:** Menghasilkan pseudocode mirip C dari binary
- **Scripting:** Otomasi analisis via Python/Java
- **Collaboration:** Multi-user reverse engineering project

### Contoh Praktis (Konteks Analisis Binary Sederhana)

```
# Workflow dasar Ghidra untuk pemula:

1. Import file .exe -> Ghidra akan auto-analyze
2. Buka "Symbol Tree" -> lihat fungsi yang di-export
3. Klik fungsi -> lihat Assembly (kiri) & Decompiler (kanan)
4. Cari string menarik: Search -> For Strings -> "password", "api", "key"
5. Gunakan Script Manager untuk otomasi (Python)
```

### Integrasi Python (Ghidra Scripting)

```python
# Ghidra script (Python) untuk list semua fungsi yang memanggil API jaringan
# Simpan sebagai: FindNetworkCalls.py

from ghidra.program.model.symbol import RefType

def find_network_api_calls():
    # List API Windows yang terkait jaringan
    network_apis = ['WSAStartup', 'connect', 'send', 'recv', 'InternetOpen']
    
    for func_name in network_apis:
        symbols = getGlobalSymbols(func_name)
        for sym in symbols:
            print(f"Found API: {func_name} at {sym.getAddress()}")
            # Cari siapa yang memanggil API ini
            refs = getReferencesTo(sym.getAddress())
            for ref in refs:
                print(f"   <- Called by: {ref.getFromAddress()}")

find_network_api_calls()
```

### Peringatan Etika

- Legal: Analisis binary milik sendiri / open source / dengan izin
- Ilegal: Reverse engineering software proprietary melanggar EULA (Excel, Adobe, dll)

### Ringkasan Ghidra

> Ghidra adalah "mikroskop" untuk binary. Powerful tapi butuh belajar assembly & konsep low-level.

---

## Perbandingan & Kapan Pakai Apa

### Decision Tree Cepat

| Saya ingin... | Gunakan Tools |
|--------------|---------------|
| Tahu device apa saja di jaringan | **Nmap** |
| Lihat isi paket data yang lewat | **Wireshark** |
| Testing celah website | **Burp Suite** |
| Deteksi file malware berdasarkan pola | **Yara** |
| Bedah cara kerja file .exe | **Ghidra** |
| Monitoring sistem + AI analysis | **Sysmon + Python + LLM** |

### Kategori Target

```
Target Analisis --> Jaringan?       --> Nmap + Wireshark
                --> Aplikasi Web?  --> Burp Suite
                --> File/Binary?   --> Ghidra
                --> Malware?       --> Yara + Ghidra

Output: Log/Packet | HTTP Request | Assembly/Pseudocode | Rule Match
         |
         v
    AI Analysis Layer
```

---

## Setup Environment (Python + Tools)

```bash
# 1. Buat virtual environment (pilih salah satu)
python -m venv .venv
# atau
conda create -n security-tools python=3.11

# 2. Aktifkan
.venv\Scripts\activate  # Windows venv
# atau
conda activate security-tools

# 3. Install library pendukung
pip install python-nmap pyshark yara-python requests wmi pywin32

# 4. Download tools (manual)
# - Nmap: https://nmap.org/download
# - Wireshark: https://www.wireshark.org/download
# - Burp: https://portswigger.net/burp/communitydownload
# - Ghidra: https://ghidra-sre.org/
# - Yara: https://virustotal.github.io/yara/

# 5. Simpan dependencies
pip freeze > requirements.txt
```

---

## Glossary (Istilah Teknis)

| Istilah | Penjelasan Singkat |
|---------|-------------------|
| **Reconnaissance** | Tahap pengumpulan informasi awal tentang target |
| **Port Scanning** | Teknik mengecek port jaringan yang terbuka pada sebuah host |
| **Packet Sniffing** | Proses menangkap dan menganalisis paket data yang lewat di jaringan |
| **Man-in-the-Middle (MitM)** | Serangan dimana penyerang menyadap komunikasi antara dua pihak |
| **Reverse Engineering** | Proses menganalisis produk untuk memahami cara kerjanya, biasanya dari binary ke source-like code |
| **Disassembler** | Tools yang mengubah machine code menjadi assembly language |
| **Decompiler** | Tools yang mencoba menghasilkan high-level code (seperti C) dari binary |
| **Signature-Based Detection** | Metode deteksi malware berdasarkan pola/byte sequence yang sudah dikenal |
| **Syscall (System Call)** | Permintaan program ke kernel OS untuk layanan seperti akses file, jaringan, dll |
| **EULA** | End User License Agreement: kontrak legal penggunaan software |
| **CVE** | Common Vulnerabilities and Exposures: database publik untuk kerentanan keamanan |
| **IoC** | Indicator of Compromise: artefak yang menandakan sistem telah dikompromi |
| **EDR** | Endpoint Detection and Response: sistem keamanan yang memantau & merespons ancaman di endpoint |
| **Pseudocode** | Kode mirip bahasa pemrograman tinggi yang dihasilkan decompiler, bukan source code asli |
| **Hooking** | Teknik intercepting function calls untuk memantau atau memodifikasi perilaku program |

---

## Ringkasan Akhir

### 5 Tools Cybersecurity Dasar dalam 1 Kalimat

- **Nmap**: "Si Pemeta" — scan jaringan & port
- **Wireshark**: "Si Perekam" — tangkap & baca paket
- **Burp Suite**: "Si Penguji Web" — intercept & exploit HTTP
- **Yara**: "Si Pemburu Malware" — deteksi berbasis rule
- **Ghidra**: "Si Pembongkar Binary" — RE & decompile

Kunci: Pilih tools sesuai target, selalu patuhi etika & legalitas.

---

## Update Log

| Tanggal | Perubahan |
|---------|-----------|
| 2026-01-09 | Dokumen awal dibuat, mencakup 5 tools dasar + integrasi Python |

> **Catatan Pribadi:**
> *"Tools hanyalah alat. Yang membedakan hacker etis dan kriminal adalah **niat** dan **izin**. Selalu dokumentasikan scope sebelum testing."*

---

*Document generated for personal learning purposes. Always verify legal compliance before using security tools in production environments.*
