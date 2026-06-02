from flask import Blueprint, jsonify, request, session
from configs.conn import get_db
from datetime import datetime

pengaduan_api = Blueprint("api_pengaduan", __name__, url_prefix="/api/pengaduan")


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
def current_user_id():
    return session.get("user", {}).get("id")

def get_status_id(cur, kode):
    cur.execute("SELECT id FROM status WHERE kode = %s", (kode,))
    row = cur.fetchone()
    return row["id"] if row else None


# ─────────────────────────────────────────────
# 1. Daftar pengaduan (dengan filter + paginasi)
# ─────────────────────────────────────────────
@pengaduan_api.route("", methods=["GET"])
def get_pengaduan():
    status   = request.args.get("status",    "")
    kategori = request.args.get("kategori",  "")
    prioritas= request.args.get("prioritas", "")
    cari     = request.args.get("cari",      "")
    page     = max(1, int(request.args.get("page",     1)))
    per_page = max(1, int(request.args.get("per_page", 15)))
    offset   = (page - 1) * per_page

    clauses = []
    params  = []

    if status:
        clauses.append("s.kode = %s");    params.append(status)
    if kategori:
        clauses.append("p.kategori_id = %s"); params.append(kategori)
    if prioritas:
        clauses.append("p.prioritas = %s");   params.append(prioritas)
    if cari:
        clauses.append("(p.judul LIKE %s OR pg.nama_lengkap LIKE %s)")
        params += [f"%{cari}%", f"%{cari}%"]

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Total
            cur.execute(f"""
                SELECT COUNT(*) AS n
                FROM pengaduan p
                JOIN pengguna  pg ON pg.id = p.pengguna_id
                JOIN status     s ON s.id  = p.status_id
                {where}
            """, params)
            total = cur.fetchone()["n"]

            # Data
            cur.execute(f"""
                SELECT
                    p.id, p.judul, p.lokasi, p.prioritas, p.dibuat_pada,
                    pg.nama_lengkap  AS pelapor,
                    k.nama           AS kategori,
                    s.nama           AS status,
                    s.kode           AS status_kode,
                    s.warna          AS warna_status,
                    pt.unit_kerja    AS unit_petugas,
                    (SELECT COUNT(*) FROM lampiran  l  WHERE l.pengaduan_id  = p.id) AS jumlah_lampiran,
                    (SELECT COUNT(*) FROM komentar  km WHERE km.pengaduan_id = p.id
                        AND km.adalah_internal = 0) AS jumlah_komentar
                FROM pengaduan p
                JOIN pengguna  pg ON pg.id = p.pengguna_id
                JOIN kategori   k ON k.id  = p.kategori_id
                JOIN status     s ON s.id  = p.status_id
                LEFT JOIN petugas pt ON pt.id = p.petugas_id
                {where}
                ORDER BY p.dibuat_pada DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()
    finally:
        conn.close()

    data = []
    for r in rows:
        data.append({
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
            "unit_petugas":   r["unit_petugas"],
            "jumlah_lampiran":r["jumlah_lampiran"],
            "jumlah_komentar":r["jumlah_komentar"],
        })

    return jsonify({"data": data, "total": total})


# ─────────────────────────────────────────────
# 2. Counter per status (untuk badge tab)
# ─────────────────────────────────────────────
@pengaduan_api.route("/counter", methods=["GET"])
def counter():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.kode, COUNT(p.id) AS n
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id
                GROUP BY s.id, s.kode
            """)
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS n FROM pengaduan")
            semua = cur.fetchone()["n"]
    finally:
        conn.close()

    result = {"semua": semua}
    for r in rows:
        result[r["kode"]] = r["n"]
    return jsonify(result)


# ─────────────────────────────────────────────
# 3. Detail satu pengaduan
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>", methods=["GET"])
def get_detail(id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.id, p.judul, p.deskripsi, p.lokasi,
                    p.latitude, p.longitude,
                    p.prioritas, p.dibuat_pada, p.diselesaikan_pada,
                    p.petugas_id,
                    pg.nama_lengkap  AS pelapor,
                    k.nama           AS kategori,
                    s.nama           AS status,
                    s.kode           AS status_kode,
                    s.warna          AS warna_status,
                    pt.unit_kerja    AS unit_petugas,
                    (SELECT COUNT(*) FROM lampiran  l  WHERE l.pengaduan_id  = p.id) AS jumlah_lampiran,
                    (SELECT COUNT(*) FROM komentar  km WHERE km.pengaduan_id = p.id
                        AND km.adalah_internal = 0) AS jumlah_komentar
                FROM pengaduan p
                JOIN pengguna  pg ON pg.id = p.pengguna_id
                JOIN kategori   k ON k.id  = p.kategori_id
                JOIN status     s ON s.id  = p.status_id
                LEFT JOIN petugas pt ON pt.id = p.petugas_id
                WHERE p.id = %s
            """, (id,))
            p = cur.fetchone()

            if not p:
                return jsonify({"message": "Pengaduan tidak ditemukan"}), 404

            # Lampiran
            cur.execute("""
                SELECT id, nama_file, tipe_file, url_file, ukuran_byte, diunggah_pada
                FROM lampiran WHERE pengaduan_id = %s
            """, (id,))
            lampiran = cur.fetchall()
    finally:
        conn.close()

    return jsonify({
        "id":               p["id"],
        "judul":            p["judul"],
        "deskripsi":        p["deskripsi"],
        "lokasi":           p["lokasi"],
        "latitude":         float(p["latitude"])  if p["latitude"]  else None,
        "longitude":        float(p["longitude"]) if p["longitude"] else None,
        "prioritas":        p["prioritas"],
        "dibuat_pada":      p["dibuat_pada"].isoformat()      if p["dibuat_pada"]      else None,
        "diselesaikan_pada":p["diselesaikan_pada"].isoformat()if p["diselesaikan_pada"]else None,
        "petugas_id":       p["petugas_id"],
        "pelapor":          p["pelapor"],
        "kategori":         p["kategori"],
        "status":           p["status"],
        "status_kode":      p["status_kode"],
        "warna_status":     p["warna_status"],
        "unit_petugas":     p["unit_petugas"],
        "jumlah_lampiran":  p["jumlah_lampiran"],
        "jumlah_komentar":  p["jumlah_komentar"],
        "lampiran": [{
            "id":           l["id"],
            "nama_file":    l["nama_file"],
            "tipe_file":    l["tipe_file"],
            "url_file":     l["url_file"],
            "ukuran_byte":  l["ukuran_byte"],
        } for l in lampiran],
    })


# ─────────────────────────────────────────────
# 4. Ubah status pengaduan
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>/status", methods=["PUT"])
def ubah_status(id):
    body   = request.get_json()
    kode   = body.get("kode", "").upper()
    catatan= body.get("catatan", "")

    VALID = {"MASUK", "VERIFIKASI", "PROSES", "SELESAI", "DITOLAK"}
    if kode not in VALID:
        return jsonify({"message": "Kode status tidak valid"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            status_id = get_status_id(cur, kode)
            if not status_id:
                return jsonify({"message": "Status tidak ditemukan"}), 404

            selesai_pada = "NOW()" if kode == "SELESAI" else "NULL"

            cur.execute(f"""
                UPDATE pengaduan
                SET status_id = %s,
                    diselesaikan_pada = {selesai_pada},
                    diperbarui_pada = NOW()
                WHERE id = %s
            """, (status_id, id))

            # Simpan komentar otomatis jika ada catatan
            if catatan:
                uid = current_user_id()
                if uid:
                    cur.execute("""
                        INSERT INTO komentar (pengaduan_id, pengguna_id, isi, adalah_internal)
                        VALUES (%s, %s, %s, 1)
                    """, (id, uid, f"[{kode}] {catatan}"))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("ubah_status error:", e)
        return jsonify({"message": "Gagal memperbarui status"}), 500
    finally:
        conn.close()

    return jsonify({"message": f"Status berhasil diubah ke {kode}"})


# ─────────────────────────────────────────────
# 5. Assign petugas
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>/assign", methods=["PUT"])
def assign_petugas(id):
    body       = request.get_json()
    petugas_id = body.get("petugas_id")
    print(petugas_id)

    if not petugas_id:
        return jsonify({"message": "petugas_id wajib diisi"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Validasi petugas ada & aktif
            cur.execute("SELECT id FROM petugas WHERE id = %s AND aktif = 1", (petugas_id,))
            if not cur.fetchone():
                return jsonify({"message": "Petugas tidak ditemukan atau tidak aktif"}), 404

            cur.execute("""
                UPDATE pengaduan
                SET petugas_id = %s, diperbarui_pada = NOW()
                WHERE id = %s
            """, (petugas_id, id))

            # Komentar internal otomatis
            uid = current_user_id()
            if uid:
                cur.execute("""
                    SELECT pg.nama_lengkap FROM petugas pt
                    JOIN pengguna pg ON pg.id = pt.pengguna_id
                    WHERE pt.id = %s
                """, (petugas_id,))
                nama_pt = cur.fetchone()
                nama_pt = nama_pt["nama_lengkap"] if nama_pt else "—"

                cur.execute("""
                    INSERT INTO komentar (pengaduan_id, pengguna_id, isi, adalah_internal)
                    VALUES (%s, %s, %s, 1)
                """, (id, uid, f"Pengaduan ditugaskan kepada {nama_pt}."))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("assign_petugas error:", e)
        return jsonify({"message": "Gagal menugaskan petugas"}), 500
    finally:
        conn.close()

    return jsonify({"message": "Petugas berhasil ditugaskan"})


# ─────────────────────────────────────────────
# 6. Ubah prioritas
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>/prioritas", methods=["PUT"])
def ubah_prioritas(id):
    body     = request.get_json()
    prioritas= body.get("prioritas")

    if prioritas not in (1, 2, 3):
        return jsonify({"message": "Prioritas harus 1, 2, atau 3"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pengaduan SET prioritas = %s, diperbarui_pada = NOW()
                WHERE id = %s
            """, (prioritas, id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Gagal memperbarui prioritas"}), 500
    finally:
        conn.close()

    return jsonify({"message": "Prioritas diperbarui"})


# ─────────────────────────────────────────────
# 7. Komentar - GET
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>/komentar", methods=["GET"])
def get_komentar(id):
    mode = request.args.get("mode", "publik")  # publik | internal | semua

    where = ""
    if mode == "publik":
        where = "AND k.adalah_internal = 0"
    elif mode == "internal":
        where = "AND k.adalah_internal = 1"

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    k.id, k.isi, k.adalah_internal, k.dibuat_pada,
                    pg.nama_lengkap AS nama,
                    pg.peran
                FROM komentar k
                JOIN pengguna pg ON pg.id = k.pengguna_id
                WHERE k.pengaduan_id = %s {where}
                ORDER BY k.dibuat_pada ASC
            """, (id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "id":             r["id"],
        "isi":            r["isi"],
        "adalah_internal":r["adalah_internal"],
        "dibuat_pada":    r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
        "nama":           r["nama"],
        "peran":          r["peran"],
    } for r in rows])


# ─────────────────────────────────────────────
# 8. Komentar - POST
# ─────────────────────────────────────────────
@pengaduan_api.route("/<int:id>/komentar", methods=["POST"])
def post_komentar(id):
    body     = request.get_json()
    isi      = (body.get("isi") or "").strip()
    internal = int(body.get("adalah_internal", 0))
    uid      = current_user_id()
    # print(session.get("user"))
    

    if not isi:
        return jsonify({"message": "Isi komentar tidak boleh kosong"}), 400
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO komentar (pengaduan_id, pengguna_id, isi, adalah_internal)
                VALUES (%s, %s, %s, %s)
            """, (id, uid, isi, internal))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("post_komentar error:", e)
        return jsonify({"message": "Gagal menyimpan komentar"}), 500
    finally:
        conn.close()

    return jsonify({"message": "Komentar berhasil dikirim"}), 201


# ─────────────────────────────────────────────
# 9. Daftar petugas aktif (untuk dropdown assign)
# ─────────────────────────────────────────────
@pengaduan_api.route("/petugas-aktif", methods=["GET"])
def petugas_aktif():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pt.id, pg.nama_lengkap AS nama, pt.unit_kerja, pt.jabatan
                FROM petugas pt
                JOIN pengguna pg ON pg.id = pt.pengguna_id
                WHERE pt.aktif = 1
                ORDER BY pg.nama_lengkap
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify([{
        "id":        r["id"],
        "nama":      r["nama"],
        "unit_kerja":r["unit_kerja"],
        "jabatan":   r["jabatan"],
    } for r in rows])