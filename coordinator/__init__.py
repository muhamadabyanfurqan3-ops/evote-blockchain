"""
Coordinator Module: Master Node, Load Balancer / Dispatcher, & Web Dashboard
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import argparse
import io
import json
from typing import Dict, List, Any
import requests
from flask import Flask, jsonify, render_template_string, request, Response

# Topologi default: 6 Worker Nodes
DEFAULT_WORKERS = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
    "http://127.0.0.1:5004",
    "http://127.0.0.1:5005",
    "http://127.0.0.1:5006",
]

# Daftar Kandidat Default Pemilu
DEFAULT_CANDIDATES = [
    {"id": "PASLON-01", "name": "Kandidat 01 - Tim Alpha"},
    {"id": "PASLON-02", "name": "Kandidat 02 - Tim Beta"},
    {"id": "PASLON-03", "name": "Kandidat 03 - Tim Gamma"},
]


def create_coordinator_app(workers: List[str] = None) -> Flask:
    """Application Factory untuk Master/Coordinator Node."""
    app = Flask(__name__)
    worker_nodes = workers or DEFAULT_WORKERS.copy()

    HTML_DASHBOARD = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard E-Voting Blockchain - Master Coordinator</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
            .card { background-color: #1e293b; border: 1px solid #334155; color: #f8fafc; border-radius: 12px; }
            .badge-worker { font-size: 0.85rem; }
            .btn-primary { background-color: #3b82f6; border-color: #3b82f6; }
            .btn-primary:hover { background-color: #2563eb; }
        </style>
    </head>
    <body class="py-4">
        <div class="container">
            <header class="pb-3 mb-4 border-bottom border-secondary d-flex justify-content-between align-items-center">
                <div>
                    <h2 class="fw-bold text-primary mb-0">E-Voting Distributed Consensus</h2>
                    <small class="text-secondary">UAS Komputasi Paralel dan Terdistribusi - Topologi 1 Master + 6 Workers</small>
                </div>
                <span class="badge bg-success px-3 py-2">Master Active (:5000)</span>
            </header>

            <div class="row g-4">
                <!-- Form Pemberian Suara -->
                <div class="col-md-5">
                    <div class="card p-4 shadow-sm h-100">
                        <h4 class="card-title fw-bold mb-3 text-info">🗳️ Surat Suara Digital</h4>
                        <p class="text-secondary small">Masukkan identitas pemilih (NIK/ID) dan pilih kandidat pilihan Anda.</p>
                        <form id="voteForm">
                            <div class="mb-3">
                                <label class="form-label">ID Pemilih (NIK/NIM):</label>
                                <input type="text" id="voterId" class="form-control bg-dark text-light border-secondary" placeholder="Contoh: VOTER-001" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Pilih Pasangan Calon:</label>
                                <select id="candidateId" class="form-select bg-dark text-light border-secondary" required>
                                    <option value="" disabled selected>-- Pilih Paslon --</option>
                                    <option value="PASLON-01">PASLON-01: Kandidat Alpha</option>
                                    <option value="PASLON-02">PASLON-02: Kandidat Beta</option>
                                    <option value="PASLON-03">PASLON-03: Kandidat Gamma</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 py-2 fw-semibold">Kirim Suara ke Jaringan</button>
                        </form>
                        <div id="voteAlert" class="mt-3"></div>
                    </div>
                </div>

                <!-- Status 6 Worker Nodes -->
                <div class="col-md-7">
                    <div class="card p-4 shadow-sm h-100">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4 class="card-title fw-bold mb-0 text-info">⚙️ Status 6 Worker Nodes</h4>
                            <button class="btn btn-sm btn-outline-warning" onclick="triggerMining()">⚡ Trigger Mining Semua Worker</button>
                        </div>
                        <div class="row g-2" id="workerList">
                            <div class="col-12 text-center text-secondary py-4">Memuat status worker...</div>
                        </div>
                    </div>
                </div>

                <!-- Rekapitulasi Suara -->
                <div class="col-12">
                    <div class="card p-4 shadow-sm">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4 class="card-title fw-bold mb-0 text-success">📊 Rekapitulasi Suara Terverifikasi</h4>
                            <button class="btn btn-sm btn-outline-light" onclick="loadTally()">🔄 Refresh Rekapitulasi</button>
                        </div>
                        <div class="row g-3" id="tallyResults">
                            <div class="col-12 text-center text-secondary py-3">Memuat rekapitulasi dari konsensus...</div>
                        </div>
                        <div class="mt-4 text-center">
                            <img id="tallyChart" src="/chart" class="img-fluid rounded border border-secondary" alt="Grafik Rekapitulasi Suara" onerror="this.style.display='none'">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function fetchWorkers() {
                try {
                    const res = await fetch('/workers');
                    const data = await res.json();
                    const container = document.getElementById('workerList');
                    container.innerHTML = '';
                    data.forEach(w => {
                        const isOnline = w.status === 'online';
                        container.innerHTML += `
                            <div class="col-md-4">
                                <div class="p-3 rounded border border-secondary ${isOnline ? 'bg-black' : 'bg-danger-subtle text-dark'}">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <strong>${w.node_id || w.url}</strong>
                                        <span class="badge ${isOnline ? 'bg-success' : 'bg-danger'}">${w.status}</span>
                                    </div>
                                    <div class="small mt-2 text-secondary">
                                        Blok: <span class="text-info">${w.chain_length || 0}</span> | Pending: <span class="text-warning">${w.pending_votes || 0}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                } catch (e) {
                    console.error(e);
                }
            }

            async function loadTally() {
                try {
                    const res = await fetch('/tally');
                    const data = await res.json();
                    const container = document.getElementById('tallyResults');
                    container.innerHTML = '';
                    const tally = data.tally || {};
                    const total = data.total_valid_votes || 0;

                    for (const [paslon, count] of Object.entries(tally)) {
                        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                        container.innerHTML += `
                            <div class="col-md-4">
                                <div class="p-3 rounded bg-dark border border-secondary">
                                    <h5>${paslon}</h5>
                                    <h2 class="fw-bold text-success">${count} <small class="fs-6 text-secondary">suara (${pct}%)</small></h2>
                                    <div class="progress mt-2" style="height: 6px;">
                                        <div class="progress-bar bg-success" style="width: ${pct}%"></div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                    document.getElementById('tallyChart').src = '/chart?t=' + new Date().getTime();
                    document.getElementById('tallyChart').style.display = 'block';
                } catch (e) {
                    console.error(e);
                }
            }

            async function triggerMining() {
                const res = await fetch('/trigger-mining', { method: 'POST' });
                const data = await res.json();
                alert(JSON.stringify(data, null, 2));
                fetchWorkers();
                loadTally();
            }

            document.getElementById('voteForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const alertBox = document.getElementById('voteAlert');
                alertBox.innerHTML = '<div class="alert alert-info">Memproses pengiriman suara...</div>';

                const payload = {
                    voter_id: document.getElementById('voterId').value.trim(),
                    candidate_id: document.getElementById('candidateId').value
                };

                try {
                    const res = await fetch('/vote', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const result = await res.json();
                    if (res.ok) {
                        alertBox.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
                        document.getElementById('voteForm').reset();
                        fetchWorkers();
                    } else {
                        alertBox.innerHTML = `<div class="alert alert-danger">${result.error || 'Gagal mengirim suara'}</div>`;
                    }
                } catch (err) {
                    alertBox.innerHTML = `<div class="alert alert-danger">Koneksi error: ${err.message}</div>`;
                }
            });

            setInterval(fetchWorkers, 5000);
            fetchWorkers();
            loadTally();
        </script>
    </body>
    </html>
    """

    @app.route("/", methods=["GET"])
    def dashboard():
        """Menyajikan halaman Web Dashboard utama."""
        return render_template_string(HTML_DASHBOARD)

    @app.route("/workers", methods=["GET"])
    def get_workers_status():
        """Mengecek status kesehatan 6 worker nodes."""
        status_list = []
        for url in worker_nodes:
            try:
                res = requests.get(f"{url}/status", timeout=1.5)
                if res.status_code == 200:
                    info = res.json()
                    info["url"] = url
                    info["status"] = "online"
                    status_list.append(info)
                else:
                    status_list.append({"url": url, "status": "error"})
            except requests.RequestException:
                status_list.append({"url": url, "status": "offline"})
        return jsonify(status_list), 200

    @app.route("/vote", methods=["POST"])
    def submit_vote():
        """
        Menerima suara dari pemilih dan menyebarkan (broadcast)
        ke antrean mempool seluruh worker nodes.
        """
        payload = request.get_json(force=True, silent=True)
        if not payload or "voter_id" not in payload or "candidate_id" not in payload:
            return jsonify({"error": "Data voter_id dan candidate_id wajib diisi"}), 400

        success_workers = []
        errors = []

        for url in worker_nodes:
            try:
                res = requests.post(f"{url}/transactions/new", json=payload, timeout=2)
                if res.status_code == 201:
                    success_workers.append(url)
                elif res.status_code == 409:
                    return jsonify({"error": res.json().get("error", "Voter terdeteksi double-voting")}), 409
                else:
                    errors.append(f"{url}: {res.text}")
            except requests.RequestException as e:
                errors.append(f"{url}: offline/unreachable")

        if not success_workers:
            return jsonify({"error": "Semua worker node gagal menerima transaksi suara", "details": errors}), 502

        return jsonify({
            "message": f"Suara pemilih {payload['voter_id']} berhasil dibroadcast ke {len(success_workers)} worker nodes.",
            "success_nodes": success_workers
        }), 200

    @app.route("/trigger-mining", methods=["POST"])
    def trigger_mining():
        """Memerintahkan seluruh worker node untuk memulai proses mining PoW."""
        mining_results = {}
        for url in worker_nodes:
            try:
                res = requests.get(f"{url}/mine", timeout=10)
                mining_results[url] = res.json()
            except requests.RequestException as e:
                mining_results[url] = {"status": "failed", "error": str(e)}

        # Picu konsensus antar-worker setelah proses penambangan
        for url in worker_nodes:
            try:
                requests.get(f"{url}/nodes/resolve", timeout=3)
            except requests.RequestException:
                pass

        return jsonify({"message": "Trigger mining selesai dijalankan", "results": mining_results}), 200

    @app.route("/tally", methods=["GET"])
    def get_tally():
        """
        Mengagregasi suara dari rantai blockchain terpanjang/terverifikasi
        pada node worker pertama yang responsif.
        """
        longest_chain = []
        for url in worker_nodes:
            try:
                res = requests.get(f"{url}/chain", timeout=2)
                if res.status_code == 200:
                    data = res.json()
                    chain = data.get("chain", [])
                    if len(chain) > len(longest_chain):
                        longest_chain = chain
            except requests.RequestException:
                continue

        tally: Dict[str, int] = {c["id"]: 0 for c in DEFAULT_CANDIDATES}
        total_votes = 0

        for block in longest_chain:
            for vote in block.get("votes", []):
                cand_id = vote.get("candidate_id")
                if cand_id:
                    tally[cand_id] = tally.get(cand_id, 0) + 1
                    total_votes += 1

        return jsonify({
            "total_blocks": len(longest_chain),
            "total_valid_votes": total_votes,
            "tally": tally,
        }), 200

    @app.route("/chart", methods=["GET"])
    def chart_image():
        """Menghasilkan grafik visualisasi rekapitulasi suara menggunakan Matplotlib."""
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-GUI backend
            import matplotlib.pyplot as plt

            # Ambil data tally
            tally_resp, _ = get_tally()
            tally_data = tally_resp.json.get("tally", {})

            labels = list(tally_data.keys())
            votes = list(tally_data.values())

            fig, ax = plt.subplots(figsize=(6, 3.5), facecolor="#1e293b")
            ax.set_facecolor("#1e293b")
            bars = ax.bar(labels, votes, color=["#38bdf8", "#34d399", "#f472b6"], width=0.5)

            ax.set_title("Perolehan Suara E-Voting Realtime", color="#f8fafc", fontsize=12, pad=12)
            ax.tick_params(colors="#94a3b8")
            ax.spines["bottom"].set_color("#475569")
            ax.spines["top"].set_color("#475569")
            ax.spines["left"].set_color("#475569")
            ax.spines["right"].set_color("#475569")

            for bar in bars:
                height = bar.get_height()
                ax.annotate(
                    f"{int(height)}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    color="#f8fafc",
                    fontweight="bold"
                )

            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=100)
            plt.close(fig)
            buf.seek(0)
            return Response(buf.getvalue(), mimetype="image/png")
        except Exception as e:
            return jsonify({"error": f"Gagal membuat grafik: {str(e)}"}), 500

    return app


def main():
    parser = argparse.ArgumentParser(description="Jalankan Master Coordinator Node E-Voting.")
    parser.add_argument("--port", type=int, default=5000, help="Port Flask server (default: 5000)")
    args = parser.parse_args()

    app = create_coordinator_app()
    print(f"[*] Menjalankan Master Coordinator Node pada http://localhost:{args.port}...")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
