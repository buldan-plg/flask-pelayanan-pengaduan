from flask import Blueprint, jsonify, request
from configs.conn import get_db
from datetime import date, datetime

laporan_api = Blueprint("api_laporan", __name__, url_prefix="/api/laporan")


# ─────────────────────────────────────────────
# Helper: ambil filter dari query string
# ─────────────────────────────────────────────
def get_filters():
    dari    = request.args.get("dari",    "2000-01-01")
    sampai  = request.args.get("sampai",  date.today().isoformat())
    kategori= request.args.get("kategori", "")   # id kategori (opsional)
    status  = request.args.get("status",   "")   # kode status  (opsional)
    return dari, sampai, kategori, status


def build_where(dari, sampai, kategori, status, alias_p="p"):
    """Kembalikan (where_clause, params_list)."""
    clauses = [f"{alias_p}.dibuat_pada BETWEEN %s AND %s"]
    params  = [f"{dari} 00:00:00", f"{sampai} 23:59:59"]

    if kategori:
        clauses.append(f"{alias_p}.kategori_id = %s")
        params.append(kategori)

    if status:
        clauses.append("s.kode = %s")
        params.append(status)

    return "WHERE " + " AND ".join(clauses), params


# ─────────────────────────────────────────────
# 0. Opsi untuk dropdown filter
# ─────────────────────────────────────────────
@laporan_api.route("/filter-options", methods=["GET"])
def filter_options():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nama FROM kategori ORDER BY nama")
            kategori = cur.fetchall()

            cur.execute("SELECT kode, nama FROM status ORDER BY id")
            status = cur.fetchall()
    finally:
        conn.close()

    return jsonify({"kategori": kategori, "status": status})


# ─────────────────────────────────────────────
# 1. Ringkasan angka (summary cards)
# ─────────────────────────────────────────────
@laporan_api.route("/ringkasan", methods=["GET"])
def ringkasan():
    dari, sampai, kategori, status = get_filters()
    where, params = build_where(dari, sampai, kategori, status)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    COUNT(p.id)                                        AS total,
                    SUM(s.kode = 'SELESAI')                           AS selesai,
                    SUM(s.kode = 'PROSES')                            AS proses,
                    SUM(s.kode = 'DITOLAK')                           AS ditolak,
                    SUM(s.kode IN ('MASUK','VERIFIKASI'))              AS menunggu,
                    ROUND(AVG(
                        CASE WHEN p.diselesaikan_pada IS NOT NULL
                        THEN TIMESTAMPDIFF(HOUR, p.dibuat_pada, p.diselesaikan_pada)
                        END
                    ), 1)                                              AS avg_jam
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                {where}
            """, params)
            row = cur.fetchone()
    finally:
        conn.close()

    return jsonify({
        "total":    row["total"]    or 0,
        "selesai":  int(row["selesai"]  or 0),
        "proses":   int(row["proses"]   or 0),
        "ditolak":  int(row["ditolak"]  or 0),
        "menunggu": int(row["menunggu"] or 0),
        "avg_jam":  row["avg_jam"],
    })


# ─────────────────────────────────────────────
# 2. Tren pengaduan (harian / mingguan / bulanan)
# ─────────────────────────────────────────────
@laporan_api.route("/tren", methods=["GET"])
def tren():
    dari, sampai, kategori, status = get_filters()
    granularity = request.args.get("granularity", "harian")

    # Format group-by berdasarkan granularity
    fmt_map = {
        "harian":   "%Y-%m-%d",
        "mingguan": "%x-W%v",
        "bulanan":  "%Y-%m",
    }
    fmt = fmt_map.get(granularity, "%Y-%m-%d")

    where, params = build_where(dari, sampai, kategori, status)
    # Duplikasi params karena dipakai 2 subquery
    params_x2 = params + params

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    periode,
                    SUM(masuk)   AS masuk,
                    SUM(selesai) AS selesai
                FROM (
                    SELECT
                        DATE_FORMAT(p.dibuat_pada, '{fmt}') AS periode,
                        COUNT(p.id)                          AS masuk,
                        0                                    AS selesai
                    FROM pengaduan p
                    JOIN status s ON s.id = p.status_id
                    {where}
                    GROUP BY periode

                    UNION ALL

                    SELECT
                        DATE_FORMAT(p.diselesaikan_pada, '{fmt}') AS periode,
                        0                                          AS masuk,
                        COUNT(p.id)                                AS selesai
                    FROM pengaduan p
                    JOIN status s ON s.id = p.status_id
                    {where}
                    AND p.diselesaikan_pada IS NOT NULL
                    GROUP BY periode
                ) combined
                GROUP BY periode
                ORDER BY periode
            """, params_x2)
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([
        {"periode": r["periode"], "masuk": r["masuk"] or 0, "selesai": r["selesai"] or 0}
        for r in rows
    ])


# ─────────────────────────────────────────────
# 3. Statistik per kategori
# ─────────────────────────────────────────────
@laporan_api.route("/kategori", methods=["GET"])
def statistik_kategori():
    dari, sampai, kategori, status = get_filters()
    where, params = build_where(dari, sampai, kategori, status)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    k.nama                                          AS kategori,
                    COUNT(p.id)                                     AS total,
                    SUM(s.kode = 'SELESAI')                        AS selesai,
                    SUM(s.kode = 'PROSES')                         AS diproses,
                    SUM(s.kode IN ('MASUK','VERIFIKASI'))           AS menunggu
                FROM kategori k
                LEFT JOIN pengaduan p ON p.kategori_id = k.id
                LEFT JOIN status    s ON s.id = p.status_id
                    AND p.dibuat_pada BETWEEN %s AND %s
                    {'AND p.kategori_id = %s' if kategori else ''}
                    {'AND s.kode = %s'        if status   else ''}
                GROUP BY k.id, k.nama
                ORDER BY total DESC
            """, [f"{dari} 00:00:00", f"{sampai} 23:59:59"]
               + ([kategori] if kategori else [])
               + ([status]   if status   else []))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "kategori": r["kategori"],
        "total":    r["total"]    or 0,
        "selesai":  int(r["selesai"]  or 0),
        "diproses": int(r["diproses"] or 0),
        "menunggu": int(r["menunggu"] or 0),
    } for r in rows])


# ─────────────────────────────────────────────
# 4. Distribusi status (untuk doughnut)
# ─────────────────────────────────────────────
@laporan_api.route("/status", methods=["GET"])
def statistik_status():
    dari, sampai, kategori, status = get_filters()
    where, params = build_where(dari, sampai, kategori, status)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT s.nama, s.warna, COUNT(p.id) AS jumlah
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id
                    AND p.dibuat_pada BETWEEN %s AND %s
                    {'AND p.kategori_id = %s' if kategori else ''}
                GROUP BY s.id, s.nama, s.warna
                ORDER BY s.id
            """, [f"{dari} 00:00:00", f"{sampai} 23:59:59"]
               + ([kategori] if kategori else []))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "nama": r["nama"], "warna": r["warna"], "jumlah": r["jumlah"] or 0
    } for r in rows])


# ─────────────────────────────────────────────
# 5. Distribusi prioritas
# ─────────────────────────────────────────────
@laporan_api.route("/prioritas", methods=["GET"])
def statistik_prioritas():
    dari, sampai, kategori, status = get_filters()
    where, params = build_where(dari, sampai, kategori, status)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.prioritas, COUNT(*) AS jumlah
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                {where}
                GROUP BY p.prioritas
                ORDER BY p.prioritas
            """, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    label_map = {1: "Rendah", 2: "Sedang", 3: "Tinggi"}
    # Pastikan semua 3 prioritas muncul meskipun 0
    data = {1: 0, 2: 0, 3: 0}
    for r in rows:
        data[r["prioritas"]] = r["jumlah"]

    return jsonify([
        {"prioritas": k, "label": label_map[k], "jumlah": v}
        for k, v in data.items()
    ])


# ─────────────────────────────────────────────
# 6. Kinerja per petugas
# ─────────────────────────────────────────────
@laporan_api.route("/petugas", methods=["GET"])
def kinerja_petugas():
    dari, sampai, kategori, status = get_filters()

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    pg.nama_lengkap                                      AS nama,
                    pt.unit_kerja,
                    COUNT(p.id)                                          AS ditugaskan,
                    SUM(s.kode = 'SELESAI')                             AS selesai,
                    SUM(s.kode = 'PROSES')                              AS diproses,
                    ROUND(AVG(
                        CASE WHEN p.diselesaikan_pada IS NOT NULL
                        THEN TIMESTAMPDIFF(HOUR, p.dibuat_pada, p.diselesaikan_pada)
                        END
                    ), 1)                                                AS avg_jam
                FROM petugas pt
                JOIN pengguna pg ON pg.id = pt.pengguna_id
                LEFT JOIN pengaduan p ON p.petugas_id = pt.id
                    AND p.dibuat_pada BETWEEN %s AND %s
                    %s
                LEFT JOIN status s ON s.id = p.status_id
                WHERE pt.aktif = 1
                GROUP BY pt.id, pg.nama_lengkap, pt.unit_kerja
                ORDER BY ditugaskan DESC
            """, [
                f"{dari} 00:00:00",
                f"{sampai} 23:59:59",
                f"AND p.kategori_id = {int(kategori)}" if kategori else "",
            ])
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "nama":        r["nama"],
        "unit_kerja":  r["unit_kerja"],
        "ditugaskan":  r["ditugaskan"] or 0,
        "selesai":     int(r["selesai"]  or 0),
        "diproses":    int(r["diproses"] or 0),
        "avg_jam":     r["avg_jam"],
    } for r in rows])


# ─────────────────────────────────────────────
# 7. Tabel detail untuk export & tampilan
# ─────────────────────────────────────────────
@laporan_api.route("/detail", methods=["GET"])
def detail():
    dari, sampai, kategori, status = get_filters()
    where, params = build_where(dari, sampai, kategori, status)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    p.id,
                    p.judul,
                    p.lokasi,
                    p.prioritas,
                    p.dibuat_pada,
                    p.diselesaikan_pada,
                    pg.nama_lengkap                                      AS pelapor,
                    k.nama                                               AS kategori,
                    s.nama                                               AS status,
                    s.warna                                              AS warna_status,
                    pg_pt.nama_lengkap                                   AS petugas,
                    CASE WHEN p.diselesaikan_pada IS NOT NULL
                         THEN TIMESTAMPDIFF(HOUR, p.dibuat_pada, p.diselesaikan_pada)
                    END                                                  AS durasi_jam
                FROM pengaduan p
                JOIN pengguna  pg   ON pg.id  = p.pengguna_id
                JOIN kategori   k   ON k.id   = p.kategori_id
                JOIN status     s   ON s.id   = p.status_id
                LEFT JOIN petugas pt      ON pt.id  = p.petugas_id
                LEFT JOIN pengguna pg_pt  ON pg_pt.id = pt.pengguna_id
                {where}
                ORDER BY p.dibuat_pada DESC
            """, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for r in rows:
        result.append({
            "id":               r["id"],
            "judul":            r["judul"],
            "lokasi":           r["lokasi"],
            "prioritas":        r["prioritas"],
            "dibuat_pada":      r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
            "diselesaikan_pada":r["diselesaikan_pada"].isoformat() if r["diselesaikan_pada"] else None,
            "pelapor":          r["pelapor"],
            "kategori":         r["kategori"],
            "status":           r["status"],
            "warna_status":     r["warna_status"],
            "petugas":          r["petugas"],
            "durasi_jam":       r["durasi_jam"],
        })

    return jsonify(result)