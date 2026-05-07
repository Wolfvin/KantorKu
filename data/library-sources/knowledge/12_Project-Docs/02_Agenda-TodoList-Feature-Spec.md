---
title: Agenda & TodoList Feature Spec
kategori: Project Docs & Notes
tags: agenda, todo-list, feature-spec, AKP2I, deadline, kanban
---

sekarang kita akan masuk ke agenda. agenda bisa diakses oleh siapapun. bahkan oleh non admin. disana user dapat menulis
- pilih tanggal, (deadline)
- title
- detail pekerjaan
lalu ada tombol "simpan"
data yang akan di ambil
- pilih tanggal, (deadline)
- title
- detail pekerjaan
- tanggal dibuat

lalu akan di display di kolom yang sama dengan yang kamu gabungkan, bersamaan dengan patch updates.
yang ini tidak akan di post ke server, tapi akan di simpan ke dalam app data, yang baru bisa di hapus jika tekan 
<button class="sp-btn-danger" onclick="cleanupNow()">🧹 Bersihkan</button>




ok selanjutnya adalah kita akan menambahkan 1 kolom dibawah
<section class="page-section active" id="page-agenda">

di sini akan ada todo list. jadi akan ada 3 kolom 
dekat deadline (merah)|sedang dikerjakan (kuning)|telah selesai (hijau)


format tugas
- warna di samping kiri 
- title
- detail tugas 
- tanggal deadline
cth:(<div class="magic-bento-card card-clickable service-item si-red" data-page="rekening">
                  <div class="service-icon">🏦</div>
                  <div class="service-info">
                    <div class="magic-bento-card__header" style="display:none;">
                      <div class="magic-bento-card__label">Tersedia</div>
                    </div>
                    <h2 class="magic-bento-card__title service-title">Rekening Koran</h2>
                    <p class="magic-bento-card__description service-desc">Kelola data rekening koran Anda</p>
                  </div>
                  <span class="service-badge">Tersedia</span>
                  <button class="card-action-btn service-arrow">›</button>
                </div>

)
lalu di paling kanan menggantikan 
service-arrow">›</button>  --> menjadi sebuah tombol centang. jika ditekan akan ada animasi jadi hijau dan akan hilang serta muncul di halaman -> telah selesai (hijau)



- dekat deadline = artinya kurang dari 10 hari
- sedang dikerjakan = artinya lebih dari 10 hari
- sudah ditekan tombol <selesai>



