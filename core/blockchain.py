"""
Modul Inti Blockchain & Algoritma Proof-of-Work E-Voting
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .block import Block
from .storage import LedgerStorage


class Blockchain:
    """
    Kelas utama pengelola Rantai Blok (Blockchain) sistem E-Voting.
    
    Fitur Utama:
    1. Konsensus Proof-of-Work (PoW) SHA-256 dengan difficulty 4 (target '0000').
    2. Validasi Anti Double-Voting tingkat mempool & immutable chain.
    3. Integrasi penyimpanan persisten terisolasi berbasis Docker Volume.
    4. Thread-safe pada penambahan transaksi suara dan proses mining.
    """

    DEFAULT_DIFFICULTY: int = 4  # Target hash diawali 4 angka nol ('0000')

    def __init__(
        self,
        node_id: str = "worker-1",
        difficulty: int = DEFAULT_DIFFICULTY,
        data_dir: Optional[str] = None,
    ) -> None:
        self.node_id: str = node_id
        self.difficulty: int = difficulty
        self.storage: LedgerStorage = LedgerStorage(node_id=node_id, data_dir=data_dir)
        self._lock: threading.Lock = threading.Lock()

        # Inisialisasi struktur data
        self.chain: List[Block] = []
        self.pending_votes: List[Dict[str, Any]] = []
        self.peers: Set[str] = set()

        # Coba muat state dari Docker Volume
        loaded_chain, loaded_votes, loaded_peers = self.storage.load_state()

        if loaded_chain and self.is_valid_chain(loaded_chain):
            self.chain = loaded_chain
            self.pending_votes = loaded_votes
            self.peers = loaded_peers
            print(f"[{self.node_id}] Rantai blockchain berhasil dimuat ({len(self.chain)} blok).")
        else:
            # Jika belum ada data persisten atau chain rusak, buat Genesis Block
            self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """Menciptakan Genesis Block sebagai pondasi awal rantai blok e-voting."""
        genesis_votes: List[Dict[str, Any]] = [
            {
                "voter_id": "SYSTEM_GENESIS",
                "kandidat": "KONSENSUS_AWAL",
                "timestamp": time.time(),
                "keterangan": "Genesis Block E-Voting KPT Terdistribusi",
            }
        ]
        genesis_block = Block(
            index=1,
            timestamp=time.time(),
            votes=genesis_votes,
            previous_hash="0" * 64,
            nonce=0,
        )

        # Lakukan PoW untuk genesis block agar memenuhi difficulty
        self.proof_of_work(genesis_block)
        self.chain = [genesis_block]
        self.pending_votes = []
        self.storage.save_state(self.chain, self.pending_votes, self.peers)
        print(f"[{self.node_id}] Genesis Block berhasil diciptakan: {genesis_block.hash}")

    @property
    def last_block(self) -> Block:
        """Mengambil blok terakhir yang valid pada rantai saat ini."""
        return self.chain[-1]

    def register_peer(self, peer_address: str) -> None:
        """
        Mendaftarkan URL peer worker node ke dalam daftar tetangga (neighbor nodes).
        Format yang diharapkan: 'http://worker-2:5002' atau '127.0.0.1:5002'.
        """
        clean_peer = peer_address.strip()
        if clean_peer and clean_peer not in self.peers:
            with self._lock:
                self.peers.add(clean_peer)
                self.storage.save_state(self.chain, self.pending_votes, self.peers)

    # --------------------------------------------------------------------------
    # MEKANISME VALIDASI ANTI DOUBLE-VOTING
    # --------------------------------------------------------------------------
    def is_voter_registered_or_voted(self, voter_id: str) -> Tuple[bool, Optional[str]]:
        """
        Memeriksa apakah voter_id telah pernah memberikan suara.
        
        Pengecekan dilakukan secara komprehensif pada:
        1. Mempool lokal (`pending_votes`) yang sedang menunggu giliran ditambang.
        2. Seluruh transaksi suara di setiap blok pada rantai `chain` yang sudah immutable.
        
        Mengembalikan:
            Tuple[bool, Optional[str]]: (True, keterangan_lokasi) jika sudah memilih,
                                        (False, None) jika pemilih belum pernah memilih.
        """
        clean_voter_id = str(voter_id).strip()

        # 1. Verifikasi di antrean pending_votes (mempool)
        for vote in self.pending_votes:
            if vote.get("voter_id") == clean_voter_id:
                return True, "antrean mempool (menunggu penambangan blok)"

        # 2. Verifikasi di seluruh blok yang sudah terverifikasi di ledger
        for block in self.chain:
            for vote in block.votes:
                if vote.get("voter_id") == clean_voter_id:
                    return True, f"buku besar (Ledger Blok #{block.index})"

        return False, None

    def add_vote(self, voter_id: str, kandidat: str) -> Tuple[bool, str]:
        """
        Menambahkan transaksi suara baru ke dalam pending votes secara thread-safe
        dengan jaminan validasi Anti Double-Voting.
        
        Argumen:
            voter_id (str): Identitas unik pemilih (e.g. NIM / NIK / ID Kriptografis).
            kandidat (str): Kode / Nama pasangan calon atau kandidat yang dipilih.
            
        Mengembalikan:
            Tuple[bool, str]: (True, pesan_sukses) atau (False, pesan_penolakan).
        """
        if not voter_id or not str(voter_id).strip():
            return False, "Penolakan: 'voter_id' tidak boleh kosong."
        if not kandidat or not str(kandidat).strip():
            return False, "Penolakan: 'kandidat' tidak boleh kosong."

        clean_voter_id = str(voter_id).strip()
        clean_kandidat = str(kandidat).strip()

        with self._lock:
            # Eksekusi pengecekan Anti Double-Voting
            already_voted, location = self.is_voter_registered_or_voted(clean_voter_id)
            if already_voted:
                msg = (
                    f"PENOLAKAN ANTI DOUBLE-VOTING: Pemilih dengan ID '{clean_voter_id}' "
                    f"sudah pernah memberikan suara sebelumnya pada {location}!"
                )
                print(f"[{self.node_id}] {msg}")
                return False, msg

            # Konstruksi payload transaksi suara
            vote_record: Dict[str, Any] = {
                "voter_id": clean_voter_id,
                "kandidat": clean_kandidat,
                "candidate_id": clean_kandidat,  # Alias kompatibilitas
                "timestamp": time.time(),
            }

            self.pending_votes.append(vote_record)
            self.storage.save_state(self.chain, self.pending_votes, self.peers)

            target_index = self.last_block.index + 1
            success_msg = (
                f"Suara sah dari pemilih '{clean_voter_id}' berhasil diverifikasi "
                f"dan masuk ke mempool. Target blok: #{target_index}."
            )
            return True, success_msg

    # --------------------------------------------------------------------------
    # ALGORITMA PROOF-OF-WORK (PoW) SHA-256
    # --------------------------------------------------------------------------
    def proof_of_work(self, block: Block) -> int:
        """
        Algoritma Proof-of-Work (PoW):
        Mencari bilangan bulat `nonce` sehingga hash SHA-256 blok
        memenuhi tingkat kesulitan (difficulty) target diawali dengan '0' * difficulty
        (secara default diawali '0000').
        """
        prefix_target = "0" * self.difficulty
        nonce = 0
        block.nonce = nonce
        computed_hash = block.compute_hash()

        while not computed_hash.startswith(prefix_target):
            nonce += 1
            block.nonce = nonce
            computed_hash = block.compute_hash()

        block.hash = computed_hash
        return nonce

    def mine_pending_votes(self, miner_id: Optional[str] = None) -> Tuple[Optional[Block], str]:
        """
        Membungkus seluruh transaksi suara di `pending_votes` menjadi satu blok baru,
        melakukan penambangan PoW SHA-256, memasukkan blok ke rantai, dan menyimpannya.
        
        Mengembalikan:
            Tuple[Optional[Block], str]: Objek Blok baru dan pesan hasil penambangan.
        """
        with self._lock:
            if not self.pending_votes:
                return None, "Tidak ada transaksi suara di pending pool untuk ditambang."

            previous_block = self.last_block
            new_block = Block(
                index=previous_block.index + 1,
                timestamp=time.time(),
                votes=list(self.pending_votes),
                previous_hash=previous_block.hash,
                nonce=0,
            )

            # Hitung waktu mining untuk analisis performa
            start_time = time.time()
            self.proof_of_work(new_block)
            elapsed_time = time.time() - start_time

            # Update chain dan bersihkan pending votes
            self.chain.append(new_block)
            cleared_count = len(self.pending_votes)
            self.pending_votes = []
            self.storage.save_state(self.chain, self.pending_votes, self.peers)

            miner_info = miner_id or self.node_id
            msg = (
                f"Blok #{new_block.index} berhasil ditambang oleh {miner_info}! "
                f"Nonce: {new_block.nonce} | Hash: {new_block.hash} | "
                f"Jumlah Suara: {cleared_count} | Waktu PoW: {elapsed_time:.4f} detik."
            )
            print(f"[{self.node_id}] {msg}")
            return new_block, msg

    # --------------------------------------------------------------------------
    # VALIDASI INTEGRITAS BLOK & RANTAI BLOK
    # --------------------------------------------------------------------------
    def is_valid_block(self, block: Block, previous_block: Block) -> bool:
        """
        Memverifikasi keabsahan satu blok terhadap blok sebelumnya:
        1. Indeks blok harus tepat index_sebelumnya + 1.
        2. `previous_hash` harus cocok dengan hash blok sebelumnya.
        3. Rekalkulasi `compute_hash()` harus sama dengan `block.hash`.
        4. Hash harus diawali target difficulty (misal '0000').
        5. Tidak boleh ada voter ganda di dalam blok tersebut.
        """
        if block.index != previous_block.index + 1:
            return False

        if block.previous_hash != previous_block.hash:
            return False

        if block.compute_hash() != block.hash:
            return False

        prefix_target = "0" * self.difficulty
        if not block.hash.startswith(prefix_target):
            return False

        # Pastikan tidak ada double voting di internal blok itu sendiri
        voters_in_block: Set[str] = set()
        for vote in block.votes:
            voter = vote.get("voter_id")
            if voter and voter != "SYSTEM_GENESIS":
                if voter in voters_in_block:
                    return False
                voters_in_block.add(voter)

        return True

    def is_valid_chain(self, chain: List[Block]) -> bool:
        """
        Memvalidasi keabsahan seluruh rantai blockchain dari Genesis hingga blok puncak.
        Memastikan seluruh kaitan hash, PoW, dan aturan anti double-voting terpenuhi.
        """
        if not chain or len(chain) == 0:
            return False

        prefix_target = "0" * self.difficulty

        # Validasi Genesis Block
        genesis = chain[0]
        if genesis.index != 1:
            return False
        if genesis.compute_hash() != genesis.hash:
            return False
        if not genesis.hash.startswith(prefix_target):
            return False

        # Telusuri dan validasi setiap blok berurutan
        all_voters_seen: Set[str] = set()

        # Rekam voter genesis jika ada
        for vote in genesis.votes:
            vid = vote.get("voter_id")
            if vid and vid != "SYSTEM_GENESIS":
                all_voters_seen.add(vid)

        for i in range(1, len(chain)):
            prev_block = chain[i - 1]
            curr_block = chain[i]

            if not self.is_valid_block(curr_block, prev_block):
                return False

            # Validasi anti double-voting secara global di seluruh rantai
            for vote in curr_block.votes:
                vid = vote.get("voter_id")
                if vid and vid != "SYSTEM_GENESIS":
                    if vid in all_voters_seen:
                        print(f"[Validasi Chain ERROR] Double-voting terdeteksi pada voter: {vid}")
                        return False
                    all_voters_seen.add(vid)

        return True
