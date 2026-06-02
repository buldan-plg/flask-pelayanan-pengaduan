from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

warga_route = Blueprint("pengaduan", __name__, url_prefix="/warga")


def warga_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("role") != "warga":
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated



# ── Riwayat pengaduan ──
@warga_route.route("/pengaduan", methods=["GET"])
@warga_required
def riwayat():
    return render_template("warga/pengaduan/list.html",
                           title="Riwayat Pengaduan")


# ── Form buat pengaduan ──
@warga_route.route("/pengaduan/buat", methods=["GET"])
@warga_required
def buat():
    return render_template("warga/pengaduan/buat.html",
                           title="Buat Pengaduan")


# ── Detail pengaduan ──
@warga_route.route("/pengaduan/<int:id>", methods=["GET"])
@warga_required
def detail(id):
    return render_template("warga/pengaduan/detail.html",
                           title=f"Detail Pengaduan", id=id)