"""
Modul Mekanisme Konsensus Terdistribusi & Block Propagation E-Voting
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import requests
except ImportError:
    requests = None

from .block import Block
from .blockchain import Blockchain


def resolve_conflicts(
    blockchain: Blockchain, peer_urls: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """
    Algoritma Konsensus Terdistribusi: Longest Valid Chain Rule.
    
    Menyelesaikan percabangan (fork) dan inkonsistensi antar-worker dengan mencari
    rantai blok terpanjang yang valid secara kriptografis di jaringan.
    
    Alur Kerja:
    1. Mengontak seluruh peer terdaftar melalui HTTP GET `/chain`.
    2. Memeriksa apakah panjang rantai peer lebih panjang dari rantai lokal.
    3. Jika lebih panjang, mengonstruksi rantai kandidat dan memvalidasi keabsahannya
       dengan `blockchain.is_valid_chain()`.
    4. Jika valid dan terpanjang, rantai lokal digantikan dengan rantai baru tersebut.
    5. Membersihkan mempool `pending_votes` lokal dari transaksi yang telah termaktub
       di dalam blok rantai baru, serta menyimpan state terkonsensus ke storage.
    
    Mengembalikan:
        Tuple[bool, str]: (True, pesan) jika rantai lokal diganti,
                          (False, pesan) jika rantai lokal tetap otoritatif.
    """
    if requests is None:
        return False, "Library 'requests' tidak terinstall; tidak dapat menghubungi peer."

    targets: Set[str] = set(peer_urls) if peer_urls else blockchain.peers
    if not targets:
        return False, "Tidak ada peer yang terdaftar untuk sinkronisasi konsensus."

    longest_chain: Optional[List[Block]] = None
    max_length: int = len(blockchain.chain)
    winning_peer: Optional[str] = None

    for peer in targets:
        url = peer if peer.startswith("http://") or peer.startswith("https://") else f"http://{peer}"
        endpoint = f"{url.rstrip('/')}/chain"

        try:
            response = requests.get(endpoint, timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                remote_length = data.get("length", 0)
                raw_chain = data.get("chain", [])

                if remote_length > max_length and len(raw_chain) == remote_length:
                    candidate_chain = [Block.from_dict(b) for b in raw_chain]

                    if blockchain.is_valid_chain(candidate_chain):
                        max_length = remote_length
                        longest_chain = candidate_chain
                        winning_peer = peer
        except Exception:
            continue

    if longest_chain is not None and winning_peer is not None:
        with blockchain._lock:
            blockchain.chain = longest_chain

            voted_ids: Set[str] = set()
            for block in blockchain.chain:
                for vote in block.votes:
                    vid = vote.get("voter_id")
                    if vid:
                        voted_ids.add(vid)

            blockchain.pending_votes = [
                v for v in blockchain.pending_votes if v.get("voter_id") not in voted_ids
            ]

            blockchain.storage.save_state(
                blockchain.chain, blockchain.pending_votes, blockchain.peers
            )

        success_msg = (
            f"KONSENSUS TERCAPAI: Rantai lokal berhasil disinkronkan dengan rantai terpanjang "
            f"dari peer '{winning_peer}' (Total Blok: {max_length})."
        )
        print(f"[{blockchain.node_id}] {success_msg}")
        return True, success_msg

    current_len = len(blockchain.chain)
    authoritative_msg = (
        f"KONSENSUS KOKOH: Rantai lokal node '{blockchain.node_id}' sudah yang terpanjang "
        f"dan otoritatif ({current_len} blok)."
    )
    return False, authoritative_msg


def broadcast_block(
    block: Block, peer_urls: List[str], timeout: float = 2.5
) -> Dict[str, bool]:
    """
    Fungsi Helper Block Propagation:
    Menyebarkan blok baru yang baru saja ditambang ke seluruh peer worker node.
    """
    results: Dict[str, bool] = {}
    if requests is None:
        return {peer: False for peer in peer_urls}

    payload = block.to_dict()

    for peer in peer_urls:
        url = peer if peer.startswith("http://") or peer.startswith("https://") else f"http://{peer}"
        endpoint = f"{url.rstrip('/')}/nodes/receive_block"

        try:
            res = requests.post(endpoint, json=payload, timeout=timeout)
            results[peer] = res.status_code in [200, 201]
        except Exception:
            results[peer] = False

    return results
