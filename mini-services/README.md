# Mini Services

Microservices pendukung KantorKu.

Setiap service adalah proses terpisah dengan responsibility spesifik.
Semua service dikonfigurasi melalui `.zscripts/mini-services-*.sh`.

## Planned Services

- `code-executor/` — Sandbox untuk eksekusi code (E2B atau Docker)
- `web-search/` — Proxy ke Tavily/Serper untuk scout worker
- `file-storage/` — File management untuk output worker

## Adding a New Service

1. Buat subfolder di sini, misalnya `my-service/`
2. Tambahkan `package.json` dengan script `dev` dan `build`
3. Buat entry point di `src/index.ts`
4. Service akan otomatis terdeteksi oleh `.zscripts/mini-services-start.sh`
