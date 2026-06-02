from flask import Blueprint, jsonify, request, session, current_app
from configs.conn import get_db
from werkzeug.utils import secure_filename
import os, uuid

warga_pengaduan_api = Blueprint(
    "api_warga_pengaduan", __name__, url_prefix="/api/warga/pengaduan"
)

ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp", "pdf", "doc", "docx", "xls", "xlsx"}
MAX_SIZE    = 5 * 1024 * 1024  # 5 MB


def get_uid():
    return session.get("user", {}).get("id")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ─────────────────────────────────────────────
# 1. Daftar pengaduan milik warga (dengan filter + paginasi)
# ─────────────────────────────────────────────
@warga_pengaduan_api.route("", methods=["GET"])
def get_pengaduan():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    status   = request.args.get("status", "")
    cari     = request.args.get("cari",   "")
    page     = max(1, int(request.args.get("page",     1)))
    per_page = max(1, int(request.args.get("per_page", 8)))
    offset   = (page - 1) * per_page

    clauses = ["p.pengguna_id = %s"]
    params  = [uid]

    if status:
        clauses.append("s.kode = %s");      params.append(status)
    if cari:
        clauses.append("p.judul LIKE %s");  params.append(f"%{cari}%")

    where = "WHERE " + " AND ".join(clauses)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) AS n
                FROM pengaduan p
                JOIN status s ON s.id = p.status_id
                {where}
            """, params)
            total = cur.fetchone()["n"]

            cur.execute(f"""
                SELECT
                    p.id, p.judul, p.lokasi, p.prioritas, p.dibuat_pada,
                    k.nama  AS kategori,
                    s.nama  AS status,
                    s.kode  AS status_kode,
                    s.warna AS warna_status,
                    (SELECT COUNT(*) FROM lampiran l WHERE l.pengaduan_id = p.id)  AS jumlah_lampiran,
                    (SELECT COUNT(*) FROM komentar km
                        WHERE km.pengaduan_id = p.id AND km.adalah_internal = 0)   AS jumlah_komentar
                FROM pengaduan p
                JOIN kategori k ON k.id = p.kategori_id
                JOIN status   s ON s.id = p.status_id
                {where}
                ORDER BY p.dibuat_pada DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify({
        "total": total,
        "data": [{
            "id":             r["id"],
            "judul":          r["judul"],
            "lokasi":         r["lokasi"],
            "prioritas":      r["prioritas"],
            "dibuat_pada":    r["dibuat_pada"].isoformat() if r["dibuat_pada"] else None,
            "kategori":       r["kategori"],
            "status":         r["status"],
            "status_kode":    r["status_kode"],
            "warna_status":   r["warna_status"],
            "jumlah_lampiran":r["jumlah_lampiran"],
            "jumlah_komentar":r["jumlah_komentar"],
        } for r in rows]
    })


# ─────────────────────────────────────────────
# 2. Counter per status milik warga
# ─────────────────────────────────────────────
@warga_pengaduan_api.route("/counter", methods=["GET"])
def counter():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.kode, COUNT(p.id) AS n
                FROM status s
                LEFT JOIN pengaduan p ON p.status_id = s.id AND p.pengguna_id = %s
                GROUP BY s.id, s.kode
            """, (uid,))
            rows = cur.fetchall()

            cur.execute(
                "SELECT COUNT(*) AS n FROM pengaduan WHERE pengguna_id = %s", (uid,)
            )
            semua = cur.fetchone()["n"]
    finally:
        conn.close()

    result = {"semua": semua}
    for r in rows:
        result[r["kode"]] = r["n"] or 0
    return jsonify(result)


# ─────────────────────────────────────────────
# 3. Detail satu pengaduan milik warga
# ─────────────────────────────────────────────
@warga_pengaduan_api.route("/<int:id>", methods=["GET"])
def get_detail(id):
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.id, p.judul, p.deskripsi, p.lokasi,
                    p.prioritas, p.dibuat_pada, p.diselesaikan_pada,
                    k.nama  AS kategori,
                    s.nama  AS status,
                    s.kode  AS status_kode,
                    s.warna AS warna_status,
                    pt.unit_kerja AS unit_petugas
                FROM pengaduan p
                JOIN kategori k ON k.id = p.kategori_id
                JOIN status   s ON s.id = p.status_id
                LEFT JOIN petugas pt ON pt.id = p.petugas_id
                WHERE p.id = %s AND p.pengguna_id = %s
            """, (id, uid))
            p = cur.fetchone()

            if not p:
                return jsonify({"message": "Pengaduan tidak ditemukan"}), 404

            cur.execute("""
                SELECT id, nama_file, tipe_file, url_file
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
        "prioritas":        p["prioritas"],
        "dibuat_pada":      p["dibuat_pada"].isoformat()       if p["dibuat_pada"]       else None,
        "diselesaikan_pada":p["diselesaikan_pada"].isoformat() if p["diselesaikan_pada"] else None,
        "kategori":         p["kategori"],
        "status":           p["status"],
        "status_kode":      p["status_kode"],
        "warna_status":     p["warna_status"],
        "unit_petugas":     p["unit_petugas"],
        "lampiran": [{
            "id":        l["id"],
            "nama_file": l["nama_file"],
            "tipe_file": l["tipe_file"],
            "url_file":  l["url_file"],
        } for l in lampiran],
    })


# ─────────────────────────────────────────────
# 4. Buat pengaduan baru
# ─────────────────────────────────────────────
@warga_pengaduan_api.route("", methods=["POST"])
def buat_pengaduan():
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    body = request.get_json()
    judul       = (body.get("judul") or "").strip()
    kategori_id = body.get("kategori_id")
    lokasi      = (body.get("lokasi") or "").strip()
    deskripsi   = (body.get("deskripsi") or "").strip()
    prioritas   = int(body.get("prioritas", 1))

    if not judul or not kategori_id or not lokasi or not deskripsi:
        return jsonify({"message": "Semua field wajib diisi"}), 400

    if prioritas not in (1, 2, 3):
        prioritas = 1

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Ambil status_id untuk 'MASUK'
            cur.execute("SELECT id FROM status WHERE kode = 'MASUK'")
            status_row = cur.fetchone()
            if not status_row:
                return jsonify({"message": "Status awal tidak ditemukan"}), 500
            status_id = status_row["id"]

            cur.execute("""
                INSERT INTO pengaduan
                    (pengguna_id, kategori_id, judul, deskripsi,
                     lokasi, prioritas, status_id, dibuat_pada, diperbarui_pada)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (uid, kategori_id, judul, deskripsi, lokasi, prioritas, status_id))

            new_id = cur.lastrowid
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("buat_pengaduan error:", e)
        return jsonify({"message": "Gagal menyimpan pengaduan"}), 500
    finally:
        conn.close()

    return jsonify({"message": "Pengaduan berhasil dikirim", "id": new_id}), 201


# ─────────────────────────────────────────────
# 5. Upload lampiran
# ─────────────────────────────────────────────
@warga_pengaduan_api.route("/<int:id>/lampiran", methods=["POST"])
def upload_lampiran(id):
    uid = get_uid()
    if not uid:
        return jsonify({"message": "Unauthorized"}), 401

    if "files" not in request.files:
        return jsonify({"message": "Tidak ada file"}), 400

    files = request.files.getlist("files")
    if len(files) > 5:
        return jsonify({"message": "Maksimal 5 file"}), 400

    # Folder simpan — sesuaikan dengan konfigurasi aplikasi Anda
    upload_folder = os.path.join(
        current_app.root_path, "static", "uploads", "lampiran", str(id)
    )
    os.makedirs(upload_folder, exist_ok=True)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Pastikan pengaduan milik warga ini
            cur.execute(
                "SELECT id FROM pengaduan WHERE id = %s AND pengguna_id = %s",
                (id, uid)
            )
            if not cur.fetchone():
                return jsonify({"message": "Pengaduan tidak ditemukan"}), 404

            saved = []
            for f in files:
                if not f.filename or not allowed_file(f.filename):
                    continue
                if f.content_length and f.content_length > MAX_SIZE:
                    continue

                ext       = f.filename.rsplit(".", 1)[1].lower()
                safe_name = secure_filename(f.filename)
                uniq_name = f"{uuid.uuid4().hex}_{safe_name}"
                save_path = os.path.join(upload_folder, uniq_name)
                f.save(save_path)

                url_file = f"/static/uploads/lampiran/{id}/{uniq_name}"

                cur.execute("""
                    INSERT INTO lampiran
                        (pengaduan_id, nama_file, tipe_file, url_file,
                         ukuran_byte, diunggah_pada)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (id, safe_name, f.mimetype, url_file,
                      os.path.getsize(save_path)))
                saved.append(safe_name)

        conn.commit()
    except Exception as e:
        conn.rollback()
        print("upload_lampiran error:", e)
        return jsonify({"message": "Gagal mengunggah lampiran"}), 500
    finally:
        conn.close()

    return jsonify({
        "message": f"{len(saved)} file berhasil diunggah",
        "files":   saved
    }), 201