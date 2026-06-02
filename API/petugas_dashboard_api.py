from flask import Blueprint, jsonify, session
from configs.conn import get_db

petugas_dashboard_api = Blueprint(
    "api_petugas_dashboard", __name__, url_prefix="/api/petugas/dashboard"
)


# ─────────────────────────────────────────────
# Helper: ambil petugas_id dari session
# ─────────────────────────────────────────────
def get_petugas_id(cur):
    """Cari petugas.id berdasarkan pengguna_id yang ada di session."""
    uid = session.get("user", {}).get("id")
    if not uid:
        return None
    cur.execute(
        "SELECT id FROM petugas WHERE pengguna_id = %s AND aktif = 1", (uid,)
    )
    row = cur.fetchone()
    return row["id"] if row else None


# ─────────────────────────────────────────────
# 1. Ringkasan & kinerja
# ─────────────────────────────────────────────
@petugas_dashboard_api.route("/ringkasan", methods=["GET"])
def ringkasan():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = get_petugas_id(cur)
            if not pid:
                return jsonify({"message": "Petugas tidak ditemukan"}), 404

            # Info profil petugas
            cur.execute("""
                SELECT pt.unit_kerja, pt.jabatan
                FROM petugas pt
                WHERE pt.id = %s
            """, (pid,))
            profil = cur.fetchone()

            # Total ditugaskan
            cur.execute(
                "SELECT COUNT(*) AS n FROM pengaduan WHERE petugas_id = %s", (pid,)
            )
            total = cur.fetchone()["n"]

            # Per status
            cur.execute("""
                SELECT s.kode, COUNT(p.id) AS n
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id AND p.petugas_id = %s
                GROUP BY s.id, s.kode
            """, (pid,))
            status_map = {r["kode"]: r["n"] for r in cur.fetchall()}

            # Prioritas tinggi yang belum selesai
            cur.execute("""
                SELECT COUNT(*) AS n
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND p.prioritas = 3
                  AND s.kode NOT IN ('SELESAI', 'DITOLAK')
            """, (pid,))
            prioritas_tinggi = cur.fetchone()["n"]

            # Rata-rata penanganan (jam) — hanya yang sudah selesai
            cur.execute("""
                SELECT ROUND(AVG(
                    TIMESTAMPDIFF(HOUR, p.dibuat_pada, p.diselesaikan_pada)
                ), 1) AS avg_jam
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                WHERE p.petugas_id = %s AND s.kode = 'SELESAI'
            """, (pid,))
            avg_jam = cur.fetchone()["avg_jam"]

    finally:
        conn.close()

    belum = (status_map.get("MASUK", 0) or 0) + (status_map.get("VERIFIKASI", 0) or 0)

    return jsonify({
        "unit_kerja":      profil["unit_kerja"] if profil else None,
        "jabatan":         profil["jabatan"]    if profil else None,
        "total":           total,
        "belum":           belum,
        "diproses":        status_map.get("PROSES",   0) or 0,
        "selesai":         status_map.get("SELESAI",  0) or 0,
        "ditolak":         status_map.get("DITOLAK",  0) or 0,
        "prioritas_tinggi":prioritas_tinggi,
        "avg_jam":         avg_jam,
    })


# ─────────────────────────────────────────────
# 2. Tren penyelesaian 7 hari terakhir
# ─────────────────────────────────────────────
@petugas_dashboard_api.route("/tren7", methods=["GET"])
def tren7():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = get_petugas_id(cur)
            if not pid:
                return jsonify([])

            cur.execute("""
                SELECT
                    DATE(p.diselesaikan_pada)                    AS tgl_raw,
                    DATE_FORMAT(p.diselesaikan_pada, '%%d/%%m')  AS tgl,
                    COUNT(*)                                      AS selesai
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND s.kode = 'SELESAI'
                  AND DATE(p.diselesaikan_pada) >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                GROUP BY DATE(p.diselesaikan_pada)
                ORDER BY DATE(p.diselesaikan_pada)
            """, (pid,))
            rows = cur.fetchall()

            # Ambil CURDATE() dari MySQL langsung agar timezone konsisten
            cur.execute("SELECT CURDATE() AS hari_ini")
            hari_ini = cur.fetchone()["hari_ini"]

    finally:
        conn.close()

    from datetime import timedelta

    # Gunakan tanggal dari MySQL, bukan Python date.today()
    hari_map = {str(r["tgl_raw"]): r["selesai"] for r in rows}

    result = []
    for i in range(6, -1, -1):
        d = hari_ini - timedelta(days=i)
        label = d.strftime("%d/%m")
        result.append({
            "tgl":    label,
            "selesai": hari_map.get(str(d), 0)
        })

    return jsonify(result)


# ─────────────────────────────────────────────
# 3. Pengaduan prioritas tinggi yang belum selesai
# ─────────────────────────────────────────────
@petugas_dashboard_api.route("/prioritas-tinggi", methods=["GET"])
def prioritas_tinggi():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = get_petugas_id(cur)
            if not pid:
                return jsonify([])

            cur.execute("""
                SELECT
                    p.id, p.judul, p.lokasi, p.dibuat_pada,
                    s.nama  AS status,
                    s.warna AS warna_status,
                    s.kode  AS status_kode
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND p.prioritas = 3
                  AND s.kode NOT IN ('SELESAI', 'DITOLAK')
                ORDER BY p.dibuat_pada ASC
                LIMIT 5
            """, (pid,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "id":          r["id"],
        "judul":       r["judul"],
        "lokasi":      r["lokasi"],
        "dibuat_pada": r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "status":      r["status"],
        "warna_status":r["warna_status"],
        "status_kode": r["status_kode"],
    } for r in rows])


# ─────────────────────────────────────────────
# 4. Tugas baru ditugaskan (5 terbaru)
# ─────────────────────────────────────────────
@petugas_dashboard_api.route("/baru-ditugaskan", methods=["GET"])
def baru_ditugaskan():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = get_petugas_id(cur)
            if not pid:
                return jsonify([])

            cur.execute("""
                SELECT
                    p.id, p.judul, p.prioritas, p.dibuat_pada,
                    k.nama AS kategori,
                    s.kode AS status_kode
                FROM pengaduan p
                JOIN kategori k ON k.id = p.kategori_id
                JOIN status   s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND s.kode NOT IN ('SELESAI', 'DITOLAK')
                ORDER BY p.diperbarui_pada DESC
                LIMIT 5
            """, (pid,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "id":          r["id"],
        "judul":       r["judul"],
        "prioritas":   r["prioritas"],
        "dibuat_pada": r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "kategori":    r["kategori"],
        "status_kode": r["status_kode"],
    } for r in rows])


# ─────────────────────────────────────────────
# 5. Semua tugas aktif (belum selesai/ditolak)
# ─────────────────────────────────────────────
@petugas_dashboard_api.route("/tugas-aktif", methods=["GET"])
def tugas_aktif():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            pid = get_petugas_id(cur)
            if not pid:
                return jsonify([])

            cur.execute("""
                SELECT
                    p.id, p.judul, p.lokasi, p.prioritas, p.dibuat_pada,
                    k.nama  AS kategori,
                    s.nama  AS status,
                    s.kode  AS status_kode,
                    s.warna AS warna_status
                FROM pengaduan p
                JOIN kategori k ON k.id = p.kategori_id
                JOIN status   s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND s.kode NOT IN ('SELESAI', 'DITOLAK')
                ORDER BY p.prioritas DESC, p.dibuat_pada ASC
            """, (pid,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "id":          r["id"],
        "judul":       r["judul"],
        "lokasi":      r["lokasi"],
        "prioritas":   r["prioritas"],
        "dibuat_pada": r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "kategori":    r["kategori"],
        "status":      r["status"],
        "status_kode": r["status_kode"],
        "warna_status":r["warna_status"],
    } for r in rows])