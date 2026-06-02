from flask import Blueprint, jsonify, request, session
from configs.conn import get_db

petugas_pengaduan_api = Blueprint(
    "api_petugas_pengaduan", __name__, url_prefix="/api/petugas/pengaduan"
)


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
def current_user_id():
    return session.get("user", {}).get("id")


def get_petugas_id(cur, pengguna_id):
    """Ambil petugas.id berdasarkan pengguna.id yang sedang login."""
    cur.execute(
        "SELECT id FROM petugas WHERE pengguna_id = %s AND aktif = 1",
        (pengguna_id,)
    )
    row = cur.fetchone()
    return row["id"] if row else None


def require_petugas(cur):
    """
    Validasi sesi adalah petugas aktif.
    Mengembalikan (petugas_id, None) jika valid,
    atau (None, response_tuple) jika tidak valid.
    """
    uid = current_user_id()
    if not uid:
        return None, (jsonify({"message": "Unauthorized"}), 401)

    petugas_id = get_petugas_id(cur, uid)
    if not petugas_id:
        return None, (jsonify({"message": "Akun ini bukan petugas aktif"}), 403)

    return petugas_id, None


# ─────────────────────────────────────────────
# 1. Daftar pengaduan milik petugas (filter + paginasi)
# ─────────────────────────────────────────────
@petugas_pengaduan_api.route("", methods=["GET"])
def get_pengaduan():
    status    = request.args.get("status",    "")
    kategori  = request.args.get("kategori",  "")
    prioritas = request.args.get("prioritas", "")
    cari      = request.args.get("cari",      "")
    page      = max(1, int(request.args.get("page",     1)))
    per_page  = max(1, int(request.args.get("per_page", 15)))
    offset    = (page - 1) * per_page

    conn = get_db()
    try:
        with conn.cursor() as cur:
            petugas_id, err = require_petugas(cur)
            if err:
                return err

            clauses = ["p.petugas_id = %s"]
            params  = [petugas_id]

            # Petugas hanya boleh melihat status VERIFIKASI, PROSES, SELESAI
            ALLOWED_STATUS = {"VERIFIKASI", "PROSES", "SELESAI"}
            if status and status.upper() in ALLOWED_STATUS:
                clauses.append("s.kode = %s")
                params.append(status.upper())
            elif not status:
                clauses.append("s.kode IN ('VERIFIKASI', 'PROSES', 'SELESAI')")

            if kategori:
                clauses.append("p.kategori_id = %s")
                params.append(kategori)
            if prioritas:
                clauses.append("p.prioritas = %s")
                params.append(prioritas)
            if cari:
                clauses.append("p.judul LIKE %s")
                params.append(f"%{cari}%")

            where = "WHERE " + " AND ".join(clauses)

            # Total
            cur.execute(f"""
                SELECT COUNT(*) AS n
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                {where}
            """, params)
            total = cur.fetchone()["n"]

            # Data
            cur.execute(f"""
                SELECT
                    p.id, p.judul, p.lokasi, p.prioritas, p.dibuat_pada,
                    pg.nama_lengkap AS pelapor,
                    k.nama          AS kategori,
                    s.nama          AS status,
                    s.kode          AS status_kode,
                    s.warna         AS warna_status,
                    (SELECT COUNT(*) FROM lampiran  l  WHERE l.pengaduan_id  = p.id) AS jumlah_lampiran,
                    (SELECT COUNT(*) FROM komentar  km WHERE km.pengaduan_id = p.id
                        AND km.adalah_internal = 0) AS jumlah_komentar
                FROM pengaduan p
                JOIN pengguna  pg ON pg.id = p.pengguna_id
                JOIN kategori   k ON k.id  = p.kategori_id
                JOIN status     s ON s.id  = p.status_id
                {where}
                ORDER BY
                    FIELD(s.kode, 'VERIFIKASI', 'PROSES', 'SELESAI'),
                    p.prioritas DESC,
                    p.dibuat_pada DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()
    finally:
        conn.close()

    data = [{
        "id":             r["id"],
        "judul":          r["judul"],
        "lokasi":         r["lokasi"],
        "prioritas":      r["prioritas"],
        "dibuat_pada":    r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "pelapor":        r["pelapor"],
        "kategori":       r["kategori"],
        "status":         r["status"],
        "status_kode":    r["status_kode"],
        "warna_status":   r["warna_status"],
        "jumlah_lampiran":r["jumlah_lampiran"],
        "jumlah_komentar":r["jumlah_komentar"],
    } for r in rows]

    return jsonify({"data": data, "total": total})


# ─────────────────────────────────────────────
# 2. Counter badge per status (untuk tab navigasi)
# ─────────────────────────────────────────────
@petugas_pengaduan_api.route("/counter", methods=["GET"])
def counter():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            petugas_id, err = require_petugas(cur)
            if err:
                return err

            cur.execute("""
                SELECT s.kode, COUNT(p.id) AS n
                FROM status s
                LEFT JOIN pengaduan p
                    ON p.status_id = s.id
                    AND p.petugas_id = %s
                    AND s.kode IN ('VERIFIKASI', 'PROSES', 'SELESAI')
                WHERE s.kode IN ('VERIFIKASI', 'PROSES', 'SELESAI')
                GROUP BY s.id, s.kode
            """, (petugas_id,))
            rows = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) AS n FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                WHERE p.petugas_id = %s
                  AND s.kode IN ('VERIFIKASI', 'PROSES', 'SELESAI')
            """, (petugas_id,))
            semua = cur.fetchone()["n"]
    finally:
        conn.close()

    result = {"semua": semua}
    for r in rows:
        result[r["kode"]] = r["n"]
    return jsonify(result)


# ─────────────────────────────────────────────
# 3. Ubah status pengaduan (hanya PROSES / SELESAI)
#    Petugas tidak boleh memverifikasi atau menolak.
#    Endpoint ini adalah guard tambahan di sisi server;
#    /api/pengaduan/<id>/status tetap dipakai untuk aksi,
#    tetapi pemanggil frontend bisa juga pakai endpoint ini
#    agar validasi peran lebih ketat.
# ─────────────────────────────────────────────
@petugas_pengaduan_api.route("/<int:id>/status", methods=["PUT"])
def ubah_status(id):
    body   = request.get_json()
    kode   = (body.get("kode") or "").upper()
    catatan = body.get("catatan", "")

    ALLOWED = {"PROSES", "SELESAI"}
    if kode not in ALLOWED:
        return jsonify({
            "message": f"Petugas hanya dapat mengubah status ke: {', '.join(ALLOWED)}"
        }), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            petugas_id, err = require_petugas(cur)
            if err:
                return err

            # Pastikan pengaduan ini memang milik petugas yang login
            cur.execute(
                "SELECT id, status_id FROM pengaduan WHERE id = %s AND petugas_id = %s",
                (id, petugas_id)
            )
            pengaduan = cur.fetchone()
            if not pengaduan:
                return jsonify({"message": "Pengaduan tidak ditemukan atau bukan milik Anda"}), 404

            # Ambil status_id tujuan
            cur.execute("SELECT id FROM status WHERE kode = %s", (kode,))
            status_row = cur.fetchone()
            if not status_row:
                return jsonify({"message": "Status tidak ditemukan"}), 404

            selesai_expr = "NOW()" if kode == "SELESAI" else "NULL"
            cur.execute(f"""
                UPDATE pengaduan
                SET status_id         = %s,
                    diselesaikan_pada = {selesai_expr},
                    diperbarui_pada   = NOW()
                WHERE id = %s
            """, (status_row["id"], id))

            # Komentar internal otomatis
            uid = current_user_id()
            if uid:
                isi_auto = f"[{kode}] {catatan}" if catatan else f"Status diubah ke {kode}."
                cur.execute("""
                    INSERT INTO komentar (pengaduan_id, pengguna_id, isi, adalah_internal)
                    VALUES (%s, %s, %s, 1)
                """, (id, uid, isi_auto))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("petugas ubah_status error:", e)
        return jsonify({"message": "Gagal memperbarui status"}), 500
    finally:
        conn.close()

    return jsonify({"message": f"Status berhasil diubah ke {kode}"})