# Simulasi Sistem Voting Digital Terdistribusi Menggunakan Konsensus Proof-of-Work Berbasis Python Flask dan Docker

Proyek Ujian Akhir Semester (UAS) mata kuliah **Komputasi Paralel dan Terdistribusi (KPT)** - Semester 5.

---

## 📌 Deskripsi Proyek
Proyek ini mengimplementasikan simulasi sistem *electronic voting* (e-voting) berbasis teknologi **Blockchain terdistribusi** dengan algoritma konsensus **Proof-of-Work (PoW)**. Sistem ini dirancang untuk menjamin sifat *immutability*, transparansi, integritas data suara, serta mencegah manipulasi atau *double voting* melalui jaringan node terdesentralisasi.

Setiap suara pemilih diperlakukan sebagai transaksi yang diverifikasi, dikumpulkan ke dalam *mempool*, dan ditambang (*mined*) ke dalam rantai blok (*blockchain*) oleh node-node worker melalui persaingan komputasi PoW.

---

## 🏗️ Topologi Jaringan & Arsitektur Sistem

Sistem beroperasi dengan topologi **1 Master / Coordinator Node + 6 Worker Nodes**:

```
                              +--------------------------+
                              |   Master / Coordinator   |
                              |       Node (Port 5000)   |
                              |  - Web UI & Voting Portal|
                              |  - Vote Dispatcher       |
                              |  - Tallying / Analytics  |
                              +-------------+------------+
                                            |
         +-----------------+----------------+-----------------+-----------------+
         |                 |                |                 |                 |
         v                 v                v                 v                 v
   +------------+    +------------+   +------------+    +------------+    +------------+    +------------+
   |  Worker 1  |<-->|  Worker 2  |<->|  Worker 3  |<-->|  Worker 4  |<-->|  Worker 5  |<-->|  Worker 6  |
   | (Port 5001)|    | (Port 5002)|   | (Port 5003)|    | (Port 5004)|   | (Port 5005)|    | (Port 5006)|
   +------------+    +------------+   +------------+    +------------+    +------------+    +------------+
   <------------------------ P2P Synchronization & Consensus (PoW) ----------------------------------->
```

### 1. Master / Coordinator Node (Port 5000)
- **Fungsi Utama**:
  - Menyediakan portal web antarmuka untuk pemilih (*Client Interface*).
  - Melakukan validasi awal pemilih (mencegah duplikasi NIK/Token pemilih).
  - Meneruskan (*broadcast/dispatch*) suara ke antrean *mempool* worker nodes.
  - Memonitor kesehatan 6 Worker Nodes.
  - Menampilkan rekapitulasi (*tallying*) suara real-time & grafik hasil voting (Matplotlib).

### 2. 6 Worker Nodes (Port 5001 - 5006)
- **Fungsi Utama**:
  - Menyimpan salinan ledger blockchain lokal secara independen.
  - Menerima transaksi suara ke dalam *pending votes pool*.
  - Melakukan *mining* blok baru menggunakan algoritma Proof-of-Work (mencari nonce yang menghasilkan hash dengan *n* leading zeros).
  - Menerapkan mekanisme konsensus (*Longest Chain Rule*) untuk rekonsiliasi dan resolusi konflik jika terjadi *fork*.
  - Melakukan sinkronisasi antar peer (*Peer-to-Peer gossip*).

---

## 👥 Pembagian Tanggung Jawab Modul

| Modul | PIC / Penanggung Jawab | Deskripsi Tanggung Jawab |
| :--- | :--- | :--- |
| **`core/`** | **Safid** | Struktur data Block & Blockchain, Algoritma Hashing (SHA-256), Mekanisme Proof-of-Work (PoW), Algoritma Konsensus Resolusi Konflik, dan Modul Persistence Storage. |
| **`worker/`** | **Abyan** | REST API Worker Node (Flask), endpoint transaksi suara, endpoint mining PoW, sinkronisasi antar-worker, dan validasi rantai peer. |
| **`coordinator/`** | **Tim / Master** | Master REST API & Load Balancer/Dispatcher, Web Dashboard pemilu, agregasi rekapitulasi hasil voting (*tally*), dan visualisasi Matplotlib. |

---

## 📁 Struktur Direktori

```text
evoting-blockchain/
├── README.md                  # Dokumentasi proyek, arsitektur, dan panduan run
├── requirements.txt           # Daftar dependensi Python (Flask, requests, matplotlib)
├── .gitignore                 # Filter file build, cache, environment, dan data
├── core/                      # Modul inti Blockchain & Konsensus (Safid)
│   └── __init__.py            # Implementasi Block, Blockchain, PoW, & Storage
├── worker/                    # Modul REST API Worker Node (Abyan)
│   └── __init__.py            # Flask endpoints untuk worker node & mining
├── coordinator/               # Modul Master / Coordinator Node
│   └── __init__.py            # Flask endpoints untuk master node & web dashboard
└── data/                      # Direktori penyimpanan ledger lokal (di-generate otomatis)
```

---

## 🚀 Panduan Menjalankan Sistem

### Persyaratan Sistem
- Python 3.10+
- Pip (Python Package Manager)
- Docker & Docker Compose (Opsional untuk orkestrasi multi-container)

---

### Cara 1: Menjalankan Secara Lokal (Python Virtual Environment)

1. **Clone repositori dan masuk ke direktori proyek**:
   ```bash
   git clone https://github.com/muhamadabyanfurqan3-op/evoting-blockchain.git
   cd evoting-blockchain
   ```

2. **Buat dan aktifkan virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan 6 Worker Node di terminal terpisah (atau gunakan script runner)**:
   ```bash
   # Terminal 1 - Worker 1
   python -m worker --port 5001 --node-id worker-1

   # Terminal 2 - Worker 2
   python -m worker --port 5002 --node-id worker-2

   # Terminal 3 s/d 6 untuk Worker 3 (5003) s/d Worker 6 (5006)
   ```

5. **Jalankan Master / Coordinator Node**:
   ```bash
   # Terminal 7 - Coordinator Node
   python -m coordinator --port 5000
   ```

6. **Akses Dashboard**:
   Buka browser dan akses `http://localhost:5000`

---

### Cara 2: Menjalankan Menggunakan Docker Compose (Direkomendasikan untuk Simulasi Penuh)

Dalam fase deployment, sistem dapat dijalankan dengan 1 perintah:
```bash
docker-compose up --build
```
Hal ini akan secara otomatis mengangkat 1 container Coordinator dan 6 container Worker dalam satu jaringan bridge terisolasi.

---

## 🔒 Alur Konsensus & Validasi Voting
1. **Pemberian Suara**: Pemilih mengirimkan suara melalui Coordinator API (`POST /vote`).
2. **Distribusi Suara**: Coordinator menyebarkan data suara ke Worker Nodes (`POST /transactions/new`).
3. **Mining Kompetitif**: Worker bersaing memecahkan teka-teki kriptografis Proof-of-Work (`GET /mine`).
4. **Propagasi Blok**: Worker pertama yang berhasil menemukan *nonce* valid akan mempublikasikan blok baru ke seluruh peer worker.
5. **Verifikasi & Konsensus**: Tiap worker memverifikasi validitas blok. Jika terjadi percabangan (*fork*), aturan rantai terpanjang (*longest valid chain*) diberlakukan.
