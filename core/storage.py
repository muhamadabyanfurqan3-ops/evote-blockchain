"""
Modul Penyimpanan Persisten Blockchain (Docker Volume Safe)
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import json
import os
import shutil
import tempfile
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from .block import Block


class LedgerStorage:
    """
    Kelas penanganan penyimpanan persisten blockchain ke Docker Volume / Disk lokal.
    
    Fitur Utama:
    1. Thread-safe: Menggunakan threading.Lock() untuk mencegah race condition
       antar-request Flask.
    2. Atomic Writes: Menulis ke temporary file sebelum menimpa berkas utama,
       mencegah file JSON corrupt saat crash atau interupsi container.
    3. Docker Volume Support: Path data dapat dikonfigurasi melalui environment
       variable `DATA_DIR` (default: './data').
    """

    def __init__(self, node_id: str = "worker-1", data_dir: Optional[str] = None) -> None:
        self.node_id: str = node_id
        # Prioritas path direktori: argumen eksplisit -> ENV DATA_DIR -> default './data'
        base_dir = data_dir or os.environ.get("DATA_DIR", "./data")
        self.node_dir: str = os.path.join(base_dir, self.node_id)
        self.ledger_file: str = os.path.join(self.node_dir, "ledger.json")
        self._lock: threading.Lock = threading.Lock()

        # Pastikan direktori penyimpanan tersedia
        os.makedirs(self.node_dir, exist_ok=True)

    def save_state(
        self,
        chain: List[Block],
        pending_votes: List[Dict[str, Any]],
        peers: Set[str],
    ) -> bool:
        """
        Menyimpan kondisi blockchain saat ini (chain, pending_votes, peers) ke disk secara thread-safe.
        
        Menggunakan teknik atomic file replacement untuk menjamin integritas data ACID-like.
        """
        payload = {
            "node_id": self.node_id,
            "chain": [block.to_dict() for block in chain],
            "pending_votes": pending_votes,
            "peers": sorted(list(peers)),
        }

        with self._lock:
            temp_file_path: Optional[str] = None
            try:
                # Tulis terlebih dahulu ke berkas temporer di direktori yang sama
                with tempfile.NamedTemporaryFile(
                    "w", dir=self.node_dir, delete=False, encoding="utf-8"
                ) as tmp:
                    temp_file_path = tmp.name
                    json.dump(payload, tmp, indent=2, sort_keys=True)
                    tmp.flush()
                    os.fsync(tmp.fileno())

                # Ganti berkas target secara atomik
                shutil.move(temp_file_path, self.ledger_file)
                return True
            except Exception as exc:
                print(f"[LedgerStorage ERROR] Gagal menyimpan state node {self.node_id}: {exc}")
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass
                return False

    def load_state(self) -> Tuple[List[Block], List[Dict[str, Any]], Set[str]]:
        """
        Memuat data persisten dari Docker Volume.
        
        Mengembalikan tuple: (chain, pending_votes, peers).
        Jika berkas belum ada atau rusak, mengembalikan struktur kosong.
        """
        with self._lock:
            if not os.path.exists(self.ledger_file):
                return [], [], set()

            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                raw_chain = data.get("chain", [])
                chain = [Block.from_dict(b) for b in raw_chain]
                pending_votes = data.get("pending_votes", [])
                peers = set(data.get("peers", []))

                print(
                    f"[LedgerStorage INFO] Node {self.node_id} berhasil memuat {len(chain)} blok, "
                    f"{len(pending_votes)} pending votes, dan {len(peers)} peers dari disk."
                )
                return chain, pending_votes, peers
            except (json.JSONDecodeError, KeyError, Exception) as exc:
                print(f"[LedgerStorage WARNING] Gagal memuat ledger file {self.ledger_file}: {exc}")
                return [], [], set()
