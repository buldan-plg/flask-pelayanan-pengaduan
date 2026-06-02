from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from configs.conn import get_db

users_api = Blueprint("api_users", __name__, url_prefix = "/api/users")

@users_api.route("", methods = ['GET'])
def get_users():
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(""" 
                    SELECT
                        id,
                        nama_lengkap as nama,
                        email,
                        no_telepon as kontak,
                        peran as role,
                        aktif as status
                    FROM pengguna
                    WHERE aktif = 1
                """)
            users = cursor.fetchall()
            
            for user in users:
                user["status"] = "aktif" if user["status"] == 1 else "Non aktif"
    finally:
        conn.close()
    
    return jsonify(users)

@users_api.route("/<int:id>")
def get_users_by_id(id):
    
    if request.method == "POST":
        return redirect(url_for("users.get_users"))
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                    SELECT
                        id,
                        nama_lengkap as nama,
                        email,
                        no_telepon as kontak,
                        peran as role,
                        aktif as status
                    FROM pengguna
                    WHERE id = %s
                """, (id,))
            user = cursor.fetchone()
            # user["status"] = "aktif" if user["satatus"] == 1 else "Non aktif"
    finally:
        conn.close()
        
    return jsonify(user)

@users_api.route("/insert", methods = ['POST'])
def user_create():
    
    user = request.get_json()
    password_hash = generate_password_hash(user["password"])
    # print(user)
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                    INSERT INTO pengguna
                        (nama_lengkap, email, no_telepon, password_hash, peran, aktif)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user["nama"], user["email"], user["kontak"], password_hash, user["role"], user["status"]))
            conn.commit()
    finally:
        conn.close()
    return jsonify({"message" : "Berhasil"})


@users_api.route("/<int:id>", methods=['PUT'])
def update_user(id):
    user = request.get_json()
    
    if not user:
        return jsonify({"message": "Data tidak ditemukan"}), 400
    
    nama = user.get("nama")
    email = user.get("email")
    kontak = user.get("kontak")
    password = user.get("password")
    role = user.get("role")

    if not nama or not role:
        return jsonify({"message": "Nama dan role wajib diisi"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if password:
                password_hash = generate_password_hash(password)
                cursor.execute("""
                    UPDATE pengguna
                    SET 
                        nama_lengkap = %s,
                        email = %s,
                        no_telepon = %s,
                        password_hash = %s,
                        peran = %s
                    WHERE id = %s
                """, (nama, email, kontak, password_hash, role, id))
            else:
                cursor.execute("""
                    UPDATE pengguna
                    SET 
                        nama_lengkap = %s,
                        email = %s,
                        no_telepon = %s,
                        peran = %s
                    WHERE id = %s
                """, (nama, email, kontak, role, id))

        conn.commit()
        return jsonify({"message": "Berhasil diperbarui"}), 200

    except Exception as e:
        conn.rollback()
        print("Error update_user:", e)
        return jsonify({"message": "Gagal memperbarui data"}), 500

@users_api.route("/<int:id>", methods=["DELETE"])
def delete_user(id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 
            cursor.execute("SELECT id FROM pengguna WHERE id = %s", (id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"message": "Pengguna tidak ditemukan"}), 404

            cursor.execute("UPDATE pengguna SET aktif = %s WHERE id = %s", (0, id))

        conn.commit()
        return jsonify({"message": "Pengguna berhasil dihapus"}), 200

    except Exception as e:
        conn.rollback()
        print("Error delete_user:", e)
        return jsonify({"message": "Gagal menghapus pengguna"}), 500