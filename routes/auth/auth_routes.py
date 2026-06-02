from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, session
from werkzeug.security import check_password_hash
from configs.conn import get_db

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    form_errors = {}
    
    if request.method == "POST":
        # 
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        email,
                        password_hash,
                        nama_lengkap as nama,
                        no_telepon as no_hp,
                        peran as role
                    FROM pengguna
                    WHERE email = %s
                    """, (email,))
                user = cursor.fetchone()
        finally:
            conn.close()
        
        if not user:
            # 
            form_errors["email"] = "email tidak terdaftar"
        
        elif not check_password_hash(user["password_hash"], password):
            # 
            form_errors["password"] = "pasword salah."
        
        else :
            # 
            role = (user["role"] or "").lower()
            nama = user["nama"]
            kontak = user["no_hp"]
            # print(user)
            
            session["user"] = {
                "id" : user["id"],
                "nama" : nama,
                "kontak" : kontak,
                "role" : role
            }
            
            flash("berhasil login.", "succes")
            return redirect(url_for("index"))
    return render_template("auth/login.html", title = "Login", error = form_errors)

@auth.route("/logout", methods = ['GET'])
def logout():
    session.clear()
    flash("Berhasil logout.", "succes")
    return redirect(url_for("index"))