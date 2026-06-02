from flask import Blueprint, request, render_template

petugas_routes = Blueprint("petugas_routes", __name__, url_prefix = "/admin")

@petugas_routes.route("/petugas", methods = ['GET'])
def get_petugas():
    
    data = {
        "title" : "Data petugas"
    }
    return render_template("admin/petugas/petugas.html", **data)

@petugas_routes.route("/petugas/create", methods= ['GET'])
def form_tambah():
    
    data = {
        "title" : "Tambah petugas"
    }
    return render_template("admin/petugas/tambah.html", **data)

@petugas_routes.route("/petugas/edit/<int:id>", methods=["GET"])
def form_edit(id):
    data = {
        "title": "Edit Petugas",
        "id": id
    }
    return render_template("admin/petugas/edit.html", **data)
