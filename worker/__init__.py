"""
Worker Module: REST API Worker Node & Mining Service
Penanggung Jawab: Abyan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import argparse
import sys
import uuid
from flask import Flask, jsonify, request
from core import Blockchain


def create_worker_app(node_id: str, difficulty: int = 4) -> Flask:
    """Application Factory untuk menginisialisasi Worker Node Flask."""
    app = Flask(__name__)
    blockchain = Blockchain(node_identifier=node_id, difficulty=difficulty)

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "service": "Worker Node E-Voting",
            "node_id": node_id,
            "status": "online",
            "endpoints": [
                "/status",
                "/chain",
                "/mine",
                "/transactions/new",
                "/nodes/register",
                "/nodes/resolve"
            ]
        }), 200

    @app.route("/status", methods=["GET"])
    def node_status():
        """Mengembalikan informasi ringkas status Worker Node."""
        return jsonify({
            "node_id": node_id,
            "chain_length": len(blockchain.chain),
            "pending_votes": len(blockchain.current_votes),
            "difficulty": blockchain.difficulty,
            "peers_count": len(blockchain.nodes),
            "peers": list(blockchain.nodes),
        }), 200

    @app.route("/chain", methods=["GET"])
    def get_full_chain():
        """Mengembalikan seluruh rantai blok saat ini pada worker lokal."""
        response = {
            "node_id": node_id,
            "chain": [block.to_dict() for block in blockchain.chain],
            "length": len(blockchain.chain),
        }
        return jsonify(response), 200

    @app.route("/transactions/new", methods=["POST"])
    def add_transaction():
        """
        Menerima transaksi suara baru dari Coordinator atau pemilih.
        Format JSON yang diharapkan:
        {
            "voter_id": "VOTER-12345",
            "candidate_id": "CANDIDATE-01"
        }
        """
        values = request.get_json(force=True, silent=True)
        if not values:
            return jsonify({"error": "Body JSON tidak valid atau kosong"}), 400

        required_fields = ["voter_id", "candidate_id"]
        if not all(k in values for k in required_fields):
            return jsonify({"error": "Data tidak lengkap, wajib memiliki voter_id dan candidate_id"}), 400

        # Cek apakah pemilih sudah pernah memilih di pending pool atau di dalam rantai blok
        voter_id = values["voter_id"]
        for block in blockchain.chain:
            for vote in block.votes:
                if vote.get("voter_id") == voter_id:
                    return jsonify({"error": f"Voter {voter_id} sudah memberikan suara pada blok #{block.index}"}), 409

        for vote in blockchain.current_votes:
            if vote.get("voter_id") == voter_id:
                return jsonify({"error": f"Voter {voter_id} sudah berada dalam antrean pending votes"}), 409

        index = blockchain.new_vote(
            voter_id=voter_id,
            candidate_id=values["candidate_id"],
        )

        return jsonify({
            "message": f"Suara berhasil dicatat ke dalam pending mempool",
            "block_target_index": index,
            "voter_id": voter_id
        }), 201

    @app.route("/mine", methods=["GET"])
    def mine():
        """
        Menjalankan algoritma Proof-of-Work untuk menambang blok baru
        berisi transaksi suara yang ada di pending pool.
        """
        if not blockchain.current_votes:
            return jsonify({
                "message": "Tidak ada transaksi suara baru di pending pool untuk ditambang.",
                "pending_count": 0
            }), 200

        last_block = blockchain.last_block
        last_proof = last_block.proof
        previous_hash = last_block.hash

        # Jalankan kalkulasi PoW
        proof = blockchain.proof_of_work(last_proof, previous_hash)

        # Buat blok baru dan rekam ke rantai
        block = blockchain.create_block(proof, previous_hash)

        response = {
            "message": f"Blok baru berhasil ditambang oleh {node_id}!",
            "index": block.index,
            "votes": block.votes,
            "proof": block.proof,
            "previous_hash": block.previous_hash,
            "hash": block.hash,
        }
        return jsonify(response), 200

    @app.route("/nodes/register", methods=["POST"])
    def register_nodes():
        """
        Mendaftarkan daftar peer worker node baru.
        Format JSON yang diharapkan:
        {
            "nodes": ["http://127.0.0.1:5002", "http://127.0.0.1:5003"]
        }
        """
        values = request.get_json(force=True, silent=True)
        if not values or "nodes" not in values:
            return jsonify({"error": "Harap sediakan list 'nodes' yang valid"}), 400

        nodes = values["nodes"]
        for node in nodes:
            try:
                blockchain.register_node(node)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

        return jsonify({
            "message": "Node peer berhasil didaftarkan.",
            "total_nodes": list(blockchain.nodes)
        }), 201

    @app.route("/nodes/resolve", methods=["GET"])
    def consensus():
        """Menjalankan algoritma konsensus untuk resolusi konflik antar-peer."""
        replaced = blockchain.resolve_conflicts()
        if replaced:
            response = {
                "message": "Rantai lokal digantikan dengan rantai konsensus terpanjang.",
                "new_chain_length": len(blockchain.chain),
                "chain": [b.to_dict() for b in blockchain.chain]
            }
        else:
            response = {
                "message": "Rantai lokal sudah mutakhir dan berstatus authoritative.",
                "chain_length": len(blockchain.chain)
            }
        return jsonify(response), 200

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
