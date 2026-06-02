from flask import Flask, session, g, redirect, url_for, request
from datetime import datetime
from configs.conn import get_db
from configs.config import Config
import pymysql

# routes auth
from routes.auth.auth_routes import auth

# routes admin
from routes.admin.dashboard_admin import admin_dashboard
from routes.admin.users_routes import users_route
from routes.admin.petugas_routes import petugas_routes
from routes.admin.laporan_routes import laporan_route
from routes.admin.pengaduan_routes import pengaduan_route

# routes petugas
from routes.petugas.dashboard_routes import dashboard_petugas
from routes.petugas.pengaduan_routes import pengaduan_petugas_route

# routes warga
from routes.warga.dashboard_routes import dashboard_warga
from routes.warga.pengaduan_routes import warga_route

# Rest api
from API.admin_dashboard_api import dashboard_api
from API.users_api import users_api
from API.petugas_api import api_petugas
from API.laporan_api import laporan_api
from API.pengaduan_api import pengaduan_api
from API.petugas_dashboard_api import petugas_dashboard_api
from API.warga_dashboard_api import warga_dashboard_api
from API.warga_pengaduan_api import warga_pengaduan_api
from API.petugas_pengaduan_api import petugas_pengaduan_api

# routes home
from routes.public.public_routes import home_routes

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if not value:
        return ""
    
    if isinstance(value, str):
        value = datetime.strptime(value, "%Y-%m-%d")
    
    return value.strftime("%m/%d/%Y")

@app.route("/", methods = ["GET"])
def index():
    
    if "user" not in session:
        
        # return redirect(url_for("auth.login"))
        return redirect(url_for("home.home"))
    
    role = session["user"].get("role", "").lower()
    
    if role == "admin":
        # return redirect(url_for("admin_dashboard"))
        return redirect(url_for("admin.dashboard"))
    
    elif role == "petugas":
        # 
        return redirect(url_for("petugas.dashboard"))
    
    elif role == "warga":
        # 
        return redirect(url_for("warga.dashboard"))
    
    else:
        # 
        session.clear()
        return redirect(url_for("auth.login"))

# register routes auth
app.register_blueprint(auth)


# register routes admin
app.register_blueprint(admin_dashboard)
app.register_blueprint(users_route)
app.register_blueprint(petugas_routes)
app.register_blueprint(laporan_route)
app.register_blueprint(pengaduan_route)

# registrasi routes petugas
app.register_blueprint(dashboard_petugas)
app.register_blueprint(pengaduan_petugas_route)

# registrasi routes warga
app.register_blueprint(dashboard_warga)
app.register_blueprint(warga_route)

# rest api
app.register_blueprint(dashboard_api)
app.register_blueprint(users_api)
app.register_blueprint(api_petugas)
app.register_blueprint(laporan_api)
app.register_blueprint(pengaduan_api)
app.register_blueprint(petugas_dashboard_api)
app.register_blueprint(warga_dashboard_api)
app.register_blueprint(warga_pengaduan_api)
app.register_blueprint(petugas_pengaduan_api)


# 
app.register_blueprint(home_routes)

if __name__ == "__main__":
    app.run(debug = True, port = 8000)