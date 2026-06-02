from flask import Blueprint, render_template, redirect, url_for
from configs.conn import get_db

users_route = Blueprint("users", __name__, url_prefix = "/admin/users")

@users_route.route("", methods = ["GET"])
def get_users():
    
    data = {
        "title" : "Kelola Users"
    }
    
    return render_template("admin/users/users.html", **data)

@users_route.route("/create", methods = ["GET"])
def form_create():
    
    data = {
        "title" : "Tambah User"
    }
    return render_template("/admin/users/tambah.html", **data)

@users_route.route("/edit/<int:id>", methods = ['GET'])
def form_edit(id):
    
    data = {
        "title" : "Edit user",
        "id": id
    }
    # render the correct template path (templates/admin/users/edit.html)
    return render_template("admin/users/edit.html", **data)