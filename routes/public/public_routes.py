from flask import Blueprint, render_template


home_routes = Blueprint("home", __name__)

@home_routes.route("/palsabolas")
def home():
    # Data desa — bisa dipindahkan ke database/JSON di masa depan
    DESA_DATA = {
        "nama": "Desa Pal XI (Palsabolas)",
        "kabupaten": "Tapanuli Selatan",
        "kecamatan": "Angkola Timur",
        "provinsi": "Sumatera Utara",
        "kode_kemendagri": "12.03.03.2097",
        "landmark": "UPPKB (Jembatan Timbang) Pal XI",
        "prestasi": "Juara II Lomba Desa Tingkat Kabupaten Tapanuli Selatan",
        "koordinat": {"lat": 1.4876, "lng": 99.3523},
        "potensi": [
            {
                "icon": "bi-truck",
                "judul": "Hub Logistik & Transportasi",
                "deskripsi": (
                    "Terletak di persimpangan vital Jalinsum — jalur Sipirok menuju Medan "
                    "dan jalur lintas tengah via Gunung Tua. Menjadi tempat transit utama "
                    "bagi armada angkutan barang dan penumpang antarkota."
                ),
                "warna": "gold",
            },
            {
                "icon": "bi-shop",
                "judul": "Ekonomi Lokal & UMKM",
                "deskripsi": (
                    "Pusat pertumbuhan warung makan khas daerah, rest area informal, "
                    "bengkel penunjang, serta sektor perdagangan yang melayani para "
                    "pelancong antarkota dan warga sekitar."
                ),
                "warna": "green",
            },
            {
                "icon": "bi-award",
                "judul": "Tata Kelola Pemerintahan Mandiri",
                "deskripsi": (
                    "Didukung oleh aparatur desa yang aktif dalam administrasi pembangunan "
                    "dan pemberdayaan masyarakat, terbukti dengan raihan prestasi di tingkat "
                    "Kabupaten Tapanuli Selatan."
                ),
                "warna": "rust",
            },
            {
                "icon": "bi-geo-alt",
                "judul": "Simpang Tiga Strategis",
                "deskripsi": (
                    "Berada di titik temu Segitiga Jalur Lintas Sumatera, desa ini menjadi "
                    "denyut nadi transportasi utama yang menghubungkan berbagai wilayah di "
                    "Tapanuli Bagian Selatan (Tabagsel)."
                ),
                "warna": "teal",
            },
        ],
    }
    
    return render_template("public/dashboard.html", desa=DESA_DATA)
        # return render_template("public/d ")