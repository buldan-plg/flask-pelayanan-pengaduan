from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

pengaduan_petugas_route = Blueprint(
    "pengaduan_petugas", __name__, url_prefix="/petugas/pengaduan"
)


def petugas_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("role") != "petugas":
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ─── Daftar semua pengaduan milik petugas ───
@pengaduan_petugas_route.route("", methods=["GET"])
@petugas_required
def daftar():
    return render_template(
        "petugas/pengaduan/list.html",
        title="Pengaduan Saya"
    )


# ─── Filter cepat per status (URL langsung dari sidebar) ───
@pengaduan_petugas_route.route("/perlu-ditangani", methods=["GET"])
@petugas_required
def perlu_ditangani():
    return render_template(
        "petugas/pengaduan/list.html",
        title="Perlu Ditangani",
        default_status="VERIFIKASI"
    )


@pengaduan_petugas_route.route("/diproses", methods=["GET"])
@petugas_required
def diproses():
    return render_template(
        "petugas/pengaduan/list.html",
        title="Sedang Diproses",
        default_status="PROSES"
    )


@pengaduan_petugas_route.route("/selesai", methods=["GET"])
@petugas_required
def selesai():
    return render_template(
        "petugas/pengaduan/list.html",
        title="Pengaduan Selesai",
        default_status="SELESAI"
    )


# ─── Detail satu pengaduan ───
@pengaduan_petugas_route.route("/<int:id>", methods=["GET"])
@petugas_required
def detail(id):
    return render_template(
        "petugas/pengaduan/detail.html",
        title=f"Detail Pengaduan #{id}",
        id=id
    )