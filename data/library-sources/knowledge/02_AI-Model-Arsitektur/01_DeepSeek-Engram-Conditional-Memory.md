---
title: DeepSeek Engram & Conditional Memory
kategori: AI Model & Arsitektur
tags: [DeepSeek, Engram, Conditional-Memory, AI-Architecture, LLM, N-gram, Hashing]
---

Laporan ini disusun berdasarkan analisis mendalam terhadap berbagai sumber video yang membahas terobosan terbaru dalam dunia kecerdasan buatan (AI), arsitektur model, agen otonom, hingga implikasi sosial dan neurosains.

═══════════════════════════════════
**TOPIK: DeepSeek Engram & Conditional Memory**
**Kategori:** AI Architecture
**Sumber:** *DeepSeek Just Fixed One Of The Biggest Problems With AI* & *DeepSeek's Insane Architecture Breakthrough [Engram Explained]*
═══════════════════════════════════
**RINGKASAN**
Teknologi Engram dari DeepSeek AI merupakan inovasi arsitektur yang memperkenalkan komponen "memori kondisional" ke dalam model bahasa besar (LLM). Tujuannya adalah untuk menghentikan pemborosan komputasi di mana AI harus membangun kembali makna frasa umum atau fakta statis dari nol setiap kali diproses. Target audiensnya adalah peneliti AI, pengembang sistem skala besar, dan pengguna yang menginginkan AI lebih cerdas namun lebih efisien secara biaya.

**KONSEP / FITUR UTAMA**
Engram menggunakan *n-gram embeddings* yang dikombinasikan dengan *multi-head hashing* untuk menciptakan tabel pencarian (*lookup table*) raksasa. Cara kerjanya adalah dengan memantau aliran token dan secara instan mengenali pola multi-token (seperti nama tokoh sejarah atau sintaksis pemrograman) untuk kemudian mengambil representasi yang sudah tersimpan. Selain itu, terdapat mekanisme *context-aware gating* yang berfungsi sebagai filter untuk memastikan data yang diambil dari memori relevan dengan konteks saat ini. Fitur ini juga diintegrasikan dengan *Multi-Head Latent Attention* (MHC) untuk meningkatkan performa melalui arsitektur multi-cabang.

**MASALAH YANG DIPECAHKAN**
Masalah utama yang dipecahkan adalah pemborosan komputasi pada model *Transformer* standar yang sering kali "membangun kembali roda" untuk fakta-fakta sederhana. Hal ini sangat membantu pengembang yang menghadapi keterbatasan sumber daya komputasi dan pengguna yang membutuhkan respons cepat untuk tugas-tugas berbasis fakta. Dengan Engram, model tidak perlu menggunakan lapisan penalaran kompleks hanya untuk mengingat informasi statis.

**MANFAAT & USE CASE**
Manfaat nyata meliputi peningkatan efisiensi komputasi sebesar 20-25% dan penurunan drastis dalam tingkat kesalahan pada *benchmark* seperti trivia dan pemahaman bacaan. Contoh *use case* yang disebutkan adalah ketika model menemui frasa "Diana Princess of Wales", di mana Engram memungkinkan model langsung mengenali entitas tersebut tanpa harus memproses hubungan antar kata secara bertahap melalui banyak lapisan. Ini menghasilkan AI yang lebih pintar namun tetap ringan untuk dijalankan di perangkat pribadi.

**KELEMAHAN / BATASAN**
Salah satu batasan teknis adalah penempatan modul Engram; jika diletakkan terlalu dalam pada jaringan saraf, akurasinya akan menurun karena model telah membuang waktu memproses informasi tersebut sebelumnya. Selain itu, jika mekanisme *gating* dihilangkan, hasil pencarian memori bisa menjadi sangat bising (*noisy*) dan mengganggu kualitas keluaran. Penggunaan memori tambahan ini juga dapat memberikan sedikit beban pada *throughput* sistem, meskipun hanya sekitar 1.9% hingga 2.8%.

**HARGA / AKSES**
DeepSeek merilis temuan ini sebagai bagian dari penelitian terbuka dan diharapkan akan diimplementasikan pada model DeepSeek V4 mendatang. Teknologi ini diprediksi akan memungkinkan sistem AI yang lebih murah, tanpa langganan mahal, dan dapat dijalankan secara privat di perangkat pengguna.

**REFERENSI YANG DISEBUTKAN**
*   Paper: "Conditional memory via scalable lookup: a new axis of sparsity for LLMs"
*   Platform: Lambda (untuk menjalankan DeepSeek secara privat)
*   Sponsor: SERP API (untuk data pencarian terstruktur)
*   Intuitive Academy (kursus AI oleh bycloud)
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: Claude Code & Auto-Mode**
**Kategori:** AI Tool / Programming / Productivity
**Sumber:** *Auto Claude: NEW Claude Auto-Mode is INSANE!* & *New Self Improving Hyperagents Break Limits Of AI*
═══════════════════════════════════
**RINGKASAN**
Claude Code memperkenalkan fitur "Auto-mode" yang memungkinkan AI bertindak secara otonom dalam melakukan tugas-tugas pengembangan perangkat lunak. Fitur ini dirancang untuk menghilangkan hambatan interaksi manual di mana pengguna sebelumnya harus memberikan izin untuk setiap langkah kecil yang diambil AI. Target audiens utamanya adalah pengembang perangkat lunak, agen SEO, dan praktisi otomasi yang ingin meningkatkan produktivitas.

**KONSEP / FITUR UTAMA**
Fitur utama adalah *Auto permissions mode* dan *Bypass permissions mode* yang dapat diaktifkan melalui pengaturan akun tim atau terminal. Sistem ini menggunakan klasifikasi berbasis AI untuk mengecek setiap tindakan sebelum dijalankan; jika tindakan dianggap aman, Claude akan langsung mengeksekusinya, namun jika berisiko (seperti menghapus file penting), sistem akan memblokir dan meminta konfirmasi. Selain itu, Claude sekarang memiliki kemampuan "Computer Use" untuk mengoperasikan aplikasi, mengedit file, dan menjalankan perintah di sistem operasi layaknya pengguna manusia.

**MASALAH YANG DIPECAHKAN**
Masalah utama yang diatasi adalah inefisiensi waktu akibat interaksi berulang ("sitting there clicking approve 100 times"). Ini sangat membantu pengembang yang sedang menangani proyek besar dengan ribuan file yang perlu diperbarui secara massal. Selain itu, fitur ini memecahkan masalah keamanan dari metode lama "skip permissions" yang sangat berisiko karena dapat merusak sistem secara tidak terkendali.

**MANFAAT & USE CASE**
Pengguna dapat memberikan tugas besar, seperti membangun situs web SEO lengkap atau melakukan refaktor kode besar-besaran, lalu meninggalkan komputer sementara Claude bekerja secara mandiri. Contoh konkretnya adalah kemampuan Claude untuk mencari file presentasi di ponsel, mengubahnya ke PDF, dan melampirkannya ke undangan kalender secara otomatis. Hal ini memberikan keuntungan berupa kecepatan pengerjaan proyek yang jauh lebih tinggi dibandingkan metode konvensional.

**KELEMAHAN / BATASAN**
Kelemahannya adalah sistem klasifikasi tidak sempurna; terkadang tindakan berisiko bisa lolos jika instruksinya membingungkan, atau tindakan aman justru terblokir. Anthropic sangat menyarankan penggunaan fitur ini dalam lingkungan terisolasi seperti *virtual machine* atau *sandbox* untuk keamanan. Selain itu, mode ini mengonsumsi lebih banyak token karena adanya pengecekan latar belakang oleh sistem klasifikasi.

**HARGA / AKSES**
Saat ini tersedia untuk pengguna Claude *Team Plan* dan akan segera hadir bagi pengguna *Enterprise* serta melalui API. Claude Code mendukung model Claude 3.5 Sonnet dan Claude 3 Opus.

**REFERENSI YANG DISEBUTKAN**
*   AI Profit Boarding (komunitas dan kursus pelatihan)
*   Dokumentasi resmi Anthropic
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: Kimi Attention Residuals**
**Kategori:** AI Architecture
**Sumber:** *China’s NEW AI Breakthrough Shocked Elon Musk*
═══════════════════════════════════
**RINGKASAN**
Kimi dari Moonshot AI memperkenalkan inovasi bernama "Attention Residuals" untuk memperbaiki kesalahan desain fundamental pada model *Transformer* yang sudah ada selama 10 tahun. Teknologi ini bertujuan untuk meningkatkan kecerdasan model seiring bertambahnya kedalaman lapisan tanpa memerlukan tambahan daya komputasi. Penemuan ini menarik perhatian tokoh besar seperti Elon Musk dan Andrej Karpathy.

**KONSEP / FITUR UTAMA**
Model *Transformer* standar memberikan bobot yang sama (nilai 1) pada setiap lapisan saat meneruskan informasi, yang menyebabkan sinyal penting tenggelam dalam kebisingan (*noise*) saat model semakin dalam. Desain baru ini memungkinkan lapisan yang lebih dalam untuk secara selektif menarik informasi dari lapisan-lapisan sebelumnya berdasarkan relevansi konten. Analogi yang digunakan adalah seorang koki yang hanya mengambil bahan yang dibutuhkan dari dapur, alih-alih mencampurkan semua bahan dari setiap stasiun kerja dalam jumlah yang sama.

**MASALAH YANG DIPECAHKAN**
Masalah utama adalah hilangnya kecerdasan pada lapisan model yang sangat dalam karena akumulasi data yang tidak relevan. Ini memecahkan hambatan dalam tugas-tugas penalaran multi-langkah (*multi-step reasoning*) di mana AI sering kali kehilangan jejak logika awal. Hal ini sangat membantu bisnis yang mengandalkan AI untuk perencanaan strategi kompleks atau penulisan proposal panjang.

**MANFAAT & USE CASE**
Memberikan peningkatan efisiensi komputasi sebesar 25%, yang berarti model mendapatkan hasil yang sama dengan biaya 25% lebih rendah. Pada pengujian *benchmark* seperti GPQA Diamond, skor meningkat dari 36.9 menjadi 44.4. Contoh penggunaan nyata adalah agensi pemasaran yang menggunakan AI untuk merancang strategi pemasaran lengkap secara logis, bukan sekadar membuat baris subjek email.

**KELEMAHAN / BATASAN**
Saat ini, teknologi ini masih berupa makalah riset dan Kimi belum meluncurkan produk konsumen yang secara resmi menggunakan arsitektur ini secara penuh. Terdapat jeda waktu antara pembuktian secara ilmiah dengan ketersediaan alat yang dapat digunakan langsung oleh pengguna umum.

**HARGA / AKSES**
Informasi harga spesifik tidak disebutkan karena masih dalam tahap riset arsitektural, namun diprediksi akan membuat alat AI di masa depan menjadi lebih cerdas dan murah.

**REFERENSI YANG DISEBUTKAN**
*   Paper: "Attention Residuals" oleh Moonshot AI
*   AI Profit Boardroom (komunitas implementasi AI)
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: OpenClaw & Krisis Spam AI**
**Kategori:** Cybersecurity / AI Ethics
**Sumber:** *AI broke the one thing we can't fix*
═══════════════════════════════════
**RINGKASAN**
Video ini membahas ancaman eksistensial terhadap infrastruktur komunikasi digital akibat munculnya alat AI otonom seperti OpenClaw. Fokusnya adalah bagaimana kemudahan akses ke teknologi ini akan membuat platform seperti Gmail, iMessage, dan X (Twitter) tidak dapat digunakan lagi dalam waktu singkat karena banjir spam yang sangat cerdas. Target audiensnya adalah masyarakat umum dan pengguna layanan komunikasi digital.

**KONSEP / FITUR UTAMA**
OpenClaw adalah proyek perangkat lunak sumber terbuka (open-source) paling populer di GitHub saat ini yang memungkinkan siapa saja membangun agen AI otonom. Agen ini mampu mengirim email, melakukan panggilan telepon, menavigasi web, dan meniru identitas manusia dengan tingkat kefasihan yang setara dengan pemegang gelar PhD. Berbeda dengan bot lama yang bodoh, bot baru ini menggunakan pemrosesan bahasa alami (NLP) tingkat lanjut dan memiliki dompet Bitcoin untuk transaksi.

**MASALAH YANG DIPECAHKAN**
OpenClaw "memecahkan" masalah kesulitan teknis dalam melakukan aktivitas spamming masif; sebelumnya, pelaku harus mengerti kode dan manajemen server, kini hanya butuh laptop dan akses ke OpenClaw. Namun, bagi masyarakat, ini menciptakan masalah baru berupa hilangnya kepercayaan pada semua bentuk komunikasi digital dari orang asing.

**MANFAAT & USE CASE**
Meskipun disorot secara negatif, contoh penggunaan "positif" adalah seseorang yang menggunakan OpenClaw untuk menegosiasikan harga mobil dengan diler melalui iMessage saat ia sedang makan siang (*brunch*). Namun, penggunaan oleh pihak seperti pemerintah Tiongkok untuk menenggelamkan informasi politik dengan konten pornografi otomatis menunjukkan sisi gelap dari teknologi ini.

**KELEMAHAN / BATASAN**
Kelemahan utamanya adalah potensi penyalahgunaan yang tidak terkendali karena sifatnya yang open-source. Tidak ada solusi teknis yang jelas untuk menghentikan banjir konten "slop" (sampah AI) ini, karena algoritma periklanan dan jaringan sosial tidak memiliki insentif untuk membedakan antara konten manusia dan bot.

**HARGA / AKSES**
OpenClaw tersedia secara gratis sebagai proyek open-source di GitHub.

**REFERENSI YANG DISEBUTKAN**
*   GitHub (untuk proyek OpenClaw)
*   X (Twitter) - sebagai studi kasus spam bot
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: JEPA (Joint Embedding Predictive Architecture)**
**Kategori:** AI Theory / Machine Learning
**Sumber:** *Mathematician Explains Why LLMs Are a Dead End*
═══════════════════════════════════
**RINGKASAN**
Makalah ini memperkenalkan JEPA sebagai alternatif untuk mengatasi keterbatasan LLM yang dianggap sebagai "jalan buntu" menuju kecerdasan umum buatan (AGI). JEPA berfokus pada prediksi dalam ruang representasi laten daripada memprediksi kata per kata, yang dianggap lebih mirip dengan cara kerja otak manusia. Target audiensnya adalah akademisi, matematikawan, dan peneliti AI tingkat lanjut.

**KONSEP / FITUR UTAMA**
JEPA membuang pendekatan prediksi token berbasis teks dan beralih ke *self-supervised learning* pada ruang geometris berdimensi rendah. Alih-alih melacak setiap detail kecil (seperti daun pada pohon yang tumbang), JEPA hanya mempelajari properti kunci dari data tersebut. Pengembangannya melibatkan "explore tokens" untuk melakukan penalaran abstrak dan "receiver tokens" untuk menangkap hasil eksplorasi tersebut tanpa terikat pada tuntutan menghasilkan teks secara langsung.

**MASALAH YANG DIPECAHKAN**
Mengatasi masalah akumulasi kesalahan eksponensial pada LLM, di mana satu kesalahan kecil dalam prediksi kata dapat menyebabkan seluruh argumen menjadi halusinasi. JEPA memecahkan hambatan "tekanan representasi" di mana model dipaksa memikirkan setiap kata berikutnya, sehingga gagal menangkap struktur dunia yang lebih luas.

**MANFAAT & USE CASE**
JEPA memungkinkan pembentukan "World Model" yang efisien untuk perencanaan tindakan dalam ruang abstrak. Dalam pengujian matematika, pendekatan ini telah menunjukkan hasil yang menjanjikan dibandingkan LLM konvensional karena mampu bernalar lebih fundamental. Ini memberikan peluang bagi sistem AI untuk melakukan generalisasi yang lebih baik pada tugas-tugas di luar data pelatihannya.

**KELEMAHAN / BATASAN**
Kelemahan utamanya adalah kesulitan teknis untuk mengubah kembali representasi dimensi rendah tersebut menjadi format yang dapat dipahami manusia seperti teks atau gambar. Saat ini, tantangan terbesarnya adalah bagaimana membuat model ini berkomunikasi dengan pengguna manusia secara efektif.

**HARGA / AKSES**
Informasi mengenai ketersediaan komersial tidak disebutkan, namun peneliti (Yan LeCun) sering merilis ide-ide ini secara terbuka melalui Meta.

**REFERENSI YANG DISEBUTKAN**
*   Yan LeCun (Kepala AI Meta)
*   Paper terkait "Universal Computer" dan "Cheering Machine"
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: MolmoWeb**
**Kategori:** AI Agents / Automation
**Sumber:** *MolmoWeb - Fully Open Multimodal Web Agents*
═══════════════════════════════════
**RINGKASAN**
MolmoWeb adalah agen web visual sumber terbuka yang dibangun oleh Allen Institute for AI (AI2) yang mampu mengontrol browser secara otonom melalui instruksi bahasa Inggris sederhana. Keunikannya terletak pada cara kerjanya yang murni berbasis visual, bukan membaca kode HTML. Target audiensnya adalah pengembang sistem otomasi dan peneliti AI yang mencari alternatif agen web transparan.

**KONSEP / FITUR UTAMA**
Model ini tersedia dalam ukuran 4 miliar dan 8 miliar parameter. Cara kerjanya adalah dengan mengambil tangkapan layar (*screenshot*) dari halaman web, memutuskan tindakan (klik, ketik, scroll) menggunakan Vision Language Model (VLM), dan mengeksekusinya hingga tugas selesai. Seluruh resep pelatihan, kumpulan data, dan bobot model dirilis secara terbuka.

**MASALAH YANG DIPECAHKAN**
Memecahkan kerumitan dalam mengotomatisasi tugas web pada halaman yang dinamis dan sulit dikikis (*scraped*) secara tradisional melalui HTML. Ini membantu pengguna yang ingin melakukan otomasi tanpa harus mengerti struktur teknis sebuah situs web.

**MANFAAT & USE CASE**
Dapat digunakan untuk tugas kompleks seperti mencari tiket pesawat termurah dari Sydney ke Jakarta pada tanggal tertentu, di mana agen akan mengisi formulir dan menavigasi situs maskapai secara mandiri. MolmoWeb memberikan hasil yang lebih baik dibandingkan agen yang dibangun di atas model tertutup yang jauh lebih besar pada beberapa *benchmark*.

**KELEMAHAN / BATASAN**
Kecepatan dan latensinya masih dianggap agak lambat untuk penggunaan waktu nyata saat ini. Selain itu, model ini membutuhkan sumber daya VRAM yang cukup besar, yaitu sekitar 17 GB untuk versi 8 miliar parameter.

**HARGA / AKSES**
Sepenuhnya gratis dan sumber terbuka (open-source).

**REFERENSI YANG DISEBUTKAN**
*   Hugging Face (untuk mengunduh bobot model)
*   Playwright & Chromium (perpustakaan yang dibutuhkan)
*   UV (pengelola paket Python)
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: Google Stitch 2.0**
**Kategori:** Design / AI Tool
**Sumber:** *NEW Google Stitch 2.0 Updates are INSANE!*
═══════════════════════════════════
**RINGKASAN**
Google Stitch 2.0 adalah alat otomasi desain UI/UX yang memungkinkan pengguna membangun antarmuka lengkap hanya dengan perintah suara. Alat ini mengintegrasikan desain visual dengan pembuatan kode *front-end* secara langsung. Target audiensnya adalah desainer UI/UX dan pengembang web.

**KONSEP / FITUR UTAMA**
Fitur utamanya adalah *infinite canvas* yang memungkinkan penataan setiap layar dan alur perjalanan pengguna dalam satu tempat secara simultan. Terdapat pula *Design Agent* yang secara otomatis mengingat preferensi warna, font, dan gaya merek di semua keluaran untuk menjaga konsistensi. Hasil akhirnya berupa kode HTML, CSS, dan React yang siap digunakan.

**MASALAH YANG DIPECAHKAN**
Mengatasi masalah inefisiensi saat harus berpindah-pindah antar file desain dan kehilangan jejak koneksi antar layar dalam sebuah proyek besar. Ini juga memecahkan masalah inkonsistensi branding yang sering terjadi pada proyek desain kolaboratif.

**MANFAAT & USE CASE**
Manfaat utamanya adalah pembuatan prototipe interaktif instan yang dapat diklik tanpa perlu penyambungan manual antar layar. Desainer dapat dengan cepat membuat demonstrasi produk yang berfungsi penuh hanya dalam hitungan menit.

**KELEMAHAN / BATASAN**
Informasi mengenai batasan teknis tidak dijelaskan secara rinci dalam video, selain fokus pada kemudahan penggunaannya.

**HARGA / AKSES**
Saat ini tersedia secara gratis.
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: Psilocybin & Neuroplasticity Mapping**
**Kategori:** Neuroscience / Biotechnology
**Sumber:** *Neuroscience JUST Did the IMPOSSIBLE*
═══════════════════════════════════
**RINGKASAN**
Para peneliti di Cornell dan Allen Institute berhasil memetakan proses perbaikan otak oleh psilosibin (jamur ajaib) secara waktu nyata menggunakan virus rabies yang direkayasa. Studi ini memberikan bukti fisik pertama tentang bagaimana pengalaman transformatif mengubah sirkuit saraf secara permanen. Target audiensnya adalah praktisi kesehatan mental, peneliti neurosains, dan masyarakat umum yang tertarik pada terapi psikotropika.

**KONSEP / FITUR UTAMA**
Penelitian ini menggunakan virus rabies yang dimodifikasi secara genetik agar tidak mematikan dan memiliki penanda fluoresen hijau untuk melacak koneksi antar neuron mundur satu sinapsis. Data diproses menggunakan *light sheet microscopy* untuk menghasilkan jutaan gambar irisan otak yang sangat tipis. Hasilnya menunjukkan bahwa psilosibin memperkuat koneksi sensorik sebesar 10% (seperti korteks visual) dan melemahkan wilayah yang terkait dengan narasi diri dan kecemasan (seperti amigdala dan insula) sebesar 15%.

**MASALAH YANG DIPECAHKAN**
Memecahkan misteri lama mengenai di mana tepatnya koneksi saraf baru tumbuh setelah penggunaan psilosibin. Hal ini memberikan dasar ilmiah bagi fenomena penyembuhan depresi dan PTSD yang sebelumnya sering dianggap anekdot.

**MANFAAT & USE CASE**
Memberikan kemampuan untuk "memprogram" perbaikan otak; para peneliti menemukan bahwa jika satu wilayah otak disenyapkan selama sesi psilosibin, wilayah tersebut tidak akan mengalami pengkabelan ulang. Ini berarti terapi masa depan dapat dirancang secara spesifik dengan mengarahkan perhatian pasien ke stimulus tertentu untuk memperkuat jalur saraf yang diinginkan.

**KELEMAHAN / BATASAN**
Terdapat risiko etis dan bahaya manipulasi identitas, karena siapa pun yang mengontrol perhatian seseorang selama jendela plastisitas puncak ini dapat membentuk kepribadian orang tersebut. Selain itu, studi ini dilakukan pada tikus, sehingga diperlukan penelitian lebih lanjut untuk aplikasi manusia secara luas.

**HARGA / AKSES**
Makalah penelitian ini tersedia untuk umum melalui tautan yang disediakan dalam deskripsi video asli.

**REFERENSI YANG DISEBUTKAN**
*   Cornell University & Allen Institute
*   Teknik: *Light Sheet Microscopy*
═══════════════════════════════════

═══════════════════════════════════
**TOPIK: Meta Hyper-agents**
**Kategori:** AI Agents / Automation
**Sumber:** *New Self Improving Hyperagents Break Limits Of AI*
═══════════════════════════════════
**RINGKASAN**
Meta memperkenalkan sistem "Hyper-agents" yang mampu menulis ulang proses peningkatannya sendiri secara mandiri. Ini adalah langkah maju dari AI yang hanya pintar pada satu tugas menjadi AI yang pintar dalam belajar bagaimana cara belajar. Target audiensnya adalah peneliti AI tingkat lanjut dan pengembang otomasi industri.

**KONSEP / FITUR UTAMA**
Hyper-agents menggabungkan seluruh sistem peningkatan diri menjadi satu program yang dapat memodifikasi kodenya sendiri tanpa batasan aturan manusia yang kaku. Dalam pengujian robotika, sistem ini mampu merancang fungsi hadiahnya sendiri untuk mencapai tujuan yang lebih efisien (seperti melompat untuk mencapai ketinggian maksimal, bukan sekadar berdiri). Sistem ini juga mampu membangun alat internalnya sendiri untuk melacak kinerjanya dan menyesuaikan strategi berdasarkan sisa daya komputasi yang tersedia.

**MASALAH YANG DIPECAHKAN**
Memecahkan masalah "langit-langit" pada AI sebelumnya (seperti DGM) di mana bagian yang melakukan peningkatan diri dirancang oleh manusia sehingga kemajuannya terbatas pada aturan awal. Hyper-agents menghilangkan lapisan birokrasi kode tersebut.

**MANFAAT & USE CASE**
Diterapkan dalam penilaian tugas matematika tingkat olimpiade, sistem ini mampu mencapai peningkatan signifikan meskipun sistem lama gagal total. Penggunaan lainnya adalah dalam peninjauan makalah penelitian, di mana AI membangun pipa evaluasi terstruktur sendiri untuk memberikan umpan balik yang lebih mendalam.

**KELEMAHAN / BATASAN**
Karena kemampuannya untuk menulis ulang kode sendiri, terdapat kekhawatiran mengenai kontrol jangka panjang jika sistem mulai mengabaikan tujuan awal manusia demi efisiensi yang ditemukannya sendiri.

**HARGA / AKSES**
Informasi harga tidak tersedia karena saat ini merupakan proyek riset dari Meta.

**REFERENSI YANG DISEBUTKAN**
*   Genesis (Simulator robotika)
*   Sponsor: Luma AI (Luma Agents untuk kolaborasi kreatif)
*   SigReg (Teknik stabilisasi representasi internal)
═══════════════════════════════════

### **INDEKS TOPIK**

| Topik | Kategori |
| :--- | :--- |
| **DeepSeek Engram & Conditional Memory** | AI Architecture |
| **Claude Code & Auto-Mode** | AI Tool / Programming / Productivity |
| **Kimi Attention Residuals** | AI Architecture |
| **OpenClaw & Krisis Spam AI** | Cybersecurity / AI Ethics |
| **JEPA (Joint Embedding Predictive Architecture)** | AI Theory / Machine Learning |
| **MolmoWeb** | AI Agents / Automation |
| **Google Stitch 2.0** | Design / AI Tool |
| **Psilocybin & Neuroplasticity Mapping** | Neuroscience / Biotechnology |
| **Meta Hyper-agents** | AI Agents / Automation |