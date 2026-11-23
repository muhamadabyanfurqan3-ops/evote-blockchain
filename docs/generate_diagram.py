"""
Script Pembuat Diagram Arsitektur Sistem E-Voting Blockchain Terdistribusi
Penanggung Jawab: Safid Nasih Ulwan
Mata Kuliah: Komputasi Paralel dan Terdistribusi (KPT)
"""

import os
import matplotlib
matplotlib.use("Agg")  # Mode non-GUI untuk eksekusi tanpa display server
import matplotlib.patches as patches
import matplotlib.pyplot as plt


def generate_architecture_diagram(output_path: str = "docs/arsitektur_sistem.png") -> None:
    """Menggambar diagram arsitektur sistem E-Voting Blockchain menggunakan matplotlib."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 9), facecolor="#0b1120")
    ax.set_facecolor("#0b1120")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Title Banner
    ax.text(
        7.0, 8.5,
        "ARSITEKTUR SISTEM E-VOTING BLOCKCHAIN TERDISTRIBUSI (EVB-02)",
        fontsize=16, fontweight="bold", color="#38bdf8", ha="center"
    )
    ax.text(
        7.0, 8.15,
        "Topologi 1 Master Coordinator + 6 Worker Blockchain Nodes (Docker Network & Volume)",
        fontsize=10, color="#94a3b8", ha="center"
    )

    # 1. Client Box (Voter)
    voter_box = patches.FancyBboxPatch(
        (0.6, 6.2), 2.2, 1.2,
        boxstyle="round,pad=0.15", ec="#38bdf8", fc="#1e293b", lw=1.5
    )
    ax.add_patch(voter_box)
    ax.text(1.7, 7.0, "CLIENT / PEMILIH", fontsize=11, fontweight="bold", color="#38bdf8", ha="center")
    ax.text(1.7, 6.5, "Web Browser / API\n(HTTP POST /vote)", fontsize=8.5, color="#cbd5e1", ha="center")

    # 2. Master Coordinator Box
    coord_box = patches.FancyBboxPatch(
        (4.5, 6.0), 5.0, 1.5,
        boxstyle="round,pad=0.2", ec="#10b981", fc="#132e27", lw=2
    )
    ax.add_patch(coord_box)
    ax.text(7.0, 7.15, "MASTER / COORDINATOR NODE (Port 5000)", fontsize=11, fontweight="bold", color="#34d399", ha="center")
    ax.text(
        7.0, 6.5,
        "- Web Dashboard & Voting Portal (Bootstrap UI)\n"
        "- Vote Transaction Dispatcher & Load Balancer\n"
        "- Cluster Health Monitor & Tallying Aggregator",
        fontsize=8.5, color="#e2e8f0", ha="center"
    )

    # Arrow from Voter to Coordinator
    ax.annotate(
        "", xy=(4.5, 6.75), xytext=(2.8, 6.75),
        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2, mutation_scale=15)
    )
    ax.text(3.65, 7.0, "POST /vote", fontsize=8, color="#38bdf8", ha="center", fontweight="semibold")

    # 3. Docker Network Container Boundary
    docker_net = patches.FancyBboxPatch(
        (0.5, 0.4), 13.0, 5.0,
        boxstyle="round,pad=0.2", ec="#64748b", fc="#0f172a", lw=1.2, ls="--"
    )
    ax.add_patch(docker_net)
    ax.text(0.8, 5.15, "Docker Bridge Network ('evoting-net')", fontsize=9, color="#94a3b8", fontweight="semibold")

    # Arrow from Coordinator down to Workers
    ax.annotate(
        "", xy=(7.0, 4.8), xytext=(7.0, 6.0),
        arrowprops=dict(arrowstyle="->", color="#10b981", lw=2, mutation_scale=15)
    )
    ax.text(7.1, 5.4, "Broadcast Transaksi Suara\n(POST /transactions/new)", fontsize=8, color="#34d399", va="center")

    # 4. 6 Worker Nodes & Volumes
    worker_coords = [
        (0.8, 2.5, "Worker 1", "5001"),
        (2.9, 2.5, "Worker 2", "5002"),
        (5.0, 2.5, "Worker 3", "5003"),
        (7.1, 2.5, "Worker 4", "5004"),
        (9.2, 2.5, "Worker 5", "5005"),
        (11.3, 2.5, "Worker 6", "5006"),
    ]

    for (x, y, w_name, port) in worker_coords:
        # Worker Box
        w_box = patches.FancyBboxPatch(
            (x, y), 1.9, 2.0,
            boxstyle="round,pad=0.1", ec="#f59e0b", fc="#261b0c", lw=1.5
        )
        ax.add_patch(w_box)
        ax.text(x + 0.95, y + 1.7, f"{w_name.upper()}", fontsize=10, fontweight="bold", color="#fbbf24", ha="center")
        ax.text(x + 0.95, y + 1.45, f"Port: {port}", fontsize=8, color="#94a3b8", ha="center")
        ax.text(
            x + 0.95, y + 0.75,
            "• PoW SHA-256 ('0000')\n"
            "• Anti Double-Voting\n"
            "• Consensus Engine\n"
            "• REST API Server",
            fontsize=7, color="#fde68a", ha="center"
        )

        # Docker Volume Box underneath
        vol_box = patches.FancyBboxPatch(
            (x + 0.15, y - 1.5), 1.6, 0.9,
            boxstyle="round,pad=0.1", ec="#a855f7", fc="#241438", lw=1.2
        )
        ax.add_patch(vol_box)
        ax.text(x + 0.95, y - 0.9, "DOCKER VOLUME", fontsize=7.5, fontweight="bold", color="#c084fc", ha="center")
        ax.text(x + 0.95, y - 1.25, f"./data/{w_name.lower().replace(' ', '-')}", fontsize=6.8, color="#e9d5ff", ha="center")

        # Connection line Worker <-> Volume
        ax.plot([x + 0.95, x + 0.95], [y, y - 0.6], color="#a855f7", lw=1.2, ls=":")

    # Horizontal P2P Gossip arrows connecting workers
    ax.annotate(
        "", xy=(11.3, 3.5), xytext=(2.7, 3.5),
        arrowprops=dict(arrowstyle="<->", color="#fbbf24", lw=1.2, ls="--", mutation_scale=12)
    )
    ax.text(7.0, 3.65, "P2P Synchronization & Block Propagation (HTTP Gossip)", fontsize=8, color="#fbbf24", ha="center")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"[OK] Diagram arsitektur berhasil disimpan ke: {output_path}")


if __name__ == "__main__":
    generate_architecture_diagram()
