---
title: HTTPS, TLS & Infrastruktur Internet
kategori: Jaringan Komputer & Kriptografi
tags: HTTPS, TLS, SSL, jaringan, kriptografi, CA, handshake, forward-secrecy, QUIC
---

# Jaringan Komputer

## WWW Bukan Server

### Klarifikasi Konsep

Salah satu kesalahpahaman umum adalah menganggap `www` sebagai penanda server atau lokasi fisik. Kenyataannya, `www` hanyalah **subdomain konvensional** yang tidak memiliki makna teknis khusus.

### Anatomi URL Lengkap

```
https://www.google.com/search?q=hello#results
  │       │      │        │           │
  │       │      │        │           └── fragment (anchor)
  │       │      │        └────────────── path & query string
  │       │      └─────────────────────── top-level domain (.com)
  │       └────────────────────────────── domain (google)
  │       ├── www = subdomain (bisa diganti apa saja)
  └────────────────────────────────────── protokol (https)
```

### Fakta tentang WWW

- `www` adalah subdomain seperti `mail`, `api`, `cdn`, `blog`
- Website modern banyak yang tidak menggunakan www: `claude.ai`, `github.com`, `huggingface.co`
- Server sebenarnya = komputer fisik/virtual di cloud (AWS, GCP, Cloudflare, dsb.)
- `www.example.com` dan `example.com` bisa mengarah ke server yang sama atau berbeda

---

## HTTPS & SSL/TLS

### Definisi

**HTTPS** (HyperText Transfer Protocol Secure) adalah ekstensi aman dari HTTP yang menggunakan enkripsi **TLS** (Transport Layer Security) untuk melindungi data antara browser dan server.

```
HTTP  → Port 80  → Data terkirim sebagai teks biasa (plaintext)
HTTPS → Port 443 → Data terenkripsi dengan AES-256 + TLS
```

### Komponen Utama HTTPS

#### 1. Sertifikat SSL/TLS
Dokumen digital yang memverifikasi identitas server. Berisi:
- Nama domain yang dilindungi
- Nama penerbit (Certificate Authority)
- Tanggal berlaku
- **Public key** server (untuk TLS handshake)
- Tanda tangan digital CA

#### 2. Certificate Authority (CA)
Lembaga tepercaya yang memverifikasi dan menandatangani sertifikat SSL. Contoh CA terpercaya:
- DigiCert
- Let's Encrypt (gratis, otomatis)
- Sectigo
- Amazon (untuk layanan AWS)
- GlobalSign

#### 3. Cipher Suite
Kombinasi algoritma yang digunakan dalam satu sesi TLS. Contoh:
```
TLS_AES_256_GCM_SHA384
 │    │       │    │
 │    │       │    └── Hash function (integritas data)
 │    │       └──────── Mode operasi (GCM)
 │    └──────────────── Ukuran kunci (256 bit)
 └───────────────────── Protokol (TLS)
```

### Perbedaan HTTP vs HTTPS

| Aspek | HTTP | HTTPS |
|-------|------|-------|
| Enkripsi | Tidak ada | AES-256 + TLS |
| Port | 80 | 443 |
| Keamanan data | Terekspos plaintext | Terenkripsi end-to-end |
| Sertifikat | Tidak diperlukan | SSL Certificate wajib |
| Indikator Browser | "Not Secure" | Gembok |
| SEO | Lebih rendah | Lebih tinggi (Google preferensi) |
| Performa | Sedikit lebih cepat | Overhead minimal di TLS 1.3 |

### Cara Verifikasi Sertifikat di Browser

**Chrome/Edge:**
```
Klik gembok di address bar
→ "Connection is secure"
→ "Certificate is valid"
→ Tab "Details" untuk info lengkap
```

Info yang tersedia:
- `Subject`: domain yang dilindungi
- `Issuer`: Certificate Authority penerbit
- `Public Key Algorithm`: RSA atau ECDSA
- `Valid From / Until`: masa berlaku
- `Fingerprint`: hash unik sertifikat (SHA-256)

---

## TLS Handshake — Proses Detail

### Gambaran Umum

TLS Handshake adalah **negosiasi keamanan** yang terjadi setiap kali browser terhubung ke server HTTPS. Tujuan: memastikan kedua pihak setuju tentang algoritma enkripsi dan bertukar kunci secara aman tanpa ada pihak ketiga yang bisa menyalin kunci.

### TLS 1.3 Handshake (Standar Modern)

```
Browser                          Server
   │                                │
   │── 1. Client Hello ────────────▶│
   │   (versi TLS, cipher list,     │
   │    client random, key share)   │
   │                                │
   │◀── 2. Server Hello ────────────│
   │   (cipher dipilih,             │
   │    server random, key share,   │
   │    sertifikat SSL)             │
   │                                │
   │── 3. Verifikasi Sertifikat ──▶ │ (lokal, ke CA)
   │   (apakah sertifikat valid?)   │
   │                                │
   │   4. Key Derivation ──────────│
   │   (kedua pihak hitung          │
   │    session key yang sama)      │
   │                                │
   │── 5. Finished ───────────────▶│
   │◀── 5. Finished ────────────────│
   │                                │
   │◀═══ Data Terenkripsi (AES) ═══▶│
```

### Langkah Detail

**Step 1 — Client Hello:**
- Versi TLS tertinggi yang didukung browser
- Daftar cipher suite yang didukung
- Client random (angka acak 32 byte)
- Key share untuk Diffie-Hellman

**Step 2 — Server Hello:**
- Cipher suite yang dipilih (terbaik yang didukung keduanya)
- Server random
- Key share server untuk Diffie-Hellman
- Sertifikat SSL (berisi public key)

**Step 3 — Verifikasi Sertifikat:**
Browser memverifikasi sertifikat ke CA:
- Apakah sertifikat ditandatangani oleh CA yang dipercaya?
- Apakah domain cocok?
- Apakah sertifikat masih berlaku?
- Apakah sertifikat di-revoke?

**Step 4 — Key Derivation:**
Menggunakan algoritma **Diffie-Hellman Ephemeral (DHE)** atau **ECDHE**, kedua pihak menghitung session key yang sama tanpa pernah mengirimkan kunci itu sendiri melalui jaringan.

**Step 5 — Finished:**
Kedua pihak kirim pesan "Finished" yang terenkripsi, mengkonfirmasi handshake berhasil.

### TLS 1.2 vs TLS 1.3

| Aspek | TLS 1.2 | TLS 1.3 |
|-------|---------|---------|
| Round trips | 2 | **1** |
| 0-RTT resume | Tidak | Ya |
| Cipher lemah | Masih ada | **Dihapus** |
| Forward Secrecy | Opsional | **Wajib** |
| Keamanan | Baik | **Lebih baik** |
| Kecepatan | Standar | **Lebih cepat** |

### Perfect Forward Secrecy (PFS)

Fitur kritis TLS 1.3: session key **baru dibuat setiap sesi** dan tidak pernah disimpan. Artinya:

> Jika private key server berhasil dicuri suatu hari, penyerang **tidak bisa** mendekripsi rekaman traffic masa lalu — karena session key sudah tidak ada lagi.

Ini sangat relevan dengan konteks NSA yang diketahui menyimpan ciphertext untuk didekripsi di masa depan ketika komputasi lebih powerful.

### Port & Protokol

```
HTTP  → TCP Port 80   → Plaintext
HTTPS → TCP Port 443  → TLS-encrypted
QUIC  → UDP Port 443  → HTTP/3 (TLS 1.3 built-in, lebih cepat)
```
