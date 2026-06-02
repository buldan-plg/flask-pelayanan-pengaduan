from flask import Blueprint, jsonify
from configs.conn import get_db

dashboard_api = Blueprint("api_dashboard", __name__, url_prefix="/api/dashboard")


# ─────────────────────────────────────────────
# 1. Ringkasan angka untuk summary cards
# ─────────────────────────────────────────────
@dashboard_api.route("/ringkasan", methods=["GET"])
def ringkasan():
    conn = get_db()
    try:
        with conn.cursor() as cur:

            # Total pengaduan
            cur.execute("SELECT COUNT(*) AS n FROM pengaduan")
            total = cur.fetchone()["n"]

            # Per status (berdasarkan kode)
            cur.execute("""
                SELECT s.kode, COUNT(p.id) AS n
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id
                GROUP BY s.id, s.kode
            """)
            status_map = {row["kode"]: row["n"] for row in cur.fetchall()}

            # Jumlah warga aktif
            cur.execute(
                "SELECT COUNT(*) AS n FROM pengguna WHERE peran = 'warga' AND aktif = 1"
            )
            jml_warga = cur.fetchone()["n"]

            # Jumlah petugas aktif
            cur.execute("SELECT COUNT(*) AS n FROM petugas WHERE aktif = 1")
            jml_petugas = cur.fetchone()["n"]

    finally:
        conn.close()

    return jsonify({
        "total":       total,
        "masuk":       status_map.get("MASUK", 0),
        "verifikasi":  status_map.get("VERIFIKASI", 0),
        "diproses":    status_map.get("PROSES", 0),
        "selesai":     status_map.get("SELESAI", 0),
        "ditolak":     status_map.get("DITOLAK", 0),
        "jml_warga":   jml_warga,
        "jml_petugas": jml_petugas,
    })


# ─────────────────────────────────────────────
# 2. Statistik per kategori (untuk bar chart)
# ─────────────────────────────────────────────
@dashboard_api.route("/kategori", methods=["GET"])
def statistik_kategori():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    k.nama                                              AS kategori,
                    COUNT(p.id)                                         AS total,
                    SUM(s.kode = 'SELESAI')                            AS selesai,
                    SUM(s.kode = 'PROSES')                             AS diproses,
                    SUM(s.kode IN ('MASUK', 'VERIFIKASI'))             AS menunggu,
                    ROUND(AVG(
                        TIMESTAMPDIFF(HOUR, p.dibuat_pada,
                            IFNULL(p.diselesaikan_pada, NOW()))
                    ), 1)                                               AS rata_penanganan_jam
                FROM kategori k
                LEFT JOIN pengaduan p ON p.kategori_id = k.id
                LEFT JOIN status s    ON s.id = p.status_id
                GROUP BY k.id, k.nama
                ORDER BY total DESC
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    # Pastikan nilai NULL diganti 0
    result = []
    for r in rows:
        result.append({
            "kategori":            r["kategori"],
            "total":               r["total"] or 0,
            "selesai":             int(r["selesai"] or 0),
            "diproses":            int(r["diproses"] or 0),
            "menunggu":            int(r["menunggu"] or 0),
            "rata_penanganan_jam": r["rata_penanganan_jam"],
        })

    return jsonify(result)


# ─────────────────────────────────────────────
# 3. Jumlah per status (untuk doughnut chart)
# ─────────────────────────────────────────────
@dashboard_api.route("/status", methods=["GET"])
def statistik_status():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.nama,
                    s.warna,
                    COUNT(p.id) AS jumlah
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id
                GROUP BY s.id, s.nama, s.warna
                ORDER BY s.id
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([
        {"nama": r["nama"], "warna": r["warna"], "jumlah": r["jumlah"] or 0}
        for r in rows
    ])


# ─────────────────────────────────────────────
# 4. Daftar pengaduan terbaru (limit 10)
# ─────────────────────────────────────────────
@dashboard_api.route("/pengaduan-terbaru", methods=["GET"])
def pengaduan_terbaru():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.id,
                    p.judul,
                    p.lokasi,
                    p.prioritas,
                    p.dibuat_pada,
                    pg.nama_lengkap  AS pelapor,
                    k.nama           AS kategori,
                    s.nama           AS status,
                    s.warna          AS warna_status
                FROM pengaduan p
                JOIN pengguna  pg ON pg.id = p.pengguna_id
                JOIN kategori   k ON k.id  = p.kategori_id
                JOIN status     s ON s.id  = p.status_id
                ORDER BY p.dibuat_pada DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for r in rows:
        result.append({
            "id":           r["id"],
            "judul":        r["judul"],
            "lokasi":       r["lokasi"],
            "prioritas":    r["prioritas"],
            "dibuat_pada":  r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
            "pelapor":      r["pelapor"],
            "kategori":     r["kategori"],
            "status":       r["status"],
            "warna_status": r["warna_status"],
        })

    return jsonify(result)