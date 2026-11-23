# Kontrak REST API Flask

Dokumen ini mendefinisikan kontrak HTTP/JSON untuk simulasi e-voting. Coordinator berjalan pada port `5000`; Worker berjalan pada port `5001`–`5006`. Endpoint `/` pada Coordinator menyajikan dashboard HTML. Semua endpoint lainnya memakai JSON kecuali `/chart` yang mengembalikan PNG.

## Aturan umum

- Base URL lokal Coordinator: `http://localhost:5000`; Worker: `http://localhost:5001` (ganti port sesuai node).
- Request body harus berupa JSON dengan `Content-Type: application/json`.
- ID pemilih dikirim sebagai `voter_id`; kandidat sebagai `kandidat` (nama kanonis) atau `candidate_id` (alias kompatibilitas).
- Suara yang diterima endpoint transaksi berarti masuk ke mempool, belum final di ledger sampai blok berhasil ditambang dan disinkronkan.
- Format error JSON: `{"error":"..."}`. Status `400` menandakan payload/parameter salah, `409` konflik anti double-voting, `502` tidak ada Worker yang menerima suara, dan `500` kegagalan internal.

## Coordinator API (Master)

| Method & path | Fungsi | Sukses | Error utama |
|---|---|---|---|
| `GET /` | Dashboard web | `200 text/html` | — |
| `GET /workers` | Status setiap worker yang dikonfigurasi | `200` array status; node gagal memuat ditandai `offline` atau `error` | `200` tetap mengembalikan status parsial |
| `POST /vote` | Validasi input dan broadcast transaksi ke Worker | `200` dengan `message`, `success_nodes` | `400`, `409`, `502` |
| `POST /trigger-mining` | Minta semua Worker menambang lalu meminta resolusi rantai | `200` dengan `message`, `results` per node | Node gagal dicatat di `results` |
| `GET /tally` | Hitung suara dalam rantai terpanjang yang berhasil dibaca | `200` dengan `total_blocks`, `total_valid_votes`, `tally` | `200` dengan data kosong bila tidak ada chain yang bisa dibaca |
| `GET /chart` | Grafik tally | `200 image/png` | `500` JSON `error` |

### `POST /vote`

Request:

```json
{"voter_id":"VOTER-001","kandidat":"PASLON-01"}
```

`candidate_id` dapat menggantikan `kandidat`. Coordinator meneruskan kedua nama field ke Worker. Contoh sukses `200`:

```json
{"message":"Suara pemilih VOTER-001 berhasil dibroadcast ke 6 worker nodes.","success_nodes":["http://localhost:5001"]}
```

Jika data tidak lengkap/JSON invalid, respons `400`. Jika Worker mendeteksi ID pemilih sudah pernah memberikan suara, respons `409`. Jika tidak ada Worker yang menerima transaksi, respons `502` dengan `details`.

## Worker API

| Method & path | Fungsi | Sukses | Error utama |
|---|---|---|---|
| `GET /` | Identitas node dan daftar endpoint | `200` JSON service, `node_id`, `status`, `endpoints` | — |
| `GET /status` | Kesehatan dan ringkasan ledger/mempool/peer | `200` JSON | — |
| `GET /chain` | Salinan chain lokal | `200` JSON `node_id`, `chain`, `length` | — |
| `POST /transactions/new` | Validasi anti double-voting dan masukkan suara ke mempool | `201` JSON status `accepted` | `400`, `409` |
| `GET /mine` | Tambang pending votes dengan PoW dan broadcast blok | `200` JSON status `mined` atau `idle` | `500` kegagalan internal |
| `POST /nodes/register` | Daftarkan peer worker | `201` JSON `message`, `total_peers`, `peers` | `400` bila field `nodes` tidak ada |
| `GET /nodes/resolve` | Jalankan konsensus longest valid chain | `200` JSON `replaced`, `message`, `chain_length`, `last_block_hash` | `500` kegagalan internal |
| `POST /nodes/receive_block` | Terima blok propagasi | `200` jika ditambahkan, `202` jika memicu rekonsiliasi | `400` payload/format blok invalid |

### `POST /transactions/new`

Request:

```json
{"voter_id":"VOTER-001","kandidat":"PASLON-01"}
```

Respons diterima `201`:

```json
{"message":"...","voter_id":"VOTER-001","kandidat":"PASLON-01","target_block_index":2,"status":"accepted"}
```

Suara duplikat ditolak dengan `409` dan JSON `error`, `voter_id`, `status: "rejected"`. Payload tidak lengkap ditolak `400`.

### Struktur data chain dan blok

`GET /chain` mengembalikan array `chain`. Setiap blok mengikuti serialisasi `Block.to_dict()`:

```json
{"index":2,"timestamp":1730000000.0,"votes":[{"voter_id":"VOTER-001","kandidat":"PASLON-01"}],"previous_hash":"...","nonce":123,"hash":"...","miner_id":"worker-1"}
```

Field persis mengikuti model `core.Block`; klien sebaiknya mempertahankan field tambahan saat meneruskan blok ke `/nodes/receive_block`. Isi `votes` berisi transaksi yang telah dimasukkan ke blok, bukan suara yang masih pending.

## Alur integrasi

1. Client mengirim `POST /vote` ke Coordinator.
2. Coordinator mengirim `POST /transactions/new` ke Worker terkonfigurasi.
3. Coordinator meminta mining melalui `POST /trigger-mining`; tiap Worker menjalankan `GET /mine` lalu `GET /nodes/resolve`.
4. Worker menyebarkan blok memakai `POST /nodes/receive_block` dan mendaftarkan peer melalui `POST /nodes/register`.
5. Dashboard membaca `GET /workers` dan `GET /tally`; tally hanya mencakup suara di chain, bukan mempool.

## Catatan kesesuaian implementasi

- Kontrak ini mendokumentasikan perilaku kode saat ini. `GET /mine` mengubah state, tetapi dipertahankan sesuai endpoint implementasi; untuk API produksi operasi perubahan state idealnya memakai `POST`.
- Validasi kandidat terhadap daftar kandidat resmi belum dilakukan oleh endpoint; konsumen harus mengirim ID kandidat yang disepakati proyek.
- Coordinator menandai vote sukses bila sekurangnya satu Worker menerima transaksi. Respons `200` tidak menjamin semua Worker menerima atau bahwa suara telah ditambang.
- Kode Worker mengembalikan `202` untuk blok yang tidak cocok langsung dan memicu resolusi; ini bukan bukti bahwa blok tersebut sudah diterapkan.
