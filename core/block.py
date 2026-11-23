"""
Modul Struktur Blok Blockchain E-Voting
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional


class Block:
    """
    Kelas representasi Blok dalam Blockchain E-Voting.

    Atribut:
        index (int): Posisi nomor urut blok dalam blockchain (dimulai dari 1 untuk Genesis).
        timestamp (float): Unix timestamp saat blok diciptakan.
        votes (List[Dict[str, Any]]): Daftar transaksi suara pemilih, masing-masing
                                      berisi minimal 'voter_id' dan 'kandidat'.
        previous_hash (str): Hash kriptografis SHA-256 dari blok sebelumnya (membentuk rantai).
        nonce (int): Nilai acak yang diiterasi dalam Proof-of-Work untuk memenuhi target difficulty.
        hash (str): Hash SHA-256 yang valid dari blok ini (diawali target '0000').
    """

    def __init__(
        self,
        index: int,
        timestamp: float,
        votes: List[Dict[str, Any]],
        previous_hash: str,
        nonce: int = 0,
        block_hash: Optional[str] = None,
    ) -> None:
        self.index: int = index
        self.timestamp: float = timestamp
        self.votes: List[Dict[str, Any]] = votes
        self.previous_hash: str = previous_hash
        self.nonce: int = nonce
        self.hash: str = block_hash if block_hash is not None else self.compute_hash()

    def compute_hash(self) -> str:
        """
        Menghitung nilai SHA-256 hash dari konten blok.
        
        Kunci payload diurutkan (`sort_keys=True`) agar serialisasi JSON menghasilkan
        representasi string yang deterministik di semua arsitektur dan sistem operasi.
        """
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        encoded_block = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_block).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Mengonversi objek Block ke bentuk dictionary yang serializable ke format JSON."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        """
        Membuat instansiasi objek Block dari dictionary data JSON.
        
        Mendukung pemulihan data persisten dari Docker Volume atau komunikasi REST API.
        """
        return cls(
            index=int(data["index"]),
            timestamp=float(data["timestamp"]),
            votes=list(data.get("votes", [])),
            previous_hash=str(data["previous_hash"]),
            nonce=int(data.get("nonce", data.get("proof", 0))),
            block_hash=data.get("hash"),
        )

    def __repr__(self) -> str:
        return (
            f"<Block #{self.index} [Hash: {self.hash[:10]}...] "
            f"Votes: {len(self.votes)} | Nonce: {self.nonce}>"
        )
