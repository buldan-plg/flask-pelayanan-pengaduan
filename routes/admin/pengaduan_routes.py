from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

pengaduan_route = Blueprint("pengaduan_admin", __name__, url_prefix="/admin/pengaduan")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("role") not in ("admin", "petugas"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ─── Daftar semua pengaduan ───
@pengaduan_route.route("", methods=["GET"])
@admin_required
def daftar():
    return render_template("admin/pengaduan/list.html", title="Kelola Pengaduan")


# ─── Filter cepat per status (URL langsung dari sidebar) ───
@pengaduan_route.route("/masuk",     methods=["GET"])
@admin_required
def masuk():
    return render_template("admin/pengaduan/list.html",
                           title="Pengaduan Masuk", default_status="MASUK")

@pengaduan_route.route("/verifikasi", methods=["GET"])
@admin_required
def verifikasi():
    return render_template("admin/pengaduan/list.html",
                           title="Pengaduan Diverifikasi", default_status="VERIFIKASI")

@pengaduan_route.route("/diproses",  methods=["GET"])
@admin_required
def diproses():
    return render_template("admin/pengaduan/list.html",
                           title="Pengaduan Diproses", default_status="PROSES")

@pengaduan_route.route("/selesai",   methods=["GET"])
@admin_required
def selesai():
    return render_template("admin/pengaduan/list.html",
                           title="Pengaduan Selesai", default_status="SELESAI")

@pengaduan_route.route("/ditolak",   methods=["GET"])
@admin_required
def ditolak():
    return render_template("admin/pengaduan/list.html",
                           title="Pengaduan Ditolak", default_status="DITOLAK")


# ─── Detail satu pengaduan ───
@pengaduan_route.route("/<int:id>", methods=["GET"])
@admin_required
def detail(id):
    return render_template("admin/pengaduan/detail.html",
                           title=f"Detail Pengaduan #{id}", id=id)