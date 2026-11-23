"""
Worker Module: REST API Worker Node & Mining Service
Penanggung Jawab: Abyan (Diintegrasikan dengan Core oleh Safid)
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import argparse
from typing import Any, Dict
from flask import Flask, jsonify, request
from core import Block, Blockchain, broadcast_block, resolve_conflicts


def create_worker_app(node_id: str, difficulty: int = 4) -> Flask:
    """Application Factory untuk menginisialisasi Worker Node Flask."""
    app = Flask(__name__)
    blockchain = Blockchain(node_id=node_id, difficulty=difficulty)

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "service": "Worker Node E-Voting Blockchain",
            "node_id": node_id,
            "status": "online",
            "endpoints": [
                "/status",
                "/chain",
                "/mine",
                "/vote",
                "/transactions/new (alias)",
                "/nodes/register",
                "/nodes/resolve",
                "/nodes/receive_block",
            ]
        }), 200

    @app.route("/status", methods=["GET"])
    def node_status():
        """Mengembalikan informasi ringkas status Worker Node."""
        return jsonify({
            "node_id": node_id,
            "chain_length": len(blockchain.chain),
            "last_block_hash": blockchain.last_block.hash,
            "pending_votes": len(blockchain.pending_votes),
            "difficulty": blockchain.difficulty,
            "peers_count": len(blockchain.peers),
            "peers": list(blockchain.peers),
        }), 200

    @app.route("/chain", methods=["GET"])
    def get_full_chain():
        """Mengembalikan seluruh rantai blok saat ini pada worker lokal."""
        return jsonify({
            "node_id": node_id,
            "chain": [block.to_dict() for block in blockchain.chain],
            "length": len(blockchain.chain),
        }), 200

    @app.route("/vote", methods=["POST"])
    @app.route("/transactions/new", methods=["POST"])
    def add_transaction():
        """
        Menerima transaksi suara baru dari Coordinator atau pemilih.
        Mendukung key 'kandidat' maupun 'candidate_id'.
        Menerapkan validasi Anti Double-Voting.
        """
        values = request.get_json(silent=True)
        if not values:
            return jsonify({"error": "Body JSON tidak valid atau kosong"}), 400

        voter_id = values.get("voter_id")
        kandidat = values.get("kandidat") or values.get("candidate_id")

        if not isinstance(voter_id, (str, int)) or not str(voter_id).strip() or not isinstance(kandidat, str) or not kandidat.strip():
            return jsonify({
                "error": "Data tidak lengkap: wajib menyediakan 'voter_id' dan 'kandidat' (atau 'candidate_id')."
            }), 400

        # Panggil validasi Anti Double-Voting di Core Blockchain
        success, message = blockchain.add_vote(voter_id=str(voter_id), kandidat=str(kandidat))

        if not success:
            # Kode 409 Conflict untuk penolakan double voting
            return jsonify({
                "error": message,
                "voter_id": voter_id,
                "status": "rejected"
            }), 409

        return jsonify({
            "message": message,
            "voter_id": voter_id,
            "kandidat": kandidat,
            "target_block_index": blockchain.last_block.index + 1,
            "status": "accepted"
        }), 201

    @app.route("/mine", methods=["GET"])
    def mine():
        """
        Menjalankan algoritma Proof-of-Work SHA-256 untuk menambang blok baru
        dari antrean pending mempool.
        """
        new_block, message = blockchain.mine_pending_votes(miner_id=node_id)
        if new_block is None:
            return jsonify({
                "message": message,
                "pending_count": 0,
                "status": "idle"
            }), 200

        # Sebarkan blok yang baru ditambang ke seluruh peer terdaftar (Block Propagation)
        propagation_results = {}
        if blockchain.peers:
            propagation_results = broadcast_block(new_block, list(blockchain.peers))

        return jsonify({
            "message": message,
            "block": new_block.to_dict(),
            "propagation": propagation_results,
            "status": "mined"
        }), 200

    @app.route("/nodes/receive_block", methods=["POST"])
    def receive_block():
        """
        Menerima blok baru hasil propagasi dari worker node lain.
        Jika blok valid dan berurutan langsung ditambahkan ke rantai lokal.
        """
        block_data = request.get_json(force=True, silent=True)
        if not block_data:
            return jsonify({"error": "Payload blok kosong"}), 400

        try:
            incoming_block = Block.from_dict(block_data)
        except Exception as e:
            return jsonify({"error": f"Format blok tidak valid: {e}"}), 400

        with blockchain._lock:
            # Periksa apakah blok ini merupakan penerus sah dari last_block lokal
            if blockchain.is_valid_block(incoming_block, blockchain.last_block):
                blockchain.chain.append(incoming_block)
                # Bersihkan pending votes lokal yang sudah ada di blok baru
                voted_ids = {v.get("voter_id") for v in incoming_block.votes if v.get("voter_id")}
                blockchain.pending_votes = [
                    v for v in blockchain.pending_votes if v.get("voter_id") not in voted_ids
                ]
                blockchain.storage.save_state(
                    blockchain.chain, blockchain.pending_votes, blockchain.peers
                )
                return jsonify({
                    "message": f"Blok #{incoming_block.index} berhasil diterima dan ditambahkan ke ledger.",
                    "chain_length": len(blockchain.chain)
                }), 200

        # Jika tidak cocok langsung, jalankan konsensus untuk rekonsiliasi
        resolve_conflicts(blockchain)
        return jsonify({
            "message": "Blok tidak cocok langsung dengan puncak rantai lokal. Telah memicu konsensus.",
            "chain_length": len(blockchain.chain)
        }), 202

    @app.route("/nodes/register", methods=["POST"])
    def register_nodes():
        """
        Mendaftarkan daftar peer worker node baru.
        Format JSON:
        { "nodes": ["http://worker-2:5002", "http://worker-3:5003"] }
        """
        values = request.get_json(force=True, silent=True)
        if not values or "nodes" not in values:
            return jsonify({"error": "Harap sediakan list 'nodes' yang valid"}), 400

        nodes = values["nodes"]
        if not isinstance(nodes, list) or not nodes or any(not isinstance(node, str) or not node.strip() for node in nodes):
            return jsonify({"error": "'nodes' harus berupa list URL peer yang tidak kosong"}), 400

        for node in nodes:
            blockchain.register_peer(node.strip())

        return jsonify({
            "message": "Daftar peer berhasil didaftarkan.",
            "total_peers": len(blockchain.peers),
            "peers": list(blockchain.peers)
        }), 201

    @app.route("/nodes/resolve", methods=["GET"])
    def consensus():
        """Menjalankan algoritma konsensus Longest Valid Chain antar-peer."""
        replaced, message = resolve_conflicts(blockchain)
        return jsonify({
            "replaced": replaced,
            "message": message,
            "chain_length": len(blockchain.chain),
            "last_block_hash": blockchain.last_block.hash
        }), 200

    return app


def main():
    parser = argparse.ArgumentParser(description="Jalankan REST API Worker Node untuk E-Voting Blockchain.")
    parser.add_argument("--port", type=int, default=5001, help="Port Flask server (default: 5001)")
    parser.add_argument("--node-id", type=str, default=None, help="Identifier unik node (default: worker-<port>)")
    parser.add_argument("--difficulty", type=int, default=4, help="Target tingkat kesulitan Proof-of-Work (default: 4)")
    args = parser.parse_args()

    node_identifier = args.node_id or f"worker-{args.port}"
    app = create_worker_app(node_id=node_identifier, difficulty=args.difficulty)

    print(f"[*] Menjalankan {node_identifier} pada port {args.port} (PoW Difficulty: {args.difficulty})...")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
