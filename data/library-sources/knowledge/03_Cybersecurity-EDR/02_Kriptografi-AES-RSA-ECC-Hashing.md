---
title: Kriptografi — AES, RSA, ECC, Hashing, Side-Channel Attacks
kategori: Cybersecurity & EDR
tags: [kriptografi, AES-256, RSA, ECC, hashing, bcrypt, argon2, side-channel, CSPRNG, session-key, PFS]
---

# Kriptografi

## Enkripsi AES-256

### Definisi & Posisi

AES (Advanced Encryption Standard) adalah **algoritma enkripsi simetris** yang ditetapkan NIST pada 2001 setelah kompetisi 5 tahun. AES-256 menggunakan kunci 256-bit dan merupakan standar enkripsi yang digunakan oleh pemerintah AS untuk data TOP SECRET, militer global, dan industri teknologi.

### Enkripsi Simetris vs Asimetris

```
SIMETRIS (AES):
Kunci yang SAMA untuk enkripsi dan dekripsi

Pengirim: plaintext + kunci -> ciphertext
Penerima: ciphertext + kunci (sama) -> plaintext

ASIMETRIS (RSA/ECC):
Kunci BERBEDA: public key (enkripsi) + private key (dekripsi)

Pengirim: plaintext + public key -> ciphertext
Penerima: ciphertext + private key -> plaintext
```

AES jauh lebih cepat dari RSA (100-1000x), sehingga digunakan untuk enkripsi data aktual, sementara RSA/ECC hanya untuk pertukaran session key.

### Struktur Kunci AES-256

```
4e2e52fab15bfe277a7e9515a256eaba7d586d4ecae1d1c9b566900a1877fc06
|-----------------------------------------------------------------|
                    64 karakter hexadecimal
                    = 32 byte
                    = 256 bit

Setiap 2 karakter hex = 1 byte (nilai 0-255)
4e = 78 desimal = 01001110 biner
2e = 46 desimal = 00101110 biner
...
```

### Mode Operasi AES-CBC (Cipher Block Chaining)

AES memproses data dalam **blok 16 byte**. Mode CBC menghubungkan setiap blok:

```
Blok 1:  IV --XOR-- Plaintext[1] --[AES-Key]--> Ciphertext[1]
                                                      |
Blok 2:  ---------------------------------------------|
         CT[1] --XOR-- Plaintext[2] --[AES-Key]--> Ciphertext[2]
                                                       |
Blok 3:  ----------------------------------------------|
         CT[2] --XOR-- Plaintext[3] --[AES-Key]--> Ciphertext[3]
```

**Efek penting**: perubahan satu bit di plaintext mengubah semua ciphertext setelahnya (avalanche effect). Ini mencegah pola yang bisa dianalisis.

### IV (Initialization Vector)

IV adalah angka acak 16 byte yang digunakan sebagai "blok sebelumnya" untuk blok pertama. Tujuan: dua pesan identik menghasilkan ciphertext berbeda jika IV berbeda.

```python
# IV dari sesi demo:
# f5 3f c7 44 9f 89 dc fa 30 a9 4a 75 63 6e 3d ec
# 16 byte = 128 bit = angka acak baru setiap sesi
```

### Keamanan AES-256 — Mengapa Tidak Bisa Dibobol

**2^256 kemungkinan kunci:**
```
115,792,089,237,316,195,423,570,985,008,687,907,853,
269,984,665,640,564,039,457,584,007,913,129,639,936
```

**Perbandingan:**
- Jumlah atom di alam semesta: ~10^80
- Jumlah kemungkinan kunci AES-256: ~1.16 x 10^77

Bahkan jika seluruh energi bintang di galaksi Bima Sakti digunakan untuk menjalankan komputer terkuat, brute force AES-256 membutuhkan waktu lebih panjang dari umur alam semesta.

### Demonstrasi dengan Web Crypto API

```javascript
// Generate kunci AES-256 baru
const key = await crypto.subtle.generateKey(
  { name: 'AES-CBC', length: 256 },
  true,           // extractable (untuk demo)
  ['encrypt', 'decrypt']
);

// Generate IV acak
const iv = crypto.getRandomValues(new Uint8Array(16));

// Enkripsi
const encoded = new TextEncoder().encode("pesan rahasia");
const ciphertext = await crypto.subtle.encrypt(
  { name: 'AES-CBC', iv },
  key,
  encoded
);

// Dekripsi
const decrypted = await crypto.subtle.decrypt(
  { name: 'AES-CBC', iv },
  key,
  ciphertext
);
const result = new TextDecoder().decode(decrypted);
```

---

## RSA & Elliptic Curve Cryptography (ECC)

### RSA — Dasar

RSA adalah algoritma enkripsi asimetris berdasarkan **sulitnya memfaktorkan bilangan besar** menjadi faktor prima:

```
Mudah:  p = 61, q = 53 -> n = p x q = 3233
Sulit:  n = 3233 -> temukan p dan q
```

Untuk keamanan nyata, n berukuran 2048-4096 bit. Faktorisasi n tersebut tidak feasible secara komputasi dengan teknologi klasik saat ini.

### Elliptic Curve (ECC) — Lebih Modern & Efisien

ECC berdasarkan **Elliptic Curve Discrete Logarithm Problem (ECDLP)**:

```
Persamaan kurva P-256: y^2 = x^3 - 3x + b (mod p)
                       di mana p adalah bilangan prima besar

Kunci publik P = k x G
  k = private key (angka rahasia, 256 bit)
  G = titik generator standar (ditetapkan NIST)
  P = titik hasil (koordinat X, Y) = PUBLIC KEY

Menghitung P dari k dan G -> MUDAH (microsecond)
Mencari k dari P dan G   -> ECDLP, TIDAK FEASIBLE
```

### Kurva P-256 (secp256r1) — Digunakan claude.ai

Kurva yang digunakan oleh sertifikat claude.ai yang dianalisis dalam sesi ini:
- Nama: P-256 / secp256r1 / prime256v1
- Standar: NIST FIPS 186-4
- Ukuran kunci: 256 bit
- Keamanan setara: RSA-3072

### Format EC Public Key Uncompressed

```
Public key claude.ai dari sesi ini:
00 04 5C C5 39 FD AA D1 10 C5 65 C6 8E 45 7E 18
66 BD B0 98 CD 79 AB BC 39 25 70 BF C8 DC EC BC
B9 7F F2 3C 30 C6 73 0A AA BF 67 05 B5 36 6B 21
43 74 E1 DD A9 B0 6E D2 12 C8 83 A5 3C 0D 82 73
25 7E

Struktur:
00       -> padding prefix
04       -> marker "uncompressed point" (vs 02/03 untuk compressed)
[32 byte] -> koordinat X pada kurva P-256
[32 byte] -> koordinat Y pada kurva P-256
Total: 65 byte
```

**Format compressed** (prefix 02 atau 03): hanya menyimpan koordinat X, karena Y bisa dihitung dari persamaan kurva (ada 2 kemungkinan Y, prefix 02/03 menentukan yang mana).

### Perbandingan RSA vs ECC

| Aspek | RSA-2048 | RSA-3072 | ECDSA P-256 | ECDSA P-384 |
|-------|---------|---------|------------|------------|
| Ukuran kunci | 2048 bit | 3072 bit | **256 bit** | 384 bit |
| Security level | ~112 bit | ~128 bit | **~128 bit** | ~192 bit |
| Kecepatan sign | Lambat | Sangat lambat | **Sangat cepat** | Cepat |
| Kecepatan verify | Cepat | Cepat | **Lebih cepat** | Cepat |
| Ukuran sertifikat | Besar | Sangat besar | **Kecil** | Kecil |
| Digunakan di | Server lama | Enterprise | **Modern (claude.ai, dll)** | High security |

---

## Session Key & IV — Ephemeral Keying

### Definisi

**Session key** adalah kunci enkripsi simetris (AES) yang dibuat baru untuk **setiap sesi TLS**. Bersifat ephemeral — hanya berlaku selama satu koneksi dan tidak pernah disimpan atau digunakan ulang.

### Perfect Forward Secrecy (PFS)

PFS adalah properti kriptografi yang memastikan kunci sesi masa lalu tidak bisa dikompromikan meskipun private key server bocor di masa depan:

```
Sesi 1 (09:00): session key A -> data terenkripsi dengan A
Sesi 2 (09:05): session key B -> data terenkripsi dengan B
Sesi 3 (09:10): session key C -> data terenkripsi dengan C

Jika private key server dicuri tahun 2030:
- Penyerang TIDAK bisa dekripsi sesi 1, 2, 3
- Karena A, B, C tidak pernah tersimpan dan tidak bisa direkonstruksi
```

**Relevansi NSA**: NSA menyimpan ciphertext berharap bisa dekripsi di masa depan. PFS menggagalkan strategi ini.

### Diffie-Hellman Key Exchange — Cara Session Key Dibuat

Dua pihak bisa menghasilkan kunci yang sama **tanpa pernah mengirimkan kunci itu sendiri**:

```
Analogi cat:
1. Alice dan Bob sepakat: warna dasar = kuning (publik)
2. Alice punya warna rahasia: merah
3. Bob punya warna rahasia: biru
4. Alice kirim: kuning + merah = oranye (publik)
5. Bob kirim: kuning + biru = hijau (publik)
6. Alice: hijau + merah = coklat (rahasia bersama)
7. Bob: oranye + biru = coklat (rahasia bersama!)
8. Eve yang mengintip hanya lihat: kuning, oranye, hijau
   -> tidak bisa hitung coklat tanpa warna rahasia
```

---

## CSPRNG — Sumber Acak Kriptografi

### Mengapa Komputer Tidak Bisa Benar-Benar Acak

Komputer adalah mesin **deterministik** — output selalu dapat diprediksi dari input yang sama. Pseudorandom Number Generator (PRNG) biasa tidak aman untuk kriptografi karena output bisa diprediksi dari seed yang diketahui.

### CSPRNG (Cryptographically Secure PRNG)

CSPRNG memenuhi syarat kriptografi:
1. **Unpredictable**: tidak bisa diprediksi meskipun tahu output sebelumnya
2. **Backward-secure**: mengetahui state sekarang tidak membocorkan output masa lalu

### Sumber Entropi yang Digunakan OS

| Sumber | Jenis Entropi | Keterangan |
|--------|--------------|------------|
| Gerakan mouse | Koordinat & kecepatan | Sangat acak |
| Timing keyboard | Jeda mikro-detik | Akurat dan unik |
| Interrupt hardware | Timing I/O device | Tidak bisa diprediksi |
| Fluktuasi suhu CPU | Sensor termal | Noise termal fisik |
| Noise jaringan | Timing paket | Variasi latensi |
| `/dev/urandom` (Linux) | Pool entropi OS | Sumber terpercaya |

### Implementasi

```javascript
// Browser — Web Crypto API
const key = crypto.getRandomValues(new Uint8Array(32));
// Menggunakan CSPRNG dari OS melalui browser

// Node.js
const crypto = require('crypto');
const key = crypto.randomBytes(32);

// Python
import secrets
key = secrets.token_bytes(32)

// Command line (Linux)
dd if=/dev/urandom bs=32 count=1 | xxd
```

---

## MD5 vs SHA-256 vs bcrypt vs Argon2

### Hashing vs Enkripsi

**Enkripsi**: dua arah — bisa dibalik dengan kunci yang benar
**Hashing**: satu arah — tidak bisa dibalik sama sekali

Hashing digunakan untuk menyimpan password: bahkan pengelola database tidak tahu password asli pengguna.

### MD5 — Usang dan Tidak Aman

MD5 menghasilkan hash 128-bit (32 karakter hex). **Sudah dinyatakan tidak aman** untuk password sejak awal 2000-an.

**Masalah utama:**
1. **Deterministic**: input sama -> output selalu sama
2. **Tidak ada salt**: dua user dengan password sama punya hash yang sama
3. **Terlalu cepat**: GPU modern bisa hitung miliaran MD5/detik
4. **Rainbow table**: database pre-computed hash tersedia publik

**Contoh dari sesi ini:**
```
MD5("123456") = f53fc7449f89dcfa30a94a75636e3dec  <- ditemukan di rainbow table
MD5("qwerty") = 7ca46410cacf95057914906045dca1df  <- ditemukan di rainbow table
```

### SHA-256 — Aman untuk Data, Kurang Ideal untuk Password

SHA-256 menghasilkan hash 256-bit. Aman secara kriptografi (collision-resistant, preimage-resistant), tapi:

- Masih terlalu cepat untuk password hashing
- GPU dapat menghitung **miliaran SHA-256/detik**
- Tanpa salt, masih rentan rainbow table

**Cocok untuk**: integritas file, digital signature, certificate fingerprint — bukan untuk simpan password.

```javascript
// Demo dari sesi ini — SHA-256 di browser
const encoded = new TextEncoder().encode("pesan");
const hashBuffer = await crypto.subtle.digest('SHA-256', encoded);
const hex = Array.from(new Uint8Array(hashBuffer))
  .map(b => b.toString(16).padStart(2, '0')).join('');
```

### bcrypt — Standar Password Hashing

bcrypt dirancang khusus untuk password dengan dua fitur kritis:

**1. Automatic Salt:**
```
bcrypt("password123", salt="$2b$12$randomsalt...")
-> $2b$12$randomsalt.../hashedpassword
   |   |   |
   |   |   +-- 22 karakter salt
   |   +------ cost factor (12 = 2^12 = 4096 iterasi)
   +---------- versi bcrypt
```

Dua user dengan password sama menghasilkan hash **berbeda** karena salt acak.

**2. Cost Factor (Work Factor):**
- Sengaja dibuat lambat dan bisa dikonfigurasi
- Cost 12 = ~300ms per hash di CPU modern
- Meningkat seiring kemajuan hardware dengan meningkatkan cost factor

```python
import bcrypt
# Simpan password
hash = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=12))

# Verifikasi
bcrypt.checkpw(b"password123", hash)  # True
bcrypt.checkpw(b"wrongpassword", hash)  # False
```

### Argon2 — Standar Terbaru (Pemenang PHC 2015)

Argon2 memenangkan Password Hashing Competition 2015 dan menjadi rekomendasi terbaru:

| Varian | Penggunaan | Keterangan |
|--------|-----------|------------|
| Argon2d | Cryptocurrencies | Resistensi GPU terbaik |
| Argon2i | Password hashing | Resistensi side-channel |
| **Argon2id** | **Umum (recommended)** | **Kombinasi keduanya** |

**Parameter Argon2id:**
```python
from argon2 import PasswordHasher
ph = PasswordHasher(
    time_cost=3,         # Jumlah iterasi
    memory_cost=65536,   # 64 MB RAM
    parallelism=1        # Thread
)
hash = ph.hash("password123")
```

Argon2 menggunakan **memori besar** (64MB+) — ini mencegah serangan GPU/ASIC yang murah, karena GPU punya ribuan core tapi memori terbatas per core.

### Perbandingan Komprehensif

| Algoritma | Kecepatan | Salt | Cost Factor | Memory-Hard | Untuk Password | Status |
|-----------|-----------|------|-------------|-------------|---------------|--------|
| MD5 | Sangat cepat | Tidak | Tidak | Tidak | **JANGAN** | Usang |
| SHA-256 | Cepat | Manual | Tidak | Tidak | Tidak ideal | Aman untuk data |
| bcrypt | Lambat | Auto | Ya | Tidak | Baik | Standar |
| scrypt | Lambat | Auto | Ya | Ya | Baik | Digunakan di crypto |
| **Argon2id** | Lambat | Auto | Ya | Ya | **Terbaik** | **Rekomendasi 2026** |

---

## EC Public Key Format — Analisis Detail

### Pembacaan Public Key claude.ai

Dalam sesi ini, public key dari sertifikat claude.ai berhasil dibaca dari browser:

```
00 04 5C C5 39 FD AA D1 10 C5 65 C6 8E 45 7E 18
66 BD B0 98 CD 79 AB BC 39 25 70 BF C8 DC EC BC
B9 7F F2 3C 30 C6 73 0A AA BF 67 05 B5 36 6B 21
43 74 E1 DD A9 B0 6E D2 12 C8 83 A5 3C 0D 82 73
25 7E

Koordinat X: 5CC539FDAAD110C565C68E457E1866BDB098CD79ABBC392570BFC8DCECBC
Koordinat Y: B97FF23C30C6730AAABF6705B5366B214374E1DDA9B06ED212C883A53C0D827357E
```

### Web Crypto API — Implementasi Nyata

Web Crypto API (`crypto.subtle`) adalah implementasi kriptografi yang **sama persis** dengan yang digunakan HTTPS, bukan simulasi:

```javascript
// AES-256-CBC enkripsi/dekripsi
// RSA-OAEP enkripsi asimetris
// ECDSA sign/verify
// ECDH key agreement
// SHA-256/384/512 hashing
// HKDF key derivation
// PBKDF2 password hashing
```

Semua operasi terjadi di native code (C++) melalui browser binding — tidak ada overhead JavaScript.

---

## Side-Channel Attacks

### Definisi

Side-channel attack **tidak menyerang algoritma kriptografi**, melainkan mengeksploitasi informasi yang "bocor" dari implementasi fisik — konsumsi daya, emisi suara, atau timing.

### Power Analysis Attack

**Simple Power Analysis (SPA)**: analisis visual konsumsi daya -> identifikasi operasi kriptografi

**Differential Power Analysis (DPA)**: analisis statistik ribuan pengukuran -> ekstraksi kunci bit per bit

**Kasus nyata (2011)**: kunci AES diekstrak dari smartphone dengan mengukur fluktuasi daya USB.

### Acoustic Cryptanalysis

**Kasus nyata (2013, Universitas Tel Aviv)**:
- Target: laptop menjalankan GnuPG (dekripsi RSA-4096)
- Alat: mikrofon biasa, smartphone di meja yang sama
- Hasil: kunci RSA-4096 berhasil diekstrak dalam ~1 jam
- Cara kerja: CPU menghasilkan suara berbeda saat memproses bit 0 vs bit 1

### Timing Attack

Implementasi kriptografi yang **tidak constant-time** bisa bocorkan kunci:

```python
# TIDAK AMAN — waktu bervariasi tergantung nilai
if stored_hash == user_hash:  # Short-circuit evaluation!
    login_ok()

# AMAN — waktu selalu sama
import hmac
if hmac.compare_digest(stored_hash, user_hash):
    login_ok()
```

### Implikasi untuk Air-Gapped Systems

Perangkat yang **tidak terhubung jaringan apapun** (air-gapped) tetap rentan:
- Acoustic attack: suara komputer bisa direkam melalui dinding
- EM attack (TEMPEST): emisi EM menembus dinding
- Optical attack: flicker LED power bisa dikodekan dengan data
- Thermal attack: fluktuasi suhu CPU membawa informasi

**Pertahanan:**
- Constant-time implementation (semua operasi makan waktu sama)
- Power filtering dan decoupling
- Akustik shielding
- Faraday cage + noise generator
- Prosedur ketat (no recording devices)

---

## Ringkasan Hierarki Keamanan Kriptografi

```
LAPISAN 1 — Identitas & Kepercayaan
  +-- Certificate Authority (CA)
      +-- Sertifikat SSL/TLS (ECC P-256 atau RSA)
          +-- Public Key Infrastructure (PKI)

LAPISAN 2 — Pertukaran Kunci
  +-- TLS Handshake
      +-- ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)
          +-- Session Key (AES-256, ephemeral)

LAPISAN 3 — Enkripsi Data
  +-- AES-256-GCM / AES-256-CBC
      +-- IV (acak setiap sesi)
          +-- CSPRNG (entropy dari OS)

LAPISAN 4 — Integritas Data
  +-- HMAC-SHA256 / AEAD (GCM)
      +-- Deteksi modifikasi data transit

LAPISAN 5 — Autentikasi Password
  +-- Argon2id / bcrypt
      +-- Salt otomatis + cost factor
          +-- Resistensi brute force & rainbow table
```
