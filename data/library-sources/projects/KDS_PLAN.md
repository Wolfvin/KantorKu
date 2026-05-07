# Kitchen Displaying System (KDS) - Rencana Implementasi

## Goal
Membangun sistem KDS untuk restoran agar pesanan dari kasir/online langsung tampil ke layar dapur, diproses per stasiun, dipantau SLA waktu masak, dan selesai tanpa miskomunikasi kertas/manual.

## Scope In
- Manajemen order real-time (new, cooking, ready, served, canceled).
- Tampilan KDS per stasiun dapur (grill, fryer, drink, plating).
- Prioritas order (dine-in, takeaway, delivery, VIP, due time).
- Timer SLA dan alert keterlambatan.
- Sinkronisasi status ke POS/order source.
- Role dasar: kasir, kitchen staff, kitchen supervisor, admin.
- Audit log perubahan status order.
- Laporan dasar performa dapur (prep time, delay rate, throughput).

## Scope Out
- Integrasi pembayaran.
- Inventori/stock management lanjutan.
- Prediksi AI demand/forecast.
- Multi-brand enterprise analytics yang kompleks.

## Yang Akan Dibangun
1. `Order Ingestion Service`
- Endpoint/API untuk menerima order dari POS/app.
- Validasi payload order + mapping item ke station.
- Idempotency key agar order duplikat tidak masuk dua kali.

2. `Realtime Event Layer`
- Broadcast event order ke layar dapur (WebSocket/SSE).
- Mekanisme reconnect + replay event saat koneksi putus.

3. `KDS Kitchen UI`
- Board per station berbasis kolom status: New -> Cooking -> Ready -> Served.
- Action cepat: start cooking, mark ready, recall, cancel reason.
- Visual priority indicator (warna, badge, countdown).

4. `Routing & Workflow Engine`
- Aturan routing item ke station.
- Split order otomatis jika item beda station.
- Dependency handling (contoh: plating menunggu station lain ready).

5. `SLA & Alert Module`
- Timer per order/item berdasarkan target prep time.
- Alert threshold: warning, critical, overdue.
- Ringkasan antrian aktif per station.

6. `Sync & Integration Adapter`
- Sync status order kembali ke POS.
- Retry + dead-letter policy untuk kegagalan sinkronisasi.

7. `Reporting & Audit`
- Log aktivitas user untuk setiap perubahan status.
- Dashboard metrik harian: avg prep time, cancel rate, bottleneck station.

8. `Security & Access Control`
- Login + role-based access control.
- Pembatasan aksi berdasarkan role/station.

## Arsitektur Teknis (Target)
- Frontend: Web app KDS touchscreen-friendly.
- Backend: API + realtime gateway + workflow service.
- Database: order state, event log, audit trail.
- Deployment: on-prem/local network atau cloud ringan sesuai kebutuhan outlet.

## Phases
| Fase | Nama | Status | Output |
|---|---|---|---|
| 1 | Discovery & Requirement Lock | in_progress | daftar requirement final, SLA target, station map |
| 2 | System Design & Data Contract | pending | ERD, API spec, event schema, status lifecycle |
| 3 | Core Backend Implementation | pending | ingestion, routing, state machine, sync adapter |
| 4 | Realtime + Kitchen UI | pending | board KDS per station + realtime event handling |
| 5 | SLA/Alert + Reporting | pending | timer, alert policy, dashboard metrik |
| 6 | Hardening & Go-Live | pending | security, test, observability, rollout checklist |

## Risks
- Koneksi dapur tidak stabil -> risiko status tidak sinkron.
- Mapping menu ke station tidak konsisten antar outlet.
- Human error (misclick status) saat jam sibuk.
- Latensi tinggi jika event layer tidak efisien.
- Perubahan requirement operasional setelah pilot berjalan.

## Mitigasi Risiko
- Offline-safe queue + replay event.
- Konfigurasi station mapping per outlet dengan versi.
- Tombol konfirmasi untuk aksi kritikal (cancel/void).
- Load test pada jam sibuk simulasi.
- Pilot rollout 1 outlet sebelum multi-outlet.

## Verification
- Uji lifecycle status end-to-end dari order masuk sampai served.
- Uji reliability realtime (disconnect/reconnect/replay).
- Uji idempotency untuk order duplikat.
- Uji SLA alert sesuai threshold yang ditetapkan.
- Uji hak akses role per aksi.
- UAT dengan skenario jam sibuk dapur.

## Delivery Gates
- Gate 1 (context cukup): requirement outlet, station list, SLA target tersedia.
- Gate 2 (plan realistis): kontrak API/event dan fase implementasi disetujui.
- Gate 3 (hasil verified): seluruh checklist verification lulus di staging.
- Gate 4 (handoff): SOP operasional + runbook incident + training kitchen.

## Blocker Saat Ini
- Belum ada detail operasional outlet (menu-station mapping, SLA per kategori menu, volume order puncak).

## Next Step Minimum
- Finalisasi requirement operasional per outlet untuk menutup fase 1 lalu lanjut desain sistem (fase 2).

## Evidence Verifikasi
- Dokumen plan ini telah dibuat sebagai baseline implementasi: `KDS_PLAN.md`.
