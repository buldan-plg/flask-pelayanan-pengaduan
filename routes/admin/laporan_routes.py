from flask import Blueprint, render_template

laporan_route = Blueprint("laporan", __name__, url_prefix = "/admin")

@laporan_route.route("/laporan", methods = ['GET'])
def laporan():
    data = {
        "titile" : "Laporan"
    }
    return render_template("admin/laporan.html", **data)