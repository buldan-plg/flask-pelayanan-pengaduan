from flask import Blueprint, render_template, session, jsonify

admin_dashboard = Blueprint("admin",__name__, url_prefix = "/admin")

@admin_dashboard.route("/dashboard", methods=["GET"])
def dashboard():
    
    return render_template("admin/dashboard.html", title = "dashboard")

@admin_dashboard.route("/session")
def sesi():
    # id = session["user"]
    
    return jsonify(session.get("nama"))