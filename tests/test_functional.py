"""
Script Pengujian Fungsional End-to-End (E2E) E-Voting Blockchain
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)

Mendukung 2 mode pengujian:
1. Mode HTTP E2E: Menguji cluster 1 Coordinator + 6 Worker Nodes (Docker / Lokal).
2. Mode Standalone (--standalone): Menguji logika Core (Anti Double-Voting, PoW, Storage, Consensus)
   langsung pada level class Python tanpa membutuhkan server aktif.
"""

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Tambahkan root proyek ke sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import requests
except ImportError:
    requests = None

# ANSI Color codes untuk output terminal yang profesional
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_pass(message: str) -> None:
    print(f"{GREEN}[PASS]{RESET} {message}")


def log_fail(message: str) -> None:
    print(f"{RED}[FAIL]{RESET} {message}")


def log_info(message: str) -> None:
    print(f"{CYAN}[INFO]{RESET} {message}")


def log_warn(message: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {message}")


# ==============================================================================
# 1. PENGUJIAN HTTP E2E (TERHADAP 6 WORKER & 1 COORDINATOR)
# ==============================================================================
def test_e2e_cluster(coordinator_url: str, worker_urls: List[str]) -> bool:
    """Menjalankan 5 skenario pengujian fungsional pada cluster REST API."""
    print(f"\n{BOLD}{CYAN}=== MEMULAI PENGUJIAN FUNGSIONAL E2E CLUSTER DOCKER ==={RESET}\n")
    all_passed = True

    # --------------------------------------------------------------------------
    # SKENARIO 1: Verifikasi Koneksi & Status Seluruh Node
    # --------------------------------------------------------------------------
    log_info(f"Skenario 1: Verifikasi kesehatan Coordinator ({coordinator_url}) dan 6 Worker Nodes...")
    active_workers: List[str] = []

    # Cek Coordinator
    try:
        res_coord = requests.get(f"{coordinator_url}/workers", timeout=3.0)
        if res_coord.status_code == 200:
            log_pass(f"Coordinator aktif dan merespons: {coordinator_url}")
        else:
            log_warn(f"Coordinator merespons HTTP {res_coord.status_code}")
    except requests.RequestException as e:
        log_warn(f"Coordinator tidak terjangkau di {coordinator_url}: {e}")

    # Cek Tiap Worker
    for w_url in worker_urls:
        try:
            res = requests.get(f"{w_url}/status", timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                log_pass(
                    f"Worker {w_url} ONLINE | Node ID: {data.get('node_id')} | "
                    f"Chain Length: {data.get('chain_length')} | Hash: {data.get('last_block_hash', '')[:10]}..."
                )
                active_workers.append(w_url)
            else:
                log_fail(f"Worker {w_url} merespons HTTP {res.status_code}")
                all_passed = False
        except requests.RequestException:
            log_fail(f"Worker {w_url} OFFLINE (koneksi gagal)")
            all_passed = False

    if len(active_workers) < len(worker_urls):
        log_warn(f"Hanya {len(active_workers)}/{len(worker_urls)} worker yang aktif.")

    # Daftarkan seluruh peer antar-worker jika belum terdaftar
    log_info("Menyinkronkan daftar peer antar-seluruh worker yang aktif...")
    for w_url in active_workers:
        peers_to_register = [p for p in active_workers if p != w_url]
        try:
            requests.post(f"{w_url}/nodes/register", json={"nodes": peers_to_register}, timeout=2.0)
        except requests.RequestException:
            pass

    # --------------------------------------------------------------------------
    # SKENARIO 2: Kirim Transaksi Suara Valid
    # --------------------------------------------------------------------------
    primary_worker = active_workers[0] if active_workers else worker_urls[0]
    log_info(f"\nSkenario 2: Mengirim transaksi suara valid ke {primary_worker}...")
    valid_vote = {"voter_id": "MHS001", "kandidat": "PASLON-01"}

    try:
        res = requests.post(f"{primary_worker}/transactions/new", json=valid_vote, timeout=3.0)
        if res.status_code == 201:
            log_pass(f"Suara valid berhasil diterima: {res.json().get('message')}")
        else:
            log_fail(f"Pengiriman suara valid gagal: HTTP {res.status_code} - {res.text}")
            all_passed = False
    except requests.RequestException as e:
        log_fail(f"Gagal mengirim suara valid: {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # SKENARIO 3: Uji Validasi Anti Double-Voting (Harus Ditolak!)
    # --------------------------------------------------------------------------
    log_info("\nSkenario 3: Uji Anti Double-Voting dengan mengirim ulang voter_id 'MHS001'...")
    duplicate_vote = {"voter_id": "MHS001", "kandidat": "PASLON-02"}

    try:
        # Coba kirim ke worker yang sama
        res_dup = requests.post(f"{primary_worker}/transactions/new", json=duplicate_vote, timeout=3.0)
        if res_dup.status_code == 409:
            log_pass(f"Sistem BERHASIL MENOLAK double-voting di mempool: {res_dup.json().get('error')}")
        else:
            log_fail(f"Sistem GAGAL menolak double-voting! HTTP {res_dup.status_code}: {res_dup.text}")
            all_passed = False
    except requests.RequestException as e:
        log_fail(f"Gagal melakukan pengujian anti double-voting: {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # SKENARIO 4: Jalankan Mining Proof-of-Work (Target Hash '0000')
    # --------------------------------------------------------------------------
    log_info(f"\nSkenario 4: Memulai proses mining PoW SHA-256 pada {primary_worker}...")
    try:
        res_mine = requests.get(f"{primary_worker}/mine", timeout=15.0)
        if res_mine.status_code == 200:
            mine_data = res_mine.json()
            block_info = mine_data.get("block", {})
            block_hash = block_info.get("hash", "")
            nonce = block_info.get("nonce", 0)

            if block_hash.startswith("0000"):
                log_pass(
                    f"Mining PoW SUKSES! Hash Blok #{block_info.get('index')} diawali '0000'!\n"
                    f"         Hash : {block_hash}\n"
                    f"         Nonce: {nonce}"
                )
            else:
                log_fail(f"Hash tidak diawali '0000': {block_hash}")
                all_passed = False
        else:
            log_fail(f"Mining gagal: HTTP {res_mine.status_code} - {res_mine.text}")
            all_passed = False
    except requests.RequestException as e:
        log_fail(f"Koneksi mining timeout/gagal: {e}")
        all_passed = False

    # --------------------------------------------------------------------------
    # SKENARIO 5: Konsensus & Sinkronisasi Longest Valid Chain ke Seluruh 6 Node
    # --------------------------------------------------------------------------
    log_info("\nSkenario 5: Menjalankan konsensus resolusi konflik ke seluruh worker...")
    for w_url in active_workers:
        try:
            res_resolve = requests.get(f"{w_url}/nodes/resolve", timeout=5.0)
            if res_resolve.status_code == 200:
                data = res_resolve.json()
                log_pass(f"Resolusi {w_url}: {data.get('message')} (Panjang: {data.get('chain_length')})")
        except requests.RequestException as e:
            log_warn(f"Gagal menghubungi {w_url} untuk konsensus: {e}")

    # Verifikasi konsistensi ledger antar-seluruh node aktif
    log_info("\nVerifikasi Integritas Rantai Antar-Semua Worker Aktif:")
    chain_hashes: Dict[str, str] = {}
    chain_lengths: Dict[str, int] = {}

    for w_url in active_workers:
        try:
            res_stat = requests.get(f"{w_url}/status", timeout=2.0)
            if res_stat.status_code == 200:
                st = res_stat.json()
                chain_hashes[w_url] = st.get("last_block_hash", "")
                chain_lengths[w_url] = st.get("chain_length", 0)
        except requests.RequestException:
            pass

    unique_hashes = set(chain_hashes.values())
    unique_lengths = set(chain_lengths.values())

    if len(unique_hashes) == 1 and len(unique_lengths) == 1 and len(active_workers) > 0:
        log_pass(
            f"KONSENSUS SEMPURNA: Seluruh {len(active_workers)} worker memiliki panjang rantai "
            f"({list(unique_lengths)[0]} blok) dan hash puncak yang 100% IDENTIK!\n"
            f"         Hash Puncak: {list(unique_hashes)[0]}"
        )
    else:
        log_fail(
            f"INKONSISTENSI KONSENSUS DITEMUKAN!\n"
            f"Hashes: {chain_hashes}\nLengths: {chain_lengths}"
        )
        all_passed = False

    # --------------------------------------------------------------------------
    # SKENARIO TAMBAHAN: Uji Anti Double-Voting Post-Mining
    # --------------------------------------------------------------------------
    log_info("\nSkenario Tambahan: Uji Anti Double-Voting setelah transaksi masuk ke blok...")
    try:
        res_post = requests.post(f"{primary_worker}/transactions/new", json={"voter_id": "MHS001", "kandidat": "PASLON-03"}, timeout=3.0)
        if res_post.status_code == 409:
            log_pass(f"Anti Double-Voting pada Ledger terverifikasi: {res_post.json().get('error')}")
        else:
            log_fail(f"Gagal mendeteksi double-voting pada ledger permanen! HTTP {res_post.status_code}")
            all_passed = False
    except requests.RequestException as e:
        log_warn(f"Request gagal: {e}")

    return all_passed


# ==============================================================================
# 2. PENGUJIAN STANDALONE CORE (OFFLINE UNIT TESTING)
# ==============================================================================
def test_standalone_core() -> bool:
    """Menguji modul Core (Block, Storage, Blockchain, PoW, Anti Double-Voting) tanpa HTTP server."""
    print(f"\n{BOLD}{CYAN}=== MEMULAI PENGUJIAN STANDALONE CORE BLOCKCHAIN ==={RESET}\n")
    import os
    import shutil
    import tempfile
    from core import Block, Blockchain, LedgerStorage

    temp_data_dir = tempfile.mkdtemp(prefix="test_evoting_")
    all_passed = True

    try:
        # 1. Test Block Creation & Compute Hash
        log_info("Test 1: Pengujian Block & Deterministic Hashing...")
        b = Block(
            index=1,
            timestamp=1700000000.0,
            votes=[{"voter_id": "V1", "kandidat": "K1"}],
            previous_hash="0" * 64,
            nonce=42,
        )
        computed = b.compute_hash()
        assert computed == b.hash, "Hash compute_hash harus sama dengan block.hash"
        b_dict = b.to_dict()
        b_restored = Block.from_dict(b_dict)
        assert b_restored.hash == b.hash, "Restorasi dari dict harus mempertahankan hash"
        log_pass("Class Block & hashing SHA-256 terurut bekerja dengan baik.")

        # 2. Test Blockchain Initialization & Genesis
        log_info("Test 2: Pengujian Blockchain Genesis Block & Difficulty 4...")
        bc1 = Blockchain(node_id="test-worker-1", difficulty=4, data_dir=temp_data_dir)
        assert len(bc1.chain) == 1, "Rantai awal harus berisi 1 Genesis Block"
        assert bc1.last_block.hash.startswith("0000"), "Hash Genesis Block harus diawali '0000'"
        log_pass(f"Genesis Block valid dengan hash: {bc1.last_block.hash}")

        # 3. Test Anti Double-Voting (Mempool & Ledger)
        log_info("Test 3: Pengujian Validasi Anti Double-Voting...")
        # Input vote pertama -> harus sukses
        ok1, msg1 = bc1.add_vote(voter_id="MHS100", kandidat="PASLON-01")
        assert ok1 is True, "Vote pertama harus sah dan diterima"
        log_pass("Transaksi suara pertama berhasil diterima.")

        # Input vote kedua dengan voter_id sama -> harus ditolak
        ok2, msg2 = bc1.add_vote(voter_id="MHS100", kandidat="PASLON-02")
        assert ok2 is False, "Double-voting pada mempool harus ditolak"
        assert "PENOLAKAN ANTI DOUBLE-VOTING" in msg2
        log_pass(f"Double-voting di mempool berhasil ditolak: {msg2}")

        # 4. Test Proof-of-Work & Mining
        log_info("Test 4: Pengujian Mining PoW SHA-256...")
        new_block, mine_msg = bc1.mine_pending_votes(miner_id="test-miner")
        assert new_block is not None, "Mining harus menghasilkan blok baru"
        assert new_block.index == 2, "Blok baru harus memiliki indeks 2"
        assert new_block.hash.startswith("0000"), "Hash blok baru harus berawalan '0000'"
        assert len(bc1.pending_votes) == 0, "Mempool harus dikosongkan setelah mining"
        log_pass(f"Mining PoW sukses: Blok #{new_block.index} Nonce={new_block.nonce} Hash={new_block.hash}")

        # Input vote ketiga dengan voter_id sama setelah masuk ke blok -> harus ditolak
        ok3, msg3 = bc1.add_vote(voter_id="MHS100", kandidat="PASLON-03")
        assert ok3 is False, "Double-voting pada ledger blockchain harus ditolak"
        assert "PENOLAKAN ANTI DOUBLE-VOTING" in msg3
        log_pass(f"Double-voting di ledger berhasil ditolak: {msg3}")

        # 5. Test Persistence & Storage Recovery
        log_info("Test 5: Pengujian Persistence Storage (Docker Volume Emulation)...")
        # Buat instansiasi blockchain kedua pada direktori yang sama
        bc2 = Blockchain(node_id="test-worker-1", difficulty=4, data_dir=temp_data_dir)
        assert len(bc2.chain) == 2, "Blockchain kedua harus berhasil me-load 2 blok dari disk"
        assert bc2.last_block.hash == bc1.last_block.hash, "Hash blok terakhir harus sama persis"
        log_pass("Persistensi data JSON pada disk berhasil dimuat dan valid.")

        # 6. Test Chain Validation & Tamper Resistance
        log_info("Test 6: Pengujian Integritas Rantai & Tamper Resistance...")
        assert bc2.is_valid_chain(bc2.chain) is True, "Rantai orisinal harus valid"
        # Manipulasi data secara sengaja
        fake_block = Block(
            index=3,
            timestamp=time.time(),
            votes=[{"voter_id": "HACKER", "kandidat": "PASLON-99"}],
            previous_hash=bc2.last_block.hash,
            nonce=123,
            block_hash="0000fakehash1234567890abcdef",
        )
        fake_chain = list(bc2.chain) + [fake_block]
        assert bc2.is_valid_chain(fake_chain) is False, "Rantai palsu dengan hash palsu harus ditolak"
        log_pass("Verifikasi rantai berhasil mendeteksi dan menolak blok palsu.")

    except AssertionError as ae:
        log_fail(f"Assertion gagal: {ae}")
        all_passed = False
    except Exception as exc:
        log_fail(f"Terjadi error tak terduga: {exc}")
        all_passed = False
    finally:
        shutil.rmtree(temp_data_dir, ignore_errors=True)

    return all_passed


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Script Pengujian Fungsional E-Voting Blockchain.")
    parser.add_argument("--coordinator", type=str, default="http://localhost:5000", help="URL Coordinator Node")
    parser.add_argument(
        "--workers",
        nargs="+",
        default=[
            "http://localhost:5001",
            "http://localhost:5002",
            "http://localhost:5003",
            "http://localhost:5004",
            "http://localhost:5005",
            "http://localhost:5006",
        ],
        help="Daftar URL Worker Nodes",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Jalankan pengujian unit core internal langsung tanpa memerlukan HTTP server aktif.",
    )
    args = parser.parse_args()

    success = False
    if args.standalone or requests is None:
        if requests is None and not args.standalone:
            log_warn("Library 'requests' belum terinstall di Python host. Menjalankan mode Standalone...")
        success = test_standalone_core()
    else:
        # Coba koneksi ke worker pertama, jika tidak aktif otomatis fallback atau jalankan
        try:
            requests.get(f"{args.workers[0]}/status", timeout=1.0)
            success = test_e2e_cluster(coordinator_url=args.coordinator, worker_urls=args.workers)
        except requests.RequestException:
            log_warn(f"Server {args.workers[0]} tidak terdeteksi aktif.")
            log_info("Beralih otomatis menjalankan Pengujian Standalone Core...")
            success = test_standalone_core()

    if success:
        print(f"\n{BOLD}{GREEN}>>> SELURUH PENGUJIAN BERHASIL LULUS 100% (TESTS PASSED) <<<{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{BOLD}{RED}>>> BEBERAPA PENGUJIAN MENGALAMI KEGAGALAN (TESTS FAILED) <<<{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
