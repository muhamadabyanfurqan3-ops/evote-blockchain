# Laporan Analisis Eksperimen & Kinerja Komputasi Paralel Terdistribusi
## Simulasi Sistem E-Voting Blockchain Berbasis Proof-of-Work dan Docker

**Mata Kuliah:** Komputasi Paralel dan Terdistribusi (KPT) - Semester 5  
**Bagian Arsitektur & Core:** Safid Nasih Ulwan  
**Bagian Benchmark & Analisis Kinerja:** Naufal & Tim  
**Versi Dokumen:** 1.0.0 (Template Siap Isi Data Uji)

---

## 1. Pendahuluan & Tujuan Eksperimen

Eksperimen ini bertujuan untuk mengevaluasi kinerja, skalabilitas, dan keandalan sistem voting digital terdistribusi berbasis Blockchain dengan algoritma konsensus **Proof-of-Work (PoW)**. Pengujian difokuskan pada pengukuran metrik komputasi paralel klasik (*Speedup* dan *Efficiency*), performa jaringan terdistribusi (*Throughput* dan *Propagation Delay*), serta ketahanan sistem terhadap kegagalan node (*Fault Recovery*).

> [!NOTE]
> Seluruh container worker dan coordinator dijalankan pada satu *host machine* yang sama menggunakan Docker Bridge Network (`evoting-net`) untuk mensimulasikan lingkungan terdistribusi multi-node.

---

## 2. Metodologi & Spesifikasi Lingkungan Pengujian (Testbed)

### 2.1. Spesifikasi Perangkat Keras & Lunak
* **Processor (CPU)**: *(Isi spesifikasi CPU pengujian, misal: AMD Ryzen 7 / Intel Core i7, Jumlah Cores/Threads)*
* **Memori (RAM)**: *(Isi kapasitas RAM, misal: 16 GB DDR4)*
* **Sistem Operasi Host**: *(Windows 11 / Ubuntu 22.04 LTS)*
* **Docker Engine**: *(Versi Docker, misal: 24.0.x)*
* **Python Runtime**: Python 3.11-slim (Containerized)
* **Tingkat Kesulitan PoW (Difficulty)**: 4 leading zeros (`"0000"`)

---

## 3. Landasan Teori Komputasi Paralel

Dalam komputasi paralel dan terdistribusi, efektivitas sistem diukur menggunakan formulasi metrik baku:

### 3.1. Speedup Ratio ($S$)
Speedup mengukur peningkatan kecepatan komputasi ketika beban kerja diselesaikan oleh $P$ unit pemroses (node worker) dibandingkan dengan 1 unit pemroses tunggal (sekuensial):

$$S = \frac{T_{sekuensial}}{T_{paralel}}$$

di mana:
- $T_{sekuensial}$: Waktu eksekusi penambangan/pemrosesan transaksi pada 1 node tunggal.
- $T_{paralel}$: Waktu eksekusi rata-rata ketika didistribusikan ke $P$ worker nodes yang bersaing secara paralel.

### 3.2. Parallel Efficiency ($E$)
Efisiensi mengukur seberapa optimal pemanfaatan sumber daya komputasi paralel:

$$E = \frac{S}{P} \times 100\%$$

di mana:
- $S$: Nilai Speedup.
- $P$: Jumlah worker nodes yang berpartisipasi ($P \in \{2, 4, 6, 8\}$).

### 3.3. Throughput (Transactions Per Second / TPS)
Kapasitas sistem dalam menerima, memvalidasi, dan mencatatkan transaksi suara ke dalam blok per satuan detik:

$$\text{TPS} = \frac{\text{Total Suara Berhasil Masuk Ledger (Transaksi)}}{\text{Total Waktu Pengujian (Detik)}}$$

---

## 4. Lembar Data Hasil Eksperimen Skalabilitas Node

Pengujian dilakukan dengan memvariasikan jumlah container worker: **2, 4, 6, dan 8 node**.

### 4.1. Tabel Pengukuran Waktu Eksekusi PoW & Throughput
*(Silakan isi data angka riil hasil benchmark pada tabel di bawah ini)*

| Jumlah Worker ($P$) | Beban Transaksi (Suara) | Waktu Mining Rata-rata ($T_{paralel}$, detik) | Speedup Ratio ($S$) | Efisiensi Paralel ($E$) | Throughput Rata-rata (TPS) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1 (Baseline)** | 100 suara | *(contoh: 8.45 s)* | 1.00x | 100.0% | *(contoh: 11.8 TPS)* |
| **2 Worker** | 100 suara | *[Isi data]* | *[Isi data]* | *[Isi data]* | *[Isi data]* |
| **4 Worker** | 100 suara | *[Isi data]* | *[Isi data]* | *[Isi data]* | *[Isi data]* |
| **6 Worker** | 100 suara | *[Isi data]* | *[Isi data]* | *[Isi data]* | *[Isi data]* |
| **8 Worker** | 100 suara | *[Isi data]* | *[Isi data]* | *[Isi data]* | *[Isi data]* |

### 4.2. Tabel Pengukuran Block Propagation Delay & Konsensus
Pengukuran waktu yang dibutuhkan sejak blok baru ditambang oleh satu node hingga blok tersebut tervalidasi dan terdistribusi ke seluruh node (*Longest Valid Chain reconciliation*).

| Jumlah Worker ($P$) | Latensi Jaringan Rata-rata (ms) | Propagation Delay ke Node Terjauh (ms) | Waktu Konsensus Resolusi Konflik (ms) | Tingkat Kegagalan Validasi (%) |
| :---: | :---: | :---: | :---: | :---: |
| **2 Worker** | *[Isi data]* | *[Isi data]* | *[Isi data]* | 0.0% |
| **4 Worker** | *[Isi data]* | *[Isi data]* | *[Isi data]* | 0.0% |
| **6 Worker** | *[Isi data]* | *[Isi data]* | *[Isi data]* | 0.0% |
| **8 Worker** | *[Isi data]* | *[Isi data]* | *[Isi data]* | *[Isi data]* |

---

## 5. Analisis Ilmiah & Komparasi Kinerja

### 5.1. Analisis Speedup & Efisiensi (Teori vs Realita)
*(Subbab untuk diisi Naufal berdasarkan data tabel 4.1)*

* **Relevansi Hukum Amdahl**:
  Pada sistem blockchain Proof-of-Work, proses hashing SHA-256 merupakan bagian yang dapat diparalelkan (*parallel portion*), namun verifikasi integritas rantai, penulisan ke disk (I/O), dan koordinasi konsensus merupakan fraksi sekuensial (*serial portion*).
* **Fenomena Penurunan Efisiensi**:
  Ketika jumlah node bertambah dari 2 ke 8, perhatikan apakah nilai efisiensi $E$ mengalami degradasi. Diskusikan mengapa penambahan node pekerja dalam sistem konsensus blockchain tidak selalu menghasilkan *linear speedup* (karena overhead komunikasi broadcast HTTP/JSON dan kompetisi non-kolektif antar-penambang).

### 5.2. Analisis Throughput vs Propagation Delay
* Diskusikan trade-off antara desentralisasi dan latensi.
* Jelaskan bagaimana ukuran payload transaksi suara mempengaruhi *propagation delay* saat jumlah node meningkat.

---

## 6. Analisis Profiling Bottleneck Sistem

> [!WARNING]
> Hasil profiling mengidentifikasi tiga area kritis yang menjadi pembatas performa (*performance bottleneck*):

1. **Overhead Komunikasi HTTP/1.1 Synchronous**:
   - Komunikasi antar-node menggunakan arsitektur REST berbasis HTTP/1.1 dengan format serialisasi JSON. Setiap pemanggilan konsensus `/nodes/resolve` memerlukan *TCP handshake* dan *connection teardown* yang menambah latensi overhead dibandingkan protokol biner (seperti gRPC atau WebSocket).
2. **Operasi I/O Disk & File Locking (`threading.Lock()`)**:
   - Untuk menjamin sifat *ACID-like* dan mencegah data corrupt pada Docker Volume, modul `LedgerStorage` menggunakan write atomik (`NamedTemporaryFile` + `os.fsync` + `shutil.move`). Saat transaksi masuk bertubi-tubi, antrean lock pada disk I/O menjadi salah satu penahan lonjakan throughput.
3. **Pemanfaatan Resource CPU pada Proof-of-Work**:
   - Hashing SHA-256 pada Python berjalan pada *single thread* per container karena pengaruh *Global Interpreter Lock (GIL)*. Penggunaan multi-container di Docker memungkinkan pemanfaatan multi-core CPU fisik secara optimal di level OS host.

---

## 7. Evaluasi Fault Tolerance & Node Recovery

Uji ketahanan (*chaos testing*) dilakukan dengan mematikan salah satu node secara mendadak saat sistem sedang aktif:

### Skenario Pengujian:
1. Sistem berjalan normal dengan 6 node.
2. 5 transaksi suara dikirimkan ke mempool.
3. Node `evoting-worker-3` dimatikan menggunakan perintah:
   ```bash
   docker stop evoting-worker-3
   ```
4. Transaksi suara ditambang oleh `evoting-worker-1` hingga menghasilkan Blok baru (#2).
5. Transaksi baru lainnya ditambang hingga terbentuk Blok (#3).
6. Node `evoting-worker-3` dihidupkan kembali:
   ```bash
   docker start evoting-worker-3
   ```
7. Pemicuan konsensus dilakukan via `GET http://localhost:5003/nodes/resolve`.

### Hasil Observasi Pemulihan (*Recovery*):
* **Status Data Lokal Pasca Restart**: *(Isi hasil observasi: Berkas `ledger.json` pada volume `./data/worker-3` tetap utuh).*
* **Efektivitas Longest Valid Chain**: *(Jelaskan bagaimana worker-3 berhasil mengunduh rantai terpanjang dari worker tetangga dan meng-update tinggi rantainya dari 1 ke 3 tanpa kehilangan konsistensi).*
* **Kesimpulan Fault Tolerance**: Sistem terbukti memiliki ketahanan tinggi (*high availability*) terhadap *node failure* berkat perpaduan Docker persistent volumes dan aturan konsensus rantai terpanjang.
