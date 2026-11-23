# Spesifikasi Arsitektur & Alur Sistem (EVB-02)
## Simulasi Sistem Voting Digital Terdistribusi Berbasis Proof-of-Work, Python Flask, dan Docker

**Penyusun:** Safid Nasih Ulwan (Senior Distributed Systems & Blockchain Engineer)  
**Mata Kuliah:** Komputasi Paralel dan Terdistribusi (KPT) - Semester 5  
**Proyek:** E-Voting Blockchain (EVB-02)

---

## 1. Ringkasan Eksekutif & Topologi Jaringan

Sistem *E-Voting Blockchain* ini dirancang dengan arsitektur **Master-Worker terdistribusi** yang berjalan di dalam jaringan virtual terisolasi (**Docker Bridge Network**) dengan persistensi data independen untuk setiap node (**Docker Named/Mounted Volumes**).

### Komponen Arsitektur:
1. **1 Master / Coordinator Node (Port 5000)**:
   - Gerbang utama pemilih (*Voting Web Portal*).
   - *Load Balancer* dan *Transaction Dispatcher* yang menyebarkan transaksi suara pemilih ke mempool worker.
   - Monitor kesehatan cluster worker dan agregator rekapitulasi hasil pemilu (*Tallying Engine*).
2. **6 Worker Blockchain Nodes (Port 5001 s.d. 5006)**:
   - Beroperasi sebagai *mining node* peer-to-peer (P2P).
   - Menjaga integritas *ledger* lokal secara independen.
   - Melakukan kompetisi Proof-of-Work (PoW) dengan kesulitan *4 leading zeros* (`"0000"`).
   - Menerapkan mekanisme konsensus *Longest Valid Chain* untuk rekonsiliasi percabangan rantai (*fork resolution*).
3. **Docker Storage Volumes (`/app/data`)**:
   - Volume terpisah untuk setiap container worker (`./data/worker-1` s.d. `./data/worker-6`) untuk menjamin sifat *Fault Tolerance* (node tetap mempertahankan ledger saat container restart/crash).

---

## 2. Diagram Topologi Jaringan Docker

Diagram berikut mengilustrasikan interkoneksi Master Node dan 6 Worker Nodes dalam lingkungan Docker:

```mermaid
flowchart TD
    subgraph ClientLayer["Klien & Antarmuka Pemilih"]
        Voter["Pemilih (Web Browser / REST Client)"]
    end

    subgraph DockerBridge["Docker Network: evoting-net (Bridge)"]
        subgraph MasterCluster["Master / Coordinator Layer"]
            Coordinator["Coordinator Node (Port 5000)<br/>- Web UI Portal<br/>- Vote Dispatcher<br/>- Tallying Aggregator"]
        end

        subgraph WorkerCluster["Distributed Worker Nodes (Mining & Ledger)"]
            W1["Worker 1 (Port 5001)<br/>Mining & Ledger"]
            W2["Worker 2 (Port 5002)<br/>Mining & Ledger"]
            W3["Worker 3 (Port 5003)<br/>Mining & Ledger"]
            W4["Worker 4 (Port 5004)<br/>Mining & Ledger"]
            W5["Worker 5 (Port 5005)<br/>Mining & Ledger"]
            W6["Worker 6 (Port 5006)<br/>Mining & Ledger"]
        end
    end

    subgraph StorageLayer["Docker Volumes (Persistent Storage)"]
        Vol1[("Volume: data/worker-1")]
        Vol2[("Volume: data/worker-2")]
        Vol3[("Volume: data/worker-3")]
        Vol4[("Volume: data/worker-4")]
        Vol5[("Volume: data/worker-5")]
        Vol6[("Volume: data/worker-6")]
    end

    Voter -->|"HTTP POST /vote"| Coordinator
    Coordinator -->|"HTTP POST /transactions/new"| W1
    Coordinator -->|"HTTP POST /transactions/new"| W2
    Coordinator -->|"HTTP POST /transactions/new"| W3
    Coordinator -->|"HTTP POST /transactions/new"| W4
    Coordinator -->|"HTTP POST /transactions/new"| W5
    Coordinator -->|"HTTP POST /transactions/new"| W6

    W1 <-->|"P2P Gossip & Consensus"| W2
    W2 <-->|"P2P Gossip & Consensus"| W3
    W3 <-->|"P2P Gossip & Consensus"| W4
    W4 <-->|"P2P Gossip & Consensus"| W5
    W5 <-->|"P2P Gossip & Consensus"| W6
    W6 <-->|"P2P Gossip & Consensus"| W1

    W1 --- Vol1
    W2 --- Vol2
    W3 --- Vol3
    W4 --- Vol4
    W5 --- Vol5
    W6 --- Vol6
```

---

## 3. Alur Transaksi Suara & Validasi Anti Double-Voting

Setiap suara yang dikirimkan pemilih melewati dua lapis validasi ketat sebelum dapat masuk ke dalam rantai blok:

```mermaid
sequenceDiagram
    autonumber
    actor Voter as Pemilih
    participant Coord as Coordinator Node (Port 5000)
    participant W as Worker Node (Port 500X)
    participant Mempool as Pending Mempool
    participant Ledger as Immutable Ledger (Chain)

    Voter->>Coord: POST /vote {"voter_id": "MHS001", "kandidat": "PASLON-01"}
    Coord->>W: POST /transactions/new {"voter_id": "MHS001", "kandidat": "PASLON-01"}
    
    Note over W: Pengecekan Anti Double-Voting
    W->>Mempool: Cek apakah voter_id sudah ada di antrean?
    alt Sudah ada di Mempool
        W-->>Coord: HTTP 409 Conflict ("Voter sudah di antrean")
        Coord-->>Voter: Tolak suara ("Double-voting terdeteksi")
    else Belum ada di Mempool
        W->>Ledger: Cek seluruh blok di Chain (Genesis s.d. Puncak)
        alt Sudah ada di Ledger
            W-->>Coord: HTTP 409 Conflict ("Voter sudah tercatat di Blok #N")
            Coord-->>Voter: Tolak suara ("Double-voting terdeteksi")
        else Belum pernah memilih sama sekali
            W->>Mempool: Tambahkan transaksi suara sah
            W-->>Coord: HTTP 201 Created ("Suara sah diterima di mempool")
            Coord-->>Voter: HTTP 200 OK ("Suara Anda berhasil tercatat")
        end
    end
```

---

## 4. Alur Algoritma Proof-of-Work (PoW) SHA-256

Worker menambang transaksi suara menggunakan algoritma hash SHA-256 dengan target tingkat kesulitan (*difficulty*) 4:

```mermaid
flowchart TD
    StartMining(["Mulai Mining: GET /mine"]) --> CheckPool{"Apakah Pending Mempool kosong?"}
    CheckPool -- "Ya" --> NoOp["Kembalikan status Idle (Tidak ada transaksi)"]
    CheckPool -- "Tidak" --> PrepBlock["Siapkan Blok Baru:<br/>- index = last_block.index + 1<br/>- previous_hash = last_block.hash<br/>- votes = copy(pending_votes)<br/>- nonce = 0"]
    
    PrepBlock --> HashCalc["Hitung SHA-256:<br/>hash = SHA256(index + timestamp + votes + previous_hash + nonce)"]
    HashCalc --> CheckDiff{"Apakah hash berawalan '0000'?"}
    
    CheckDiff -- "Tidak" --> IncNonce["nonce = nonce + 1"]
    IncNonce --> HashCalc
    
    CheckDiff -- "Ya (Target Tercapai)" --> SealBlock["Kunci Blok Baru:<br/>block.hash = hash"]
    SealBlock --> AppendChain["Tambahkan Blok ke Chain Lokal"]
    AppendChain --> ClearPool["Kosongkan Pending Mempool Lokal"]
    ClearPool --> SaveDisk["Simpan State Atomik ke Docker Volume"]
    SaveDisk --> Broadcast["Sebarkan Blok Baru (Block Propagation ke Seluruh Peer)"]
    Broadcast --> Done(["Mining Selesai"])
```

---

## 5. Alur Konsensus Terdistribusi (Longest Valid Chain Rule)

Ketika salah satu node menambang blok baru atau ketika terjadi percabangan (*fork*), konsensus dijalankan untuk merekonsiliasi seluruh node ke satu kebenaran tunggal (*single source of truth*):

```mermaid
sequenceDiagram
    autonumber
    participant W_Miner as Worker 1 (Penambang Sukses)
    participant W_Peer as Worker 2..6 (Peers)
    participant Disk as Docker Volume

    Note over W_Miner: Berhasil menemukan Nonce valid (Hash '0000...')
    W_Miner->>W_Peer: POST /nodes/receive_block {New Block Payload}
    
    alt Blok cocok langsung dengan last_block peer
        Note over W_Peer: Validasi: index = last+1, prev_hash cocok, PoW sah
        W_Peer->>W_Peer: Append blok ke chain lokal
        W_Peer->>Disk: Simpan update chain ke storage
        W_Peer-->>W_Miner: HTTP 200 OK (Blok diterima)
    else Terjadi perbedaan panjang rantai / Fork
        Note over W_Peer: Panggil resolve_conflicts()
        W_Peer->>W_Miner: GET /chain
        W_Miner-->>W_Peer: Data Rantai Lengkap (Panjang = N)
        Note over W_Peer: Validasi seluruh rantai kandidat (PoW & Anti Double-Voting)
        alt Rantai kandidat sah dan lebih panjang
            W_Peer->>W_Peer: Timpa rantai lokal dengan rantai konsensus
            W_Peer->>W_Peer: Bersihkan pending mempool dari suara yang sudah masuk blok
            W_Peer->>Disk: Persistensikan rantai konsensus ke Docker Volume
        else Rantai kandidat tidak valid
            Note over W_Peer: Tolak rantai, pertahankan rantai lokal
        end
    end
```

---

## 6. Tabel Spesifikasi Endpoint REST API

| Modul | Endpoint | Method | Fungsi Utama | Status Response |
| :--- | :--- | :---: | :--- | :--- |
| **Coordinator** | `/` | `GET` | Antarmuka web voting dan status real-time cluster | `200 OK` (HTML) |
| **Coordinator** | `/vote` | `POST` | Menerima suara pemilih dan broadcast ke worker nodes | `200 OK` / `409 Conflict` |
| **Coordinator** | `/workers` | `GET` | Health check 6 worker container | `200 OK` (JSON) |
| **Coordinator** | `/trigger-mining` | `POST` | Menginstruksikan worker untuk menambang | `200 OK` (JSON) |
| **Coordinator** | `/tally` | `GET` | Rekapitulasi perolehan suara terverifikasi | `200 OK` (JSON) |
| **Coordinator** | `/chart` | `GET` | Gambar visualisasi grafik perolehan suara | `200 OK` (Image PNG) |
| **Worker** | `/status` | `GET` | Status node, panjang rantai, pending mempool, hash | `200 OK` (JSON) |
| **Worker** | `/chain` | `GET` | Salinan seluruh rantai blok lokal | `200 OK` (JSON) |
| **Worker** | `/transactions/new` | `POST` | Input transaksi suara baru + Anti Double-Voting | `201 Created` / `409 Conflict` |
| **Worker** | `/mine` | `GET` | Eksekusi Proof-of-Work SHA-256 | `200 OK` (JSON) |
| **Worker** | `/nodes/receive_block`| `POST` | Menerima blok baru hasil propagasi peer | `200 OK` / `202 Accepted` |
| **Worker** | `/nodes/resolve` | `GET` | Eksekusi konsensus Longest Valid Chain | `200 OK` (JSON) |
| **Worker** | `/nodes/register` | `POST` | Mendaftarkan alamat URL peer tetangga | `201 Created` (JSON) |
