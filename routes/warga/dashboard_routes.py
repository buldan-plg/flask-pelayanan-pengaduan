from flask import Blueprint, render_template

dashboard_warga = Blueprint("warga", __name__, url_prefix = "/warga")

@dashboard_warga.route("/dashboard", methods = ['GET'])
def dashboard():
    
    return render_template("warga/dashboard.html", tittle = "Dashboard")
