"""
Core Module: Blockchain, Proof-of-Work, Consensus Mechanism, & Storage
Penanggung Jawab: Safid
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
import requests


class Block:
    """Representasi struktur blok dalam Blockchain."""

    def __init__(
        self,
        index: int,
        timestamp: float,
        votes: List[Dict[str, Any]],
        proof: int,
        previous_hash: str,
        block_hash: Optional[str] = None,
    ):
        self.index = index
        self.timestamp = timestamp
        self.votes = votes
        self.proof = proof
        self.previous_hash = previous_hash
        self.hash = block_hash or self.calculate_hash()

    def calculate_hash(self) -> str:
        """Menghitung SHA-256 hash dari data blok."""
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "votes": self.votes,
                "proof": self.proof,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Konversi objek Block ke format dictionary serializable."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes": self.votes,
            "proof": self.proof,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        """Membangun objek Block dari dictionary."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            votes=data["votes"],
            proof=data["proof"],
            previous_hash=data["previous_hash"],
            block_hash=data.get("hash"),
        )


class StorageManager:
    """Manajer penyimpanan persisten blockchain ke disk (JSON format)."""

    def __init__(self, data_dir: str = "data", filename: str = "blockchain.json"):
        self.data_dir = data_dir
        self.filepath = os.path.join(self.data_dir, filename)
        os.makedirs(self.data_dir, exist_ok=True)

    def save_chain(self, chain: List[Block]) -> bool:
        """Menyimpan list Block ke file JSON."""
        try:
            serialized_chain = [block.to_dict() for block in chain]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(serialized_chain, f, indent=4)
            return True
        except IOError as e:
            print(f"[StorageManager] Gagal menyimpan blockchain: {e}")
            return False

    def load_chain(self) -> Optional[List[Block]]:
        """Memuat list Block dari file JSON jika tersedia."""
        if not os.path.exists(self.filepath):
            return None
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                return [Block.from_dict(b) for b in raw_data]
        except (IOError, json.JSONDecodeError) as e:
            print(f"[StorageManager] Gagal memuat blockchain: {e}")
            return None


class Blockchain:
    """
    Kelas utama Blockchain dengan algoritma Proof-of-Work (PoW)
    dan mekanisme konsensus rantai terpanjang (Longest Chain Rule).
    """

    DEFAULT_DIFFICULTY = 4  # Mengharuskan hash berawalan sejumlah nol

    def __init__(
        self,
        node_identifier: str = "default_node",
        difficulty: int = DEFAULT_DIFFICULTY,
        storage_enabled: bool = True,
    ):
        self.node_identifier = node_identifier
        self.difficulty = difficulty
        self.current_votes: List[Dict[str, Any]] = []
        self.chain: List[Block] = []
        self.nodes: Set[str] = set()
        self.storage = StorageManager(filename=f"chain_{node_identifier}.json") if storage_enabled else None

        # Load dari file jika ada, atau buat Genesis Block
        loaded_chain = self.storage.load_chain() if self.storage else None
        if loaded_chain and self.is_valid_chain(loaded_chain):
            self.chain = loaded_chain
            print(f"[{self.node_identifier}] Blockchain berhasil dimuat dari disk ({len(self.chain)} blok).")
        else:
            self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Membuat blok awal (Genesis Block) sistem voting."""
        genesis_block = Block(
            index=1,
            timestamp=time.time(),
            votes=[{"type": "GENESIS", "info": "E-Voting Genesis Block"}],
            proof=100,
            previous_hash="0" * 64,
        )
        self.chain = [genesis_block]
        if self.storage:
            self.storage.save_chain(self.chain)

    def register_node(self, address: str) -> None:
        """Menambahkan worker node baru ke dalam daftar peer (misal: 'http://127.0.0.1:5002')."""
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError(f"URL node tidak valid: {address}")

    @property
    def last_block(self) -> Block:
        """Mengambil blok terakhir dalam rantai."""
        return self.chain[-1]

    def new_vote(self, voter_id: str, candidate_id: str, timestamp: Optional[float] = None) -> int:
        """
        Menambahkan transaksi suara baru ke dalam mempool pending votes.
        Mengembalikan indeks blok berikutnya yang akan menampung suara ini.
        """
        vote_data = {
            "voter_id": voter_id,
            "candidate_id": candidate_id,
            "timestamp": timestamp or time.time(),
        }
        self.current_votes.append(vote_data)
        return self.last_block.index + 1

    def proof_of_work(self, last_proof: int, previous_hash: str) -> int:
        """
        Algoritma Proof-of-Work:
        Mencari bilangan integer 'proof' (nonce) sehingga hash(last_proof, proof, previous_hash)
        memenuhi target tingkat kesulitan (difficulty) leading zeros.
        """
        proof = 0
        while not self.valid_proof(last_proof, proof, previous_hash, self.difficulty):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int, previous_hash: str, difficulty: int) -> bool:
        """
        Validasi Proof: Apakah hash(last_proof, proof, previous_hash)
        berawalan dengan <difficulty> angka nol?
        """
        guess = f"{last_proof}{proof}{previous_hash}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash.startswith("0" * difficulty)

    def create_block(self, proof: int, previous_hash: Optional[str] = None) -> Block:
        """
        Membuat blok baru, membersihkan antrean pending votes,
        dan menambahkannya ke rantai blockchain.
        """
        block = Block(
            index=len(self.chain) + 1,
            timestamp=time.time(),
            votes=self.current_votes,
            proof=proof,
            previous_hash=previous_hash or self.last_block.hash,
        )

        # Reset pool pending votes
        self.current_votes = []
        self.chain.append(block)

        if self.storage:
            self.storage.save_chain(self.chain)

        return block

    def is_valid_chain(self, chain: List[Block]) -> bool:
        """
        Menentukan apakah rantai blockchain tertentu valid dengan memverifikasi:
        1. Hash previous_block sama dengan previous_hash blok berikutnya.
        2. Proof of work tiap blok valid.
        """
        if not chain:
            return False

        # Verifikasi tiap blok terhadap blok sebelumnya
        for i in range(1, len(chain)):
            prev_block = chain[i - 1]
            curr_block = chain[i]

            # Cek hash integrity
            if curr_block.previous_hash != prev_block.hash:
                return False

            # Cek perhitungan hash blok saat ini
            if curr_block.calculate_hash() != curr_block.hash:
                return False

            # Cek Proof of Work
            if not self.valid_proof(prev_block.proof, curr_block.proof, curr_block.previous_hash, self.difficulty):
                return False

        return True

    def resolve_conflicts(self) -> bool:
        """
        Mekanisme Konsensus: Aturan Rantai Terpanjang (Longest Chain Rule).
        Menyelesaikan konflik antar worker dengan mencari rantai terpanjang yang valid di jaringan.
        Mengembalikan True jika rantai lokal digantikan dengan rantai baru yang lebih panjang.
        """
        neighbours = self.nodes
        new_chain: Optional[List[Block]] = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f"http://{node}/chain", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    length = data.get("length", 0)
                    raw_chain = data.get("chain", [])
                    candidate_chain = [Block.from_dict(b) for b in raw_chain]

                    if length > max_length and self.is_valid_chain(candidate_chain):
                        max_length = length
                        new_chain = candidate_chain
            except requests.RequestException:
                continue

        if new_chain:
            self.chain = new_chain
            if self.storage:
                self.storage.save_chain(self.chain)
            return True

        return False
