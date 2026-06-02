from flask import Blueprint, jsonify, session
from configs.conn import get_db

warga_dashboard_api = Blueprint(
    "api_warga_dashboard", __name__, url_prefix="/api/warga/dashboard"
)


# ─────────────────────────────────────────────
# Helper: ambil pengguna_id dari session
# ─────────────────────────────────────────────
def get_uid():
    return session.get("user", {}).get("id")


# ─────────────────────────────────────────────
# 1. Ringkasan statistik milik warga ini
# ─────────────────────────────────────────────
@warga_dashboard_api.route("/ringkasan", methods=["GET"])
def ringkasan():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:

            # Total
            cur.execute(
                "SELECT COUNT(*) AS n FROM pengaduan WHERE pengguna_id = %s", (uid,)
            )
            total = cur.fetchone()["n"]

            # Per status
            cur.execute("""
                SELECT s.kode, s.nama, s.warna, COUNT(p.id) AS jumlah
                FROM status s
                LEFT JOIN pengaduan p
                    ON p.status_id = s.id AND p.pengguna_id = %s
                GROUP BY s.id, s.kode, s.nama, s.warna
                ORDER BY s.id
            """, (uid,))
            per_status = cur.fetchall()

    finally:
        conn.close()

    status_map = {r["kode"]: r["jumlah"] or 0 for r in per_status}

    return jsonify({
        "total":    total,
        "diproses": status_map.get("PROSES",   0),
        "selesai":  status_map.get("SELESAI",  0),
        "ditolak":  status_map.get("DITOLAK",  0),
        "menunggu": status_map.get("MASUK",    0) + status_map.get("VERIFIKASI", 0),
        "per_status": [{
            "kode":   r["kode"],
            "nama":   r["nama"],
            "warna":  r["warna"],
            "jumlah": r["jumlah"] or 0,
        } for r in per_status if (r["jumlah"] or 0) > 0],
    })


# ─────────────────────────────────────────────
# 2. Pengaduan terbaru milik warga (limit 5)
# ─────────────────────────────────────────────
@warga_dashboard_api.route("/terbaru", methods=["GET"])
def terbaru():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
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
                WHERE p.pengguna_id = %s
                ORDER BY p.dibuat_pada DESC
                LIMIT 5
            """, (uid,))
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


# ─────────────────────────────────────────────
# 3. Update / komentar publik terbaru pada
#    pengaduan milik warga ini (limit 7)
# ─────────────────────────────────────────────
@warga_dashboard_api.route("/update-terbaru", methods=["GET"])
def update_terbaru():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    k.isi,
                    k.dibuat_pada,
                    p.judul         AS judul_pengaduan,
                    p.id            AS pengaduan_id,
                    pg.nama_lengkap AS nama_pengirim
                FROM komentar k
                JOIN pengaduan p  ON p.id  = k.pengaduan_id
                JOIN pengguna  pg ON pg.id = k.pengguna_id
                WHERE p.pengguna_id   = %s
                  AND k.adalah_internal = 0
                  AND k.pengguna_id   != %s
                ORDER BY k.dibuat_pada DESC
                LIMIT 7
            """, (uid, uid))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "isi":              r["isi"],
        "dibuat_pada":      r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "judul_pengaduan":  r["judul_pengaduan"],
        "pengaduan_id":     r["pengaduan_id"],
        "nama_pengirim":    r["nama_pengirim"],
    } for r in rows])