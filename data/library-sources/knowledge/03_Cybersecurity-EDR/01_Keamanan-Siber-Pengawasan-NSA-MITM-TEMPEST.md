---
title: Keamanan Siber & Pengawasan — NSA, MITM, Faraday Cage, TEMPEST
kategori: Cybersecurity & EDR
tags: [keamanan-siber, NSA, MITM, faraday-cage, TEMPEST, pengawasan, SSL-stripping, DNS-spoofing, HSTS, SCIF]
---

# Keamanan Siber & Pengawasan

## Penyadapan Kabel Bawah Laut oleh NSA

### Fakta Terdokumentasi

Penyadapan kabel fiber optik bawah laut oleh NSA adalah **fakta yang terdokumentasi** — bukan teori konspirasi. Dibongkar oleh Edward Snowden pada 2013 dan dikonfirmasi oleh The Guardian, Washington Post, dan media internasional lainnya. The Guardian dan Washington Post memenangkan **Pulitzer Prize 2014** atas liputan ini.

### Program UPSTREAM

Program utama NSA untuk menyadap kabel fiber optik bawah laut secara fisik.

**Cara kerja teknis:**
```
Kabel fiber optik bawah laut
        |
        +-- "Intercept probe" dipasang
        |   (perangkat kecil menggunakan prisma optik)
        |
        +-- Cahaya dari kabel ditangkap prisma
        |
        +-- Salinan dibuat (duplikasi sinyal optik)
        |
        +-- Sinyal asli berlanjut tanpa gangguan
        |
        +-- Salinan dikirim ke NSA untuk dianalisis
```

**Fakta penting:**
- ~99% komunikasi internasional melewati kabel bawah laut
- Data dikumpulkan: email, chat, telepon, browsing history, Facebook, dsb.
- NSA punya akses ke **200+ kabel fiber optik**

### Program PRISM

Selain UPSTREAM (sadap kabel), NSA juga mengakses data langsung dari **server perusahaan teknologi** melalui PRISM.

**Perusahaan yang terlibat (terdokumentasi):**
- Microsoft (termasuk Skype & OneDrive/SkyDrive)
- Google & YouTube
- Facebook
- Yahoo
- Apple
- AOL
- PalTalk

Beberapa perusahaan dibayar oleh NSA untuk menutup biaya teknis keterlibatan mereka.

### Program TEMPORA (Inggris)

GCHQ (intelijen Inggris) menjalankan program Tempora yang bahkan lebih agresif:
- Mengumpulkan **21 juta GB data per hari**
- Menyimpan konten selama 3 hari, metadata 30 hari
- **250 analis NSA + 300 analis GCHQ** memproses data bersama
- Edward Snowden: *"GCHQ lebih parah dari NSA"*

### Skala & Anggaran

- Anggaran black budget NSA: **$52 miliar/tahun** (2013)
- 16 agen intelijen dalam ekosistem yang sama
- Room 641A di gedung AT&T San Francisco: fasilitas sadap NSA yang terbongkar tahun 2006

### Relevansi dengan HTTPS

> Inilah mengapa HTTPS sangat penting. NSA bisa mengambil semua data dari kabel, tapi data terenkripsi HTTPS hanya terlihat sebagai deretan karakter acak tanpa session key. Perfect Forward Secrecy memastikan kunci lama tidak bisa direkonstruksi.

---

## Edward Snowden

### Profil Singkat

| Aspek | Detail |
|-------|--------|
| Nama | Edward Joseph Snowden |
| Lahir | 21 Juni 1983, Elizabeth City, NC, USA |
| Pendidikan | Community college, tidak lulus |
| Karir | CIA (2006), Dell/NSA (2009), Booz Allen Hamilton (2013) |
| Pembocoran | Mei 2013, dari Hong Kong |
| Status | Tinggal di Rusia (suaka permanent) |

### Dampak Pembocoran

- Mengungkap program pengawasan massal global
- Memicu debat publik global tentang privasi vs keamanan
- Beberapa program NSA dinyatakan inkonstitusional oleh pengadilan AS
- Mendorong adopsi enkripsi end-to-end lebih luas (Signal, WhatsApp E2E, dsb.)
- Pulitzer Prize 2014 untuk The Guardian dan Washington Post

---

## Man-in-the-Middle Attack (MITM)

### Definisi

MITM adalah serangan di mana penyerang **menyisipkan diri di antara komunikasi** dua pihak tanpa sepengetahuan keduanya. Penyerang bisa membaca, memodifikasi, dan menyuntikkan data.

```
NORMAL:
Browser <---------------------------------------- Server

DENGAN MITM:
Browser <------ Penyerang ----------------------- Server
               (baca semua data)
```

### Teknik MITM

#### SSL Stripping
```
1. User ketik: google.com (tanpa https)
2. Penyerang intercept request pertama
3. Penyerang konek ke google.com via HTTPS
4. Penyerang reply ke user via HTTP biasa
5. User pikir koneksi normal, padahal tidak terenkripsi
```

**Syarat berhasil**: user harus mengunjungi site pertama kali via HTTP (belum ada HSTS).

#### Fake Certificate
Penyerang membuat sertifikat SSL palsu untuk domain target. Browser akan memperingatkan kecuali:
- User mengabaikan peringatan
- Penyerang sudah menginstall root certificate palsu di perangkat korban

#### DNS Spoofing
```
1. User ketik: bank.com
2. DNS query dikirim
3. Penyerang intercept DNS response
4. Kembalikan IP server palsu
5. User terhubung ke server palsu yang tampilannya identik
```

#### ARP Poisoning (di jaringan lokal)
Di WiFi yang sama, penyerang bisa meracuni ARP table sehingga semua traffic korban melewati perangkat penyerang.

### Perlindungan dari MITM

#### Certificate Authority (CA)
Sertifikat SSL harus diverifikasi oleh CA yang masuk **root store** browser (dikelola oleh Mozilla, Google, Microsoft, Apple). Sertifikat palsu yang tidak ditandatangani CA tepercaya akan ditolak.

#### HSTS (HTTP Strict Transport Security)
```
Header HTTP: Strict-Transport-Security: max-age=31536000; includeSubDomains
```
Browser menyimpan instruksi ini: "Domain ini harus selalu HTTPS." Berlaku bahkan untuk kunjungan berikutnya, mencegah SSL stripping.

#### Certificate Pinning
Aplikasi menyimpan **hash public key server** dalam kode:
```python
# Pseudo-code
expected_pin = "sha256/ABC123..."
actual_pin   = hash(server.certificate.public_key)
if actual_pin != expected_pin:
    REJECT CONNECTION
```
Digunakan oleh aplikasi banking dan sensitif.

#### DANE (DNS-based Authentication of Named Entities)
Verifikasi sertifikat melalui DNSSEC — menambahkan lapisan verifikasi DNS.

### Peringatan Praktis

> **Jangan pernah install sertifikat dari sumber tidak dikenal.** Ini sama saja memberikan izin kepada orang tersebut untuk menyadap semua koneksi HTTPS kamu — termasuk internet banking, email, dan akun media sosial.

---

## Faraday Cage

### Definisi & Sejarah

Faraday Cage (Sangkar Faraday) adalah struktur konduktor logam yang **memblokir medan elektromagnetik** — baik masuk maupun keluar. Ditemukan oleh ilmuwan Inggris **Michael Faraday pada 1836**.

### Prinsip Fisika

Ketika gelombang EM mengenai konduktor:
1. Muatan bebas dalam konduktor bergerak merespons medan eksternal
2. Distribusi muakan menciptakan **medan internal berlawanan**
3. Medan luar dan dalam saling meniadakan (cancel out)
4. Hasil: interior terlindungi dari medan eksternal

### Tipe Faraday Cage

| Tipe | Material | Efektivitas | Contoh |
|------|----------|-------------|--------|
| Solid | Lembaran logam padat | Sangat tinggi | Ruang MRI, SCIF |
| Mesh | Jaring logam | Tinggi (tergantung mesh size) | Pintu microwave |
| Painted | Cat konduktif | Sedang | Ruangan biasa |
| Fabric | Kain EMF-blocking | Rendah-sedang | Pakaian pelindung |

### Aplikasi Nyata

**Militer & Intelijen — Ruangan SCIF:**
Sensitive Compartmented Information Facility. Digunakan CIA, NSA, Kemenhan:
- Dinding berlapis tembaga atau baja
- Tidak ada jendela
- Pintu berperisai berlapis ganda
- Noise generator aktif
- Semua kabel masuk melalui filter EMI

**Medis — Ruang MRI:**
Seluruh ruangan MRI dilapisi tembaga (Faraday cage arsitektur). Mencegah sinyal WiFi, HP, dan radio mengganggu medan magnet 1.5-3 Tesla alat MRI.

**Konsumen — Microwave Oven:**
Jaring logam di pintu kaca microwave adalah Faraday cage. Mencegah gelombang mikro 2.45 GHz bocor keluar — frekuensi yang sama dengan WiFi 2.4GHz.

**Kendaraan:**
Bodi logam mobil, pesawat, dan kapal membentuk Faraday cage alami. Alasan mengapa aman di dalam mobil saat petir — arus mengalir di permukaan logam, bukan masuk ke interior.

**Konsumen — RFID Blocking Wallet:**
Dompet dengan lapisan aluminium mencegah pembaca RFID jarak jauh membaca kartu kredit contactless (VISA Tap, Mastercard Contactless).

### Sinyal yang Bisa & Tidak Bisa Diblokir

| Bisa Diblokir | Tidak Bisa Diblokir |
|----------------|----------------------|
| WiFi (2.4/5 GHz) | Gravitasi |
| 4G/5G cellular | Medan magnet statis (DC) |
| Bluetooth | Neutrino |
| RFID/NFC | Gelombang seismik |
| EMP (Electromagnetic Pulse) | Cahaya (frekuensi terlalu tinggi) |
| Sinyal radio AM/FM | Radiasi gamma (sebagian besar) |

### Faraday Cage vs Enkripsi

| Aspek | Faraday Cage | Enkripsi (HTTPS/AES) |
|-------|-------------|---------------------|
| Jenis proteksi | Fisik | Digital |
| Cara kerja | Blokir sinyal | Acak data |
| Sinyal keluar? | Tidak ada | Keluar tapi tidak terbaca |
| Dapat disadap? | Tidak | Ada ciphertext, tapi tidak bermakna |
| Cocok untuk | Area sensitif tertutup | Komunikasi jarak jauh |

---

## TEMPEST Attack & Van Eck Phreaking

### Definisi

**TEMPEST** adalah nama program rahasia NSA (diklasifikasikan sejak 1960-an) untuk menyadap data dari **emisi elektromagnetik tidak sengaja** yang dipancarkan perangkat elektronik.

**Van Eck Phreaking** adalah teknik spesifik dalam keluarga TEMPEST — rekonstruksi gambar layar monitor dari emisi EM — dipublikasikan oleh Wim van Eck pada 1985.

> Koneksi logis: "Kalau bisa blokir (Faraday), berarti bisa copy juga sebelum diblokir" — ini adalah **logika yang tepat** dan persis dasar pemikiran Van Eck.

### Prinsip — Emisi Tidak Sengaja

Setiap komponen elektronik memancarkan sinyal EM sebagai **efek samping** operasinya:

| Komponen | Frekuensi Emisi | Data yang Bocor |
|----------|----------------|-----------------|
| Monitor VGA | 25-100 MHz | Gambar layar |
| Monitor HDMI | 150-600 MHz | Gambar layar (lebih sulit) |
| Keyboard PS/2 | 1-30 MHz | Keystroke |
| Keyboard USB | 1-15 MHz | Keystroke |
| CPU saat enkripsi | Bervariasi | Kunci kriptografi |
| Kabel data | Bervariasi | Data yang ditransmisi |
| RAM | 200-400 MHz | Data yang diproses |

### Pipeline TEMPEST Attack

```
+-------------+    +-------------+    +-------------+    +-------------+    +-------------+
|   ANTENA    |--->|    SDR      |--->|    FFT      |--->|   FILTER    |--->| REKONSTRUKSI|
|             |    |             |    |             |    |             |    |             |
| Tangkap EM  |    | Digitalisasi|    | Pisahkan    |    | Hilangkan   |    | Rebuild     |
| dari target |    | sinyal      |    | frekuensi   |    | noise       |    | data asli   |
+-------------+    +-------------+    +-------------+    +-------------+    +-------------+
```

**Penjelasan setiap tahap:**

**1. Antena** — menangkap emisi EM lemah dari perangkat target. Bisa antenna directional untuk fokus ke satu target dari jauh, atau wideband untuk tangkap semua frekuensi.

**2. SDR (Software Defined Radio)** — hardware yang mengubah sinyal analog dari antena menjadi data digital. Men-sample sinyal jutaan kali per detik (MSPS).

**3. FFT (Fast Fourier Transform)** — algoritma matematika yang memisahkan campuran banyak frekuensi menjadi komponen individual. Ibarat "memisahkan semua instrumen dari rekaman musik orkestra."

**4. Signal Processing** — filter noise, sinkronisasi timing menggunakan Phase-Locked Loop (PLL), matched filtering.

**5. Rekonstruksi** — untuk monitor VGA: sync pulse digunakan untuk rebuild frame gambar baris per baris. Untuk keyboard: timing dan karakteristik sinyal unik per tombol dicocokkan dengan database.

### Jenis-Jenis TEMPEST Attack

#### Van Eck Phreaking (Monitor)
- Terbukti 1985 oleh Wim van Eck
- Rekonstruksi gambar layar dari jarak **100m+** menggunakan antena + TV biasa
- NSA panik dan meminta paper diklasifikasikan (terlambat)
- Dengan RTL-SDR murah: terbukti kerja di **5-10 meter**

#### Keystroke Emanation (Keyboard)
- Setiap tombol keyboard menghasilkan **sinyal EM unik**
- Perbedaan waktu keystroke + karakteristik sinyal = identifikasi tombol
- Berlaku untuk keyboard kabel maupun wireless

#### Power Analysis Attack (CPU/Chip)
- Fluktuasi konsumsi daya saat proses enkripsi **berbeda tergantung nilai bit**
- Dengan cukup sampel: kunci AES bisa diekstrak
- Terbukti pada smartphone (2011)
- Membutuhkan akses ke jalur power (bisa lewat USB atau power supply)

#### Acoustic Attack (Suara CPU)
- CPU menghasilkan suara frekuensi tinggi (ultrasonic) saat kalkulasi
- **Peneliti Israel (2013)**: ekstrak kunci RSA-4096 hanya dari merekam suara laptop
- Mikrofon biasa dari jarak dekat cukup
- Bahkan smartphone di meja yang sama bisa digunakan

#### Cold Boot Attack (RAM)
- Kunci enkripsi tersisa di RAM **beberapa detik hingga menit** setelah power off
- Semprot RAM dengan nitrogen cair (-196 C): data tahan **beberapa jam**
- Lepas RAM, pindah ke komputer lain, dump isinya
- Kunci enkripsi disk (BitLocker, VeraCrypt) bisa dicuri

### Hardware untuk TEMPEST

| Hardware | Harga | Frekuensi | Kemampuan |
|----------|-------|-----------|-----------|
| RTL-SDR V4 (dongle USB) | ~$25 | 24 MHz-1.8 GHz | VGA, keyboard PS/2 |
| HackRF One | ~$300 | 1 MHz-6 GHz | HDMI, keyboard USB, lebih banyak target |
| USRP B200 (Ettus) | ~$1.000 | 70 MHz-6 GHz | Lab penelitian profesional |
| Perangkat NSA/militer | Diklasifikasikan | Ultra-wideband | Jarak ratusan meter, AI filtering |

### Software Open Source

```bash
# TempestSDR — rekonstruksi gambar monitor
git clone https://github.com/martinmarinov/TempestSDR

# GNU Radio — platform signal processing
sudo apt install gnuradio

# inspectrum — visualisasi dan analisis sinyal
sudo apt install inspectrum
```

### VGA vs HDMI vs DisplayPort — Ketahanan TEMPEST

| Interface | Frekuensi | Ketahanan | Tool Minimum |
|-----------|-----------|-----------|-------------|
| VGA | 25-100 MHz | Sangat lemah | RTL-SDR $25 |
| HDMI | 150-600 MHz | Sedang | HackRF $300 |
| DisplayPort | Wideband | Lebih baik | Hardware mahal |

DisplayPort menggunakan **spread spectrum signaling** — emisi tersebar ke banyak frekuensi sekaligus, sehingga sulit difokuskan dan direkonstruksi.

### Ruangan SCIF — Perlindungan Berlapis

Fasilitas intelijen menggabungkan **semua lapisan perlindungan**:

```
Lapisan 1: Lokasi (basement, tidak ada jendela)
Lapisan 2: Faraday cage arsitektur (tembaga/baja di dinding, lantai, langit-langit)
Lapisan 3: TEMPEST-certified hardware (emisi minimal by design)
Lapisan 4: Noise generator aktif (tenggelamkan emisi yang tersisa)
Lapisan 5: Enkripsi end-to-end untuk semua data yang keluar
Lapisan 6: Air gap (tidak terhubung internet publik)
Lapisan 7: Prosedur operasi (no phones, no wireless devices)
```

### Kontra-TEMPEST

| Metode | Efektivitas | Biaya | Keterangan |
|--------|------------|-------|------------|
| TEMPEST-certified hardware | Sangat tinggi | Sangat mahal | MIL-STD-461, NATO SDIP-27 |
| Faraday cage (perangkat) | Tinggi | Sedang | Harus melingkupi seluruh perangkat |
| Noise generator | Tinggi | Sedang | Pancarkan noise EM untuk ganggu sadap |
| Jarak fisik | Sedang | Gratis | Sinyal melemah kuadrat jarak |
| DisplayPort vs VGA/HDMI | Sedang | Minimal | Ganti kabel/monitor |
| Enkripsi full-disk | Rendah | Gratis | Hanya bantu untuk cold boot |

---

## Topik Pendukung Keamanan

### DNS Spoofing
Manipulasi response DNS untuk mengarahkan pengguna ke server palsu. Dapat dikombinasikan dengan fake SSL certificate untuk serangan phishing yang sulit dideteksi.

**Perlindungan**: DNSSEC, HTTPS (verifikasi sertifikat), HSTS preloading.

### HSTS (HTTP Strict Transport Security)
Header HTTP yang menginstruksikan browser untuk **selalu** menggunakan HTTPS untuk domain tertentu, bahkan setelah browser restart.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

Browser menyimpan instruksi ini secara lokal. Domain populer (google.com, facebook.com, dsb.) sudah di-hardcode dalam **HSTS preload list** yang di-bundle dalam browser.

### Certificate Pinning
Teknik menyimpan hash public key server yang sah di dalam kode aplikasi. Digunakan oleh:
- Aplikasi perbankan
- Aplikasi pemerintah
- Email client seperti Gmail
- Aplikasi dengan data sangat sensitif
