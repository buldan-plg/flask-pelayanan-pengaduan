from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from configs.conn import get_db

api_petugas = Blueprint("api_petugas", __name__, url_prefix = "/api")

@api_petugas.route("/petugas", methods= ['GET'])
def get_all_petugas():
    
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                    SELECT
                        pt.id as id_petugas,
                        pt.unit_kerja,
                        pt.jabatan,
                        pt.aktif as status,
                        pg.id as id_user,
                        pg.nama_lengkap as nama,
                        pg.no_telepon as kontak
                    FROM petugas as pt
                    JOIN pengguna as pg ON pt.pengguna_id = pg.id
                """)
            rows = cursor.fetchall()
            
            for row in rows:
                row["status"] = "Aktif" if row["status"] == 1 else "Non aktif"
    finally:
        conn.close()
    return jsonify(rows)

@api_petugas.route("/petugas/aktif", methods=["GET"])
def get_all_petugas_aktif():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    pt.id          AS id_petugas,
                    pt.unit_kerja,
                    pt.jabatan,
                    pt.aktif       AS status,
                    pg.id          AS id_user,
                    pg.nama_lengkap AS nama,
                    pg.no_telepon  AS kontak
                FROM petugas AS pt
                JOIN pengguna AS pg ON pt.pengguna_id = pg.id
                WHERE pt.aktif = 1
            """)
            rows = cursor.fetchall()
    finally:
        conn.close()

    # konversi status di luar blok try, setelah conn sudah ditutup
    for row in rows:
        row["status"] = "Aktif" if row["status"] == 1 else "Non Aktif"

    return jsonify(rows)


@api_petugas.route("/petugas/<int:id>", methods=['GET'])
def get_petugas_by_id(id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    pt.id          AS id_petugas,
                    pt.unit_kerja,
                    pt.jabatan,
                    pt.aktif       AS status,
                    pg.id          AS id_user,
                    pg.nama_lengkap AS nama,
                    pg.email,
                    pg.no_telepon  AS kontak
                FROM petugas AS pt
                JOIN pengguna AS pg ON pt.pengguna_id = pg.id
                WHERE pt.id = %s
            """, (id,))
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({"message": "Petugas tidak ditemukan"}), 404

    return jsonify(row)


@api_petugas.route("/petugas/<int:id>", methods=['PUT'])
def update_petugas(id):
    data = request.get_json()

    if not data:
        return jsonify({"message": "Data tidak ditemukan"}), 400

    nama       = data.get("nama")
    email      = data.get("email", "")
    kontak     = data.get("kontak", "")
    password   = data.get("password")
    unit_kerja = data.get("unit_kerja")
    jabatan    = data.get("jabatan")

    if not nama:
        return jsonify({"message": "Nama wajib diisi"}), 400
    if not unit_kerja:
        return jsonify({"message": "Unit kerja wajib diisi"}), 400
    if not jabatan:
        return jsonify({"message": "Jabatan wajib diisi"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # Ambil pengguna_id dari tabel petugas
            cursor.execute("SELECT pengguna_id FROM petugas WHERE id = %s", (id,))
            petugas = cursor.fetchone()

            if not petugas:
                return jsonify({"message": "Petugas tidak ditemukan"}), 404

            pengguna_id = petugas["pengguna_id"]

            # Update tabel pengguna
            if password:
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(password)
                cursor.execute("""
                    UPDATE pengguna
                    SET nama_lengkap  = %s,
                        email         = %s,
                        no_telepon    = %s,
                        password_hash = %s
                    WHERE id = %s
                """, (nama, email, kontak, password_hash, pengguna_id))
            else:
                cursor.execute("""
                    UPDATE pengguna
                    SET nama_lengkap = %s,
                        email        = %s,
                        no_telepon   = %s
                    WHERE id = %s
                """, (nama, email, kontak, pengguna_id))

            # Update tabel petugas
            cursor.execute("""
                UPDATE petugas
                SET unit_kerja = %s,
                    jabatan    = %s
                WHERE id = %s
            """, (unit_kerja, jabatan, id))

        conn.commit()
        return jsonify({"message": "Petugas berhasil diperbarui"}), 200

    except Exception as e:
        conn.rollback()
        print("Error update_petugas:", e)
        return jsonify({"message": "Gagal memperbarui petugas"}), 500

    finally:
        conn.close()


@api_petugas.route("/petugas/insert", methods=['POST'])
def create_petugas():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Data tidak ditemukan"}), 400

    nama       = data.get("nama")
    email      = data.get("email", "")
    kontak     = data.get("kontak", "")
    password   = data.get("password")
    unit_kerja = data.get("unit_kerja")
    jabatan    = data.get("jabatan")

    # Validasi field wajib
    if not nama:
        return jsonify({"message": "Nama wajib diisi"}), 400
    if not password:
        return jsonify({"message": "Password wajib diisi"}), 400
    if not unit_kerja:
        return jsonify({"message": "Unit kerja wajib diisi"}), 400
    if not jabatan:
        return jsonify({"message": "Jabatan wajib diisi"}), 400

    password_hash = generate_password_hash(password)

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. Insert ke tabel pengguna dengan role = 'petugas'
            cursor.execute("""
                INSERT INTO pengguna
                    (nama_lengkap, email, no_telepon, password_hash, peran, aktif)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nama, email, kontak, password_hash, "petugas", 1))

            # 2. Ambil id pengguna yang baru saja diinsert
            pengguna_id = cursor.lastrowid

            # 3. Insert ke tabel petugas
            cursor.execute("""
                INSERT INTO petugas
                    (pengguna_id, unit_kerja, jabatan, aktif)
                VALUES (%s, %s, %s, %s)
            """, (pengguna_id, unit_kerja, jabatan, 1))

        conn.commit()
        return jsonify({"message": "Petugas berhasil ditambahkan"}), 201

    except Exception as e:
        conn.rollback()
        print("Error create_petugas:", e)
        return jsonify({"message": "Gagal menambahkan petugas"}), 500

    finally:
        conn.close()


@api_petugas.route("/petugas/<int:id>", methods=["DELETE"])
def delete_petugas(id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM petugas WHERE id = %s", (id,))
            petugas = cursor.fetchone()
 
            if not petugas:
                return jsonify({"message": "Petugas tidak ditemukan"}), 404
 
            # Soft delete: set aktif = 0 di tabel petugas
            cursor.execute("UPDATE petugas SET aktif = 0 WHERE id = %s", (id,))
 
        conn.commit()
        return jsonify({"message": "Petugas berhasil dihapus"}), 200
 
    except Exception as e:
        conn.rollback()
        print("Error delete_petugas:", e)
        return jsonify({"message": "Gagal menghapus petugas"}), 500
 
    finally:
        conn.close()
