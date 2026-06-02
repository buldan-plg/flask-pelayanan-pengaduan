from flask import Blueprint, render_template

dashboard_petugas = Blueprint("petugas", __name__, url_prefix = "/petugas")

@dashboard_petugas.route("/dashboard", methods = ['GET'])
def dashboard():
    
    return render_template('petugas/dashboard.html', title = "Dashboard")