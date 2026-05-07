# Frontend Cleanliness Heuristics

## Practical Rules
- Komponen presentasional pisah dari logic berat bila itu membuat test/debug lebih mudah.
- Event handler harus eksplisit (`onSaveClick`, bukan `handleAction` generik).
- Hindari mutation state tersembunyi; gunakan update flow yang konsisten.
- Kurangi CSS global leakage; utamakan scope lokal halaman/fitur.

## Review Prompts
- Apakah orang baru bisa memahami flow layar ini dalam <5 menit?
- Kalau bug muncul, apakah titik masuk debugging jelas?
- Jika fitur ini dihapus, apakah impact area bisa diprediksi?

## Release Hygiene
- Simpan perubahan visual dan perubahan behavior dalam commit terpisah jika memungkinkan.
- Tulis risk note singkat untuk area yang sulit diverifikasi otomatis.
