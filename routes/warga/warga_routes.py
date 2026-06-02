from flask import Blueprint, render_template


warga_dashboard = Blueprint("warga", __name__, url_prefix = "/warga")

@warga_dashboard.route("/")
def dashboard():
    
    data = {
        "title" : "Dashboard"
    }
    
    return render_template("warga/dashboard.html", **data)

@warga_dashboard.route("/pengaduan")
def pengaduan():
    
    data = {
        "title" : "Pengaduan"
    }
    
    return render_template("warga/pengaduan.html", **data)