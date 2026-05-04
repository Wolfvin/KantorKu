#!/usr/bin/env python3
"""Generate kantorku Installation Guide PDF."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# ── Font Registration ──
pdfmetrics.registerFont(TTFont('NotoSerifSC', '/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoSerifSC-Bold', '/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Carlito', '/usr/share/fonts/truetype/english/Carlito-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Carlito-Bold', '/usr/share/fonts/truetype/english/Carlito-Bold.ttf'))
pdfmetrics.registerFont(TTFont('SarasaMono', '/usr/share/fonts/truetype/chinese/SarasaMonoSC-Regular.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))

registerFontFamily('Carlito', normal='Carlito', bold='Carlito-Bold')
registerFontFamily('NotoSerifSC', normal='NotoSerifSC', bold='NotoSerifSC-Bold')
registerFontFamily('SarasaMono', normal='SarasaMono', bold='SarasaMono')

# ── Palette ──
PAGE_BG       = colors.HexColor('#f4f4f4')
ACCENT        = colors.HexColor('#4729a3')
ACCENT_LIGHT  = colors.HexColor('#eee8fc')
TEXT_PRIMARY   = colors.HexColor('#181715')
TEXT_MUTED     = colors.HexColor('#8b8982')
HEADER_FILL   = colors.HexColor('#534c36')
CARD_BG       = colors.HexColor('#ebeae6')
BORDER_COLOR  = colors.HexColor('#d1cdc2')
TABLE_STRIPE  = colors.HexColor('#f0efed')
SEM_SUCCESS   = colors.HexColor('#3b8554')
SEM_INFO      = colors.HexColor('#486e94')
SEM_WARNING   = colors.HexColor('#ac8a47')

# ── Styles ──
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'CustomTitle', fontName='Carlito-Bold', fontSize=28, leading=36,
    textColor=ACCENT, alignment=TA_CENTER, spaceAfter=6
)

subtitle_style = ParagraphStyle(
    'CustomSubtitle', fontName='Carlito', fontSize=14, leading=20,
    textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=24
)

h1_style = ParagraphStyle(
    'H1', fontName='Carlito-Bold', fontSize=20, leading=28,
    textColor=ACCENT, spaceBefore=24, spaceAfter=12
)

h2_style = ParagraphStyle(
    'H2', fontName='Carlito-Bold', fontSize=15, leading=22,
    textColor=HEADER_FILL, spaceBefore=18, spaceAfter=8
)

h3_style = ParagraphStyle(
    'H3', fontName='Carlito-Bold', fontSize=12, leading=18,
    textColor=SEM_INFO, spaceBefore=12, spaceAfter=6
)

body_style = ParagraphStyle(
    'Body', fontName='Carlito', fontSize=10.5, leading=17,
    textColor=TEXT_PRIMARY, alignment=TA_JUSTIFY, spaceAfter=8,
    firstLineIndent=0
)

code_style = ParagraphStyle(
    'Code', fontName='SarasaMono', fontSize=8.5, leading=13,
    textColor=colors.HexColor('#1a1a2e'), backColor=colors.HexColor('#f5f5f0'),
    leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4,
    borderPadding=(6, 6, 6, 6)
)

note_style = ParagraphStyle(
    'Note', fontName='Carlito', fontSize=9.5, leading=15,
    textColor=SEM_INFO, leftIndent=16, spaceAfter=6,
    borderColor=SEM_INFO, borderWidth=0.5, borderPadding=6,
    backColor=colors.HexColor('#f0f4fa')
)

bullet_style = ParagraphStyle(
    'Bullet', fontName='Carlito', fontSize=10.5, leading=17,
    textColor=TEXT_PRIMARY, leftIndent=24, bulletIndent=12,
    spaceAfter=4
)

table_header_style = ParagraphStyle(
    'TableHeader', fontName='Carlito-Bold', fontSize=9.5, leading=14,
    textColor=colors.white, alignment=TA_CENTER
)

table_cell_style = ParagraphStyle(
    'TableCell', fontName='Carlito', fontSize=9, leading=13,
    textColor=TEXT_PRIMARY, alignment=TA_CENTER
)

table_cell_left = ParagraphStyle(
    'TableCellLeft', fontName='Carlito', fontSize=9, leading=13,
    textColor=TEXT_PRIMARY, alignment=TA_LEFT
)

table_cell_code = ParagraphStyle(
    'TableCellCode', fontName='SarasaMono', fontSize=8, leading=12,
    textColor=TEXT_PRIMARY, alignment=TA_LEFT
)

# ── Helpers ──
def h1(text):
    return Paragraph(f'<b>{text}</b>', h1_style)

def h2(text):
    return Paragraph(f'<b>{text}</b>', h2_style)

def h3(text):
    return Paragraph(f'<b>{text}</b>', h3_style)

def body(text):
    return Paragraph(text, body_style)

def code(text):
    return Paragraph(text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)

def note(text):
    return Paragraph(text, note_style)

def bullet(text):
    return Paragraph(f'<bullet>&bull;</bullet> {text}', bullet_style)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=12, spaceBefore=12)

def make_table(headers, rows, col_widths=None):
    data = [[Paragraph(f'<b>{h}</b>', table_header_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), table_cell_left if i == 0 else table_cell_code if '`' in str(c) else table_cell_style) for i, c in enumerate(row)])

    if col_widths is None:
        col_widths = [460 / len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, hAlign='CENTER')
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_FILL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), TABLE_STRIPE))
        else:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.white))
    t.setStyle(TableStyle(style_cmds))
    return t


# ── Build Document ──
output_path = '/home/z/my-project/download/kantorku/panduan-pemasangan-kantorku.pdf'
doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    leftMargin=1.2*inch, rightMargin=1.2*inch,
    topMargin=1*inch, bottomMargin=1*inch
)

story = []

# ── Title Page ──
story.append(Spacer(1, 80))
story.append(Paragraph('<b>kantorku</b>', title_style))
story.append(Paragraph('Panduan Pemasangan dan Konfigurasi Lengkap', subtitle_style))
story.append(Spacer(1, 20))
story.append(HRFlowable(width="40%", thickness=2, color=ACCENT, spaceAfter=20, spaceBefore=0))
story.append(Spacer(1, 12))
story.append(Paragraph('Kantor digital yang sesungguhnya', ParagraphStyle(
    'Tagline', fontName='Carlito', fontSize=12, leading=18,
    textColor=TEXT_MUTED, alignment=TA_CENTER
)))
story.append(Paragraph('AI Worker Orchestration Framework v0.1.0', ParagraphStyle(
    'Version', fontName='Carlito', fontSize=11, leading=16,
    textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=8
)))
story.append(Spacer(1, 40))
story.append(Paragraph('Manager terima brief dari client, diskusi dengan tim,<br/>tim riset sudah mulai kerja sebelum disuruh,<br/>dan para coder tinggal verifikasi + edit konteks yang sudah disiapkan.', ParagraphStyle(
    'Quote', fontName='Carlito', fontSize=10, leading=16,
    textColor=TEXT_MUTED, alignment=TA_CENTER
)))
story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 1: Persyaratan Sistem
# ══════════════════════════════════════════════════════
story.append(h1('1. Persyaratan Sistem'))
story.append(body('Sebelum memasang kantorku, pastikan sistem Anda memenuhi persyaratan minimum berikut. Kantorku membutuhkan Python 3.11 atau yang lebih baru karena menggunakan fitur-fitur bahasa modern seperti type hints, union types, dan async generators yang tidak tersedia di versi Python sebelumnya. Selain itu, kantorku bergantung pada beberapa library inti yang akan diinstal secara otomatis melalui pip.'))

story.append(h2('1.1 Prasyarat Perangkat Lunak'))
story.append(make_table(
    ['Komponen', 'Versi Minimum', 'Catatan'],
    [
        ['Python', '3.11+', 'Wajib. Gunakan python3 --version untuk cek'],
        ['pip', '24.0+', 'Manajer paket Python'],
        ['Git', '2.30+', 'Opsional, untuk clone repository'],
        ['Ollama', 'Terbaru', 'Opsional, untuk LLM lokal (gratis)'],
    ],
    [120, 100, 240]
))

story.append(h2('1.2 API Keys (Opsional)'))
story.append(body('Kantorku mendukung 5 provider LLM. Anda tidak perlu semua API key sekaligus — cukup provider yang ingin Anda gunakan. Untuk memulai tanpa biaya, gunakan Ollama (lokal, gratis). Setiap provider dipasang sebagai dependency opsional, sehingga Anda hanya menginstal yang benar-benar dibutuhkan tanpa membebani lingkungan Python Anda.'))
story.append(make_table(
    ['Provider', 'Env Variable', 'Install Command', 'Harga'],
    [
        ['Anthropic', 'ANTHROPIC_API_KEY', 'pip install kantorku[anthropic]', '$3-15/1M token'],
        ['Google', 'GOOGLE_API_KEY', 'pip install kantorku[google]', '$1.25-10/1M token'],
        ['MiniMax', 'MINIMAX_API_KEY', 'pip install kantorku[minimax]', '$0.12-0.30/1M token'],
        ['DeepSeek', 'DEEPSEEK_API_KEY', 'pip install kantorku[deepseek]', '$0.27-0.28/1M token'],
        ['Ollama', '-', 'pip install kantorku[ollama]', 'Gratis (lokal)'],
    ],
    [70, 120, 160, 110]
))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 2: Pemasangan
# ══════════════════════════════════════════════════════
story.append(h1('2. Pemasangan'))
story.append(body('Ada tiga cara memasang kantorku: dari PyPI (cara paling mudah), dari source (untuk development), dan menggunakan virtual environment (direkomendasikan untuk isolasi). Setiap metode menghasilkan instalasi yang identik secara fungsional — pilih yang paling sesuai dengan workflow Anda.'))

story.append(h2('2.1 Metode A: Instal dari PyPI (Direkomendasikan)'))
story.append(body('Cara paling mudah dan cepat. Kantorku dipublikasikan di PyPI sehingga bisa diinstal langsung dengan pip. Gunakan opsi [all] untuk memasang semua provider LLM sekaligus, atau pilih hanya provider yang Anda butuhkan untuk menghemat ruang disk dan menghindari dependency yang tidak perlu.'))

story.append(h3('Instal dengan semua provider:'))
story.append(code('pip install kantorku[all]'))

story.append(h3('Instal hanya provider tertentu:'))
story.append(code('pip install kantorku[anthropic,deepseek]'))

story.append(h3('Instal minimal (hanya core + Ollama):'))
story.append(code('pip install kantorku'))

story.append(h2('2.2 Metode B: Instal dari Source'))
story.append(body('Jika Anda ingin berkontribusi atau mengubah kode kantorku, clone repository dan instal dalam mode editable. Mode editable memungkinkan perubahan kode langsung berlaku tanpa perlu reinstalasi. Pastikan hatchling build system terpasang karena kantorku menggunakannya sebagai build backend.'))

story.append(code('git clone https://github.com/your-org/kantorku.git\ncd kantorku\npip install -e ".[dev]"\npython tests/test_office.py  # verifikasi'))

story.append(h2('2.3 Metode C: Virtual Environment (Best Practice)'))
story.append(body('Sangat disarankan menggunakan virtual environment untuk mengisolasi dependency kantorku dari proyek Python lainnya. Ini mencegah konflik versi dan memastikan lingkungan yang bersih. Python 3.11+ sudah menyertakan venv sebagai modul bawaan, sehingga Anda tidak perlu menginstal alat tambahan.'))

story.append(code('python3 -m venv kantorku-env\nsource kantorku-env/bin/activate    # Linux/macOS\n# atau:\nkantorku-env\\Scripts\\activate       # Windows\n\npip install kantorku[all]'))

story.append(h2('2.4 Verifikasi Instalasi'))
story.append(body('Setelah instalasi, verifikasi bahwa kantorku terpasang dengan benar dengan mengimpor modul utama dan menjalankan test suite bawaan. Jika semua impor berhasil tanpa error dan test suite menampilkan "ALL TESTS PASSED", maka kantorku siap digunakan.'))

story.append(code('python3 -c "from kantorku import Office; print(\'kantorku OK!\')"\n# Output: kantorku OK!\n\npython3 -m pytest tests/ -v  # jalankan semua test'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 3: Konfigurasi
# ══════════════════════════════════════════════════════
story.append(h1('3. Konfigurasi'))
story.append(body('Kantorku dikonfigurasi melalui file kantorku.toml yang mendefinisikan model LLM untuk setiap worker, pengaturan context pool, kredensial provider, dan path penyimpanan memory. File ini adalah pusat kendali seluruh operasi kantorku — setiap worker, pool instance, dan memory tier dapat dikustomisasi dari satu file tunggal ini.'))

story.append(h2('3.1 Membuat File Konfigurasi'))
story.append(body('Buat file kantorku.toml di root directory proyek Anda. Anda bisa menyalin template dari repository kantorku atau membuat dari nol. File ini menggunakan format TOML yang mudah dibaca manusia dan didukung luas oleh editor kode modern.'))

story.append(code('cp kantorku.toml.example kantorku.toml\n# atau buat manual:'))

story.append(h2('3.2 Struktur Konfigurasi Lengkap'))
story.append(body('Berikut adalah struktur lengkap file kantorku.toml dengan penjelasan setiap section. Setiap section mengontrol aspek berbeda dari operasi kantorku, mulai dari model Conductor hingga pengaturan server.'))

story.append(h3('Section [office] — Conductor Model'))
story.append(code('[office]\nconductor_model = "anthropic/claude-opus-4-6"\n# Model untuk Conductor (CEO).\n# Hanya untuk decision-making + orchestration.\n# Mahal ($5/M) tapi frekuensi pakai rendah.'))

story.append(h3('Section [workers.*] — Worker Definitions'))
story.append(code('[workers.coder_frontend]\nmodel = "anthropic/claude-sonnet-4-6"\nsquad = "coding"\nrole = "React/CSS/UI/Visual specialist"\n\n[workers.coder_backend]\nmodel = "minimax/minimax-m2-7"\nsquad = "coding"\nrole = "Python/Rust/Systems specialist"\n\n[workers.coder_wiring]\nmodel = "google/gemini-3-1-pro"\nsquad = "coding"\nrole = "API/WS/MCP/Glue specialist"'))

story.append(h3('Section [pool] — DeepSeek Context Pool'))
story.append(code('[pool]\nmodel = "deepseek/deepseek-v3-2"\ninstances = 3\nqueue_type = "fifo"\n# 3 instance standby, FIFO queue.\n# Proaktif saat briefing, reaktif saat diminta.'))

story.append(h3('Section [providers.*] — API Credentials'))
story.append(code('[providers.anthropic]\napi_key = "${ANTHROPIC_API_KEY}"\n\n[providers.google]\napi_key = "${GOOGLE_API_KEY}"\n\n[providers.minimax]\napi_key = "${MINIMAX_API_KEY}"\n\n[providers.deepseek]\napi_key = "${DEEPSEEK_API_KEY}"\n\n[providers.ollama]\nbase_url = "http://localhost:11434/v1"'))

story.append(note('Tip: Gunakan format ${ENV_VAR} untuk merujuk environment variable. Kantorku akan otomatis meresolve saat runtime, sehingga API key tidak perlu ditulis langsung di file konfigurasi.'))

story.append(h3('Section [memory] — Three-Ring Memory'))
story.append(code('[memory]\nring1_path = "data/ring1.duckdb"  # Hot: DuckDB\nring2_path = "data/ring2.db"        # Warm: SQLite\nring3_enabled = false               # Cold: Cognee (Fase 3)\nring3_path = "data/ring3"'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 4: Setting API Keys
# ══════════════════════════════════════════════════════
story.append(h1('4. Setting API Keys'))
story.append(body('API keys adalah kredensial yang memungkinkan kantorku berkomunikasi dengan berbagai provider LLM. Keamanan API key sangat penting — jangan pernah menyimpannya langsung di file konfigurasi atau source code. Kantorku mendukung referensi environment variable dengan sintaks ${VAR_NAME} di kantorku.toml, yang secara otomatis diresolve saat runtime.'))

story.append(h2('4.1 Metode Environment Variable'))
story.append(code('export ANTHROPIC_API_KEY="sk-ant-..."\nexport GOOGLE_API_KEY="AIza..."\nexport MINIMAX_API_KEY="mmx-..."\nexport DEEPSEEK_API_KEY="sk-..."'))

story.append(h2('4.2 Menggunakan .env File'))
story.append(body('Untuk kemudahan development, Anda bisa menggunakan file .env yang dimuat secara otomatis. File ini tidak boleh di-commit ke Git — tambahkan ke .gitignore untuk mencegah kebocoran kredensial. Gunakan python-dotenv atau shell sourcing untuk memuat variabel dari file ini sebelum menjalankan kantorku.'))

story.append(code('# .env (JANGAN commit ke Git!)\nANTHROPIC_API_KEY=sk-ant-...\nGOOGLE_API_KEY=AIza...\nMINIMAX_API_KEY=mmx-...\nDEEPSEEK_API_KEY=sk-...'))

story.append(code('# Muat sebelum menjalankan:\nset -a && source .env && set +a\npython -m kantorku.interface.server'))

story.append(h2('4.3 Setup Ollama (Gratis, Lokal)'))
story.append(body('Ollama adalah cara paling mudah untuk menjalankan LLM secara lokal tanpa API key. Ini sangat cocok untuk development dan testing karena sepenuhnya gratis dan data tidak pernah meninggalkan mesin Anda. Setelah Ollama terinstal, Anda tinggal pull model yang diinginkan dan menjalankan server.'))

story.append(code('# Instal Ollama\ncurl -fsSL https://ollama.com/install.sh | sh\n\n# Pull model\nollama pull llama3\nollama pull deepseek-coder-v2\n\n# Verifikasi\nollama list'))

story.append(note('Ollama berjalan di http://localhost:11434 secara default. Kantorku sudah dikonfigurasi untuk menggunakan endpoint ini secara otomatis melalui section [providers.ollama] di kantorku.toml.'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 5: Quick Start
# ══════════════════════════════════════════════════════
story.append(h1('5. Quick Start'))
story.append(body('Setelah konfigurasi selesai, Anda bisa mulai menggunakan kantorku dalam hitungan menit. Ada dua cara utama: programmatic API (untuk integrasi ke aplikasi Python Anda) dan server mode (untuk UI/frontend via WebSocket).'))

story.append(h2('5.1 Programmatic API'))
story.append(body('Cara paling langsung — import Office dan mulai bekerja. API ini mirip dengan cara Anda menggunakan CrewAI atau LangGraph, tetapi dengan fitur-fitur unik kantorku seperti Contract flow, BriefingRoom, dan Context Pool.'))

story.append(code('import asyncio\nfrom kantorku import Office\n\nasync def main():\n    # 1. Buat office dari config\n    office = Office.from_config("kantorku.toml")\n    await office.initialize()\n\n    # 2. One-shot run (paling simpel)\n    result = await office.run(\n        "Buat rate limiter di Rust"\n    )\n    print(result)\n\n    # 3. Shutdown\n    await office.shutdown()\n\nasyncio.run(main())'))

story.append(h2('5.2 Step-by-Step (Panel 1 + Panel 2)'))
story.append(body('Untuk kontrol lebih granular, gunakan alur step-by-step yang memisahkan fase negosiasi kontrak (Panel 1) dan eksekusi pekerjaan (Panel 2). Ini memungkinkan client memberikan feedback sebelum pekerjaan dimulai, dan mengamati progress secara real-time.'))

story.append(code('office = Office.from_config("kantorku.toml")\nawait office.initialize()\n\n# Panel 1: Chat dengan Manager\nasync for event in office.chat(\n    "session-1",\n    "Buat rate limiter di Rust"\n):\n    if event["type"] == "manager_message":\n        print(f"Manager: {event[\'content\']}")\n    elif event["type"] == "contract_ready":\n        print(f"Kontrak: {event[\'contract\']}")\n\n# Client setuju → mulai kerja\nresult = await office.accept_and_run("session-1")\nprint(result)'))

story.append(h2('5.3 Server Mode (WebSocket)'))
story.append(body('Jalankan kantorku sebagai server untuk terhubung dengan frontend (Tauri, React, dll). Server menyediakan dua channel WebSocket independen: /ws/client untuk Panel 1 dan /ws/office untuk Panel 2. Ini memungkinkan arsitektur dual-panel seperti yang dijelaskan dalam arsitektur kantorku.'))

story.append(code('# Jalankan server\nkantorku --config kantorku.toml --port 8000\n\n# atau dengan uvicorn langsung:\nuvicorn kantorku.interface.server:app --host 0.0.0.0 --port 8000'))

story.append(h3('WebSocket Channel 1: /ws/client'))
story.append(body('Channel untuk interaksi user dengan Manager (Panel 1). Client mengirim pesan dan menerima respons dari Conductor, termasuk contract_ready event ketika kontrak siap.'))

story.append(code('# Client kirim:\n{"type": "user_message", "content": "Buat rate limiter"}\n\n# Server respons:\n{"type": "manager_message", "content": "Production atau internal?"}\n{"type": "contract_ready", "contract": {...}}\n\n# Client setuju:\n{"type": "contract_accepted", "contract": {...}}'))

story.append(h3('WebSocket Channel 2: /ws/office'))
story.append(body('Channel untuk live event stream dari office (Panel 2). Semua aktivitas worker, context fetch, dan verification dikirim secara real-time ke channel ini, memungkinkan monitoring menyeluruh.'))

story.append(code('# Connect:\nws://localhost:8000/ws/office?session_id=session-1\n\n# Events yang diterima:\n{"type": "briefing_opened", "from": "conductor", ...}\n{"type": "context_fetch_start", "instance": 0, ...}\n{"type": "task_assigned", "to": "coder_backend", ...}\n{"type": "task_done", "from": "coder_backend", ...}'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 6: Custom Worker
# ══════════════════════════════════════════════════════
story.append(h1('6. Membuat Custom Worker'))
story.append(body('Kantorku dirancang untuk extensible — Anda bisa membuat worker kustom yang mewarisi BaseWorker dan mengimplementasikan method handle(). Worker kustom bisa menggunakan LLM manapun melalui self.llm_call(), mengakses konteks yang sudah di-prefetch melalui self.get_context(), dan berkomunikasi dengan worker lain melalui WorkerHub. Ini membuat kantorku sangat fleksibel untuk berbagai use case.'))

story.append(code('from kantorku import BaseWorker, Office\nfrom kantorku.worker.base import Task, TaskResult\n\nclass SecurityAuditor(BaseWorker):\n    """Custom worker untuk security audit."""\n\n    async def handle(self, task: Task) -> TaskResult:\n        # Ambil konteks yang sudah di-prefetch\n        context = await self.get_context(task.id)\n\n        prompt = f"""\n        Audit keamanan untuk: {task.instruction}\n\n        Konteks: {context or \'Tidak ada\'}\n\n        Periksa:\n        1. SQL injection, XSS, CSRF\n        2. Authentication/Authorization\n        3. Input validation\n        4. Sensitive data exposure\n        """\n\n        response = await self.llm_call(prompt)\n        return TaskResult(\n            task_id=task.id,\n            status="done",\n            output=response,\n        )\n\n# Daftarkan ke Office\noffice = Office()\noffice.hire_worker(\n    "security_auditor",\n    model="anthropic/claude-sonnet-4-6",\n    squad="verification",\n    role="Security audit specialist",\n    worker_class=SecurityAuditor,\n)'))

story.append(body('Worker kustom juga bisa meng-override method speak_up() untuk berpartisipasi dalam BriefingRoom, dan receive_dm() untuk menerima pesan langsung dari worker lain. Ini memungkinkan pola komunikasi yang kaya antar worker tanpa perlu mengubah kode inti kantorku.'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 7: Worker Model Assignment
# ══════════════════════════════════════════════════════
story.append(h1('7. Tabel Worker dan Model'))
story.append(body('Berikut adalah tabel lengkap seluruh worker kantorku dengan model yang direkomendasikan berdasarkan benchmark terbaru April 2026. Setiap worker dipilih berdasarkan keunggulannya di benchmark spesifik — bukan berdasarkan popularitas atau harga semata. Strategi ini memastikan setiap tugas dikerjakan oleh model yang paling kompeten di domain tersebut.'))

story.append(make_table(
    ['Worker', 'Model', 'Squad', 'Harga/1M'],
    [
        ['conductor', 'Claude Opus 4.6', 'orchestration', '$5.00'],
        ['intake', 'Llama 3 (Ollama)', 'translation', 'gratis'],
        ['narrator', 'Llama 3 (Ollama)', 'translation', 'gratis'],
        ['coder_frontend', 'Claude Sonnet 4.6', 'coding', '$1.50'],
        ['coder_backend', 'MiniMax M2.7', 'coding', '$0.30'],
        ['coder_wiring', 'Gemini 3.1 Pro', 'coding', '$2.00'],
        ['verifier_designer', 'Gemini 3.1 Pro', 'verification', '$2.00'],
        ['verifier_engineer', 'MiniMax M2.5', 'verification', '$0.12'],
        ['pool (x3)', 'DeepSeek V3.2', 'context', '$0.28'],
        ['debugger', 'DeepSeek V3.2', 'support', '$0.28'],
        ['scout', 'Gemini 2.5 Pro', 'support', '$1.25'],
        ['auditor', 'Claude Sonnet 4.6', 'support', '$1.50'],
        ['scribe', 'DeepSeek V4 Flash', 'support', '$0.27'],
        ['summarizer', 'DeepSeek V4 Flash', 'support', '$0.27'],
        ['sentinel', 'Llama 3 (Ollama)', 'support', 'gratis'],
    ],
    [110, 130, 90, 80]
))

story.append(Spacer(1, 12))
story.append(body('Rata-rata biaya per task berkisar $0.50-$2.00 tergantung kompleksitas, karena sebagian besar pekerjaan dilakukan oleh model murah (MiniMax, DeepSeek) sementara model mahal (Claude Opus) hanya digunakan untuk decision-making yang frekuensinya rendah.'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 8: Three-Ring Memory
# ══════════════════════════════════════════════════════
story.append(h1('8. Three-Ring Memory'))
story.append(body('Kantorku menggunakan sistem memory tiga lapis yang terinspirasi dari arsitektur CPU cache. Setiap ring memiliki karakteristik yang berbeda dalam hal kecepatan akses, kapasitas, dan persistensi, memungkinkan kantorku menyimpan data pada tier yang paling sesuai dengan pola aksesnya.'))

story.append(h2('8.1 Ring 1 — DuckDB Hot Memory'))
story.append(body('Ring 1 menyimpan data yang paling sering diakses dan membutuhkan latensi terendah: konteks yang sudah di-prefetch oleh Context Pool, state session aktif, riwayat percakapan, dan hasil task terbaru. DuckDB berjalan in-process (tanpa network overhead) dengan latensi mikrodetik, menjadikannya ideal untuk data yang perlu diakses berkali-kali selama satu sesi kerja.'))

story.append(bullet('Latensi: mikrodetik (in-process)'))
story.append(bullet('Konten: prefetched context, session state, task results, history'))
story.append(bullet('Kapasitas: sesuai RAM tersedia'))
story.append(bullet('Persistensi: file .duckdb di disk'))

story.append(h2('8.2 Ring 2 — SQLite Warm Memory'))
story.append(body('Ring 2 menyimpan data yang tidak perlu diakses setiap saat tetapi penting untuk analisis jangka panjang: episode log (apa yang terjadi, apa yang berhasil, apa yang gagal), pelajaran yang dipetik oleh Sentinel, dan audit trail untuk setiap aksi worker. Data ini berguna untuk fine-tuning di masa depan dan untuk memahami pola kerja tim dari waktu ke waktu.'))

story.append(bullet('Latensi: milidetik'))
story.append(bullet('Konten: episode logs, lessons learned, audit trail'))
story.append(bullet('Format: SQLite + Parquet (untuk bulk analytics)'))
story.append(bullet('Use case: training data, post-mortem analysis'))

story.append(h2('8.3 Ring 3 — Cognee GraphRAG Cold Memory'))
story.append(body('Ring 3 adalah tier penyimpanan jangka panjang yang menggunakan Cognee untuk GraphRAG (Graph-based Retrieval Augmented Generation). Ini memungkinkan pencarian semantik lintas sesi dan pembentukan knowledge graph dari semua histori pekerjaan. Ring 3 masih dalam tahap stub dan akan diimplementasikan di Fase 3 development kantorku.'))

story.append(bullet('Latensi: ratusan milidetik'))
story.append(bullet('Konten: knowledge graph, semantic search index'))
story.append(bullet('Use case: cross-session learning, pattern discovery'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 9: Troubleshooting
# ══════════════════════════════════════════════════════
story.append(h1('9. Troubleshooting'))
story.append(body('Berikut adalah masalah-masalah umum yang mungkin Anda temui saat memasang atau menjalankan kantorku, beserta solusinya. Sebagian besar masalah berkaitan dengan dependency yang kurang, konfigurasi API key, atau koneksi ke LLM provider.'))

story.append(h2('9.1 ModuleNotFoundError'))
story.append(body('Jika Anda mendapatkan error ini saat import, kemungkinan besar provider-specific package belum diinstal. Kantorku menggunakan optional dependencies — setiap provider LLM dipasang terpisah. Pastikan Anda menginstal bracket notation yang benar saat menjalankan pip install.'))

story.append(code('# Error: ModuleNotFoundError: No module named \'anthropic\'\n# Solusi:\npip install kantorku[anthropic]\n\n# Error: ModuleNotFoundError: No module named \'google.genai\'\n# Solusi:\npip install kantorku[google]'))

story.append(h2('9.2 Provider Not Configured'))
story.append(body('Error ini muncul ketika worker mencoba menggunakan provider yang belum dikonfigurasi kredensialnya. Pastikan API key sudah diset di environment variable DAN section [providers.*] sudah ada di kantorku.toml dengan referensi ${ENV_VAR} yang benar.'))

story.append(code('# Error: Provider \'anthropic\' not configured\n# Solusi:\nexport ANTHROPIC_API_KEY="sk-ant-..."\n# Verifikasi:\npython3 -c "import os; print(os.environ.get(\'ANTHROPIC_API_KEY\', \'NOT SET\'))"'))

story.append(h2('9.3 Ollama Connection Refused'))
story.append(body('Jika menggunakan Ollama dan mendapatkan connection error, pastikan Ollama server sedang berjalan dan model sudah di-pull. Ollama perlu dijalankan sebagai background service sebelum kantorku bisa menggunakannya.'))

story.append(code('# Cek apakah Ollama berjalan:\ncurl http://localhost:11434/api/tags\n\n# Jalankan Ollama:\nollama serve\n\n# Pull model yang dibutuhkan:\nollama pull llama3'))

story.append(h2('9.4 DuckDB Ring1 Error'))
story.append(body('Jika DuckDB gagal membuat file database, pastikan directory tujuan ada dan memiliki permission yang benar. Kantorku secara default membuat file di ./data/, yang mungkin belum ada di environment Anda.'))

story.append(code('# Error: Unable to open database file\n# Solusi:\nmkdir -p data\nchmod 755 data'))

story.append(PageBreak())

# ══════════════════════════════════════════════════════
# SECTION 10: Arsitektur Overview
# ══════════════════════════════════════════════════════
story.append(h1('10. Arsitektur Overview'))
story.append(body('Kantorku memiliki arsitektur yang terdiri dari beberapa layer utama yang saling berinteraksi: Conductor sebagai CEO yang mengorkestrasi seluruh operasi, BriefingRoom sebagai ruang diskusi pra-eksekusi, WorkerHub sebagai lapisan komunikasi peer-to-peer antar worker, dan ContextPool sebagai sumber konteks proaktif yang siap sebelum worker mulai bekerja.'))

story.append(h2('10.1 Flow Lengkap'))
story.append(body('Alur kerja kantorku dimulai dari pesan client, melalui negosiasi kontrak, briefing tim, prefetch konteks, eksekusi paralel, verifikasi, hingga selesai. Setiap langkah menghasilkan event yang dikirim ke Panel 2 untuk monitoring real-time. Berikut adalah urutan lengkapnya:'))

story.append(bullet('Client kirim pesan ke Panel 1'))
story.append(bullet('Conductor memahami pesan (bisa multi-turn clarification)'))
story.append(bullet('Conductor menyiapkan kontrak (structured todo list)'))
story.append(bullet('Client setuju / minta revisi'))
story.append(bullet('BriefingRoom dibuka — workers speak_up paralel'))
story.append(bullet('Context Pool prefetch konteks untuk setiap todo'))
story.append(bullet('Conductor assign tasks ke workers (paralel jika bisa)'))
story.append(bullet('Workers eksekusi dengan konteks yang sudah siap'))
story.append(bullet('Workers bisa DM sesama atau request konteks tambahan'))
story.append(bullet('Verifier memeriksa output (design + engineer paralel)'))
story.append(bullet('Sentinel mencatat pelajaran'))
story.append(bullet('Selesai — client menerima hasil'))

story.append(h2('10.2 Perbandingan Framework'))
story.append(body('Kantorku memiliki perbedaan fundamental dibanding LangGraph dan CrewAI. Alih-alih menggunakan graph routing manual atau sequential process, kantorku menggunakan Conductor yang membuat keputusan cerdas berdasarkan konteks — mirip cara manager sungguhan mengorkestrasi timnya.'))

story.append(make_table(
    ['Fitur', 'LangGraph', 'CrewAI', 'kantorku'],
    [
        ['Orkestrasi', 'Manual routing', 'Process.sequential', 'Conductor (CEO)'],
        ['Pre-execution', 'Tidak', 'Tidak', 'BriefingRoom'],
        ['Worker comms', 'Tidak', 'Terbatas', 'WorkerHub DM'],
        ['Proactive prefetch', 'Tidak', 'Tidak', 'ContextPool FIFO'],
        ['Memory', 'External', 'Basic', '3-Ring (hot/warm/cold)'],
        ['Contract flow', 'Tidak', 'Tidak', 'Client <-> Manager'],
        ['Real-time UI', 'Tidak', 'Tidak', 'Dual WebSocket'],
    ],
    [100, 90, 90, 100]
))

story.append(Spacer(1, 24))
story.append(hr())
story.append(Paragraph(
    'kantorku — karena kantor yang baik bukan yang paling canggih, tapi yang paling tahu siapa harus mengerjakan apa.',
    ParagraphStyle('Footer', fontName='Carlito', fontSize=10, leading=16,
                   textColor=TEXT_MUTED, alignment=TA_CENTER)
))

# ── Build ──
doc.build(story)
print(f"PDF generated: {output_path}")
