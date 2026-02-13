from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hotel.db"
HOST, PORT = "0.0.0.0", 8000


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_eur INTEGER NOT NULL,
            image_url TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            room_name TEXT NOT NULL,
            checkin_date TEXT NOT NULL,
            checkout_date TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    if db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO rooms(name, description, price_eur, image_url) VALUES (?, ?, ?, ?)",
            [
                (
                    "Dhomë Standarte",
                    "Wi-Fi falas, minibar dhe ambient i rehatshëm.",
                    75,
                    "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
                ),
                (
                    "Suitë Deluxe",
                    "Suitë moderne me sallon privat dhe pamje panoramike.",
                    130,
                    "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                ),
                (
                    "Dhomë Familjare",
                    "Hapësirë e madhe dhe komoditet maksimal për familje.",
                    105,
                    "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                ),
            ],
        )
    db.commit()
    db.close()


def render_page(title: str, active: str, content: str) -> str:
    nav = f"""
    <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark sticky-top\">
      <div class=\"container\">
        <a class=\"navbar-brand fw-bold\" href=\"/\">Hotel Valbona Crown</a>
        <button class=\"navbar-toggler\" type=\"button\" data-bs-toggle=\"collapse\" data-bs-target=\"#mainNav\"><span class=\"navbar-toggler-icon\"></span></button>
        <div class=\"collapse navbar-collapse\" id=\"mainNav\">
          <ul class=\"navbar-nav ms-auto\">
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'home' else ''}\" href=\"/\">Home</a></li>
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'about' else ''}\" href=\"/about\">About us</a></li>
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'contact' else ''}\" href=\"/contact\">Contact us</a></li>
          </ul>
        </div>
      </div>
    </nav>
    """
    return f"""<!doctype html>
<html lang=\"sq\"><head>
<meta charset=\"UTF-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{title}</title>
<link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\" />
<link rel=\"stylesheet\" href=\"/static/styles.css\" />
</head><body>
{nav}
{content}
<footer class=\"bg-dark text-white text-center py-3 mt-5\"><div class=\"container\"><small>© 2026 Hotel Valbona Crown • Të gjitha të drejtat e rezervuara.</small></div></footer>
<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
<script src=\"/static/script.js\"></script>
</body></html>"""


def home_html() -> str:
    db = sqlite3.connect(DB_PATH)
    rooms = db.execute("SELECT name, description, price_eur, image_url FROM rooms ORDER BY id").fetchall()
    db.close()
    cards = "".join(
        f"""<div class='col-md-4'><div class='card h-100 shadow-sm'>
        <img src='{html.escape(r[3])}' class='card-img-top' alt='{html.escape(r[0])}' />
        <div class='card-body'><h2 class='h5'>{html.escape(r[0])}</h2><p>{html.escape(r[1])}</p><p class='fw-bold text-primary'>Nga {r[2]}€ / natë</p></div>
        </div></div>"""
        for r in rooms
    )
    gallery = [
        "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1455587734955-081b22074882?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
    ]
    gallery_html = "".join(
        f"<div class='col-6 col-md-4'><img class='img-fluid rounded shadow-sm' src='{g}' alt='Pamje hoteli' /></div>" for g in gallery
    )
    body = f"""
<header class='hero text-white text-center d-flex align-items-center'><div class='container py-5'>
<h1 class='display-5 fw-bold'>Mirë se vini në Hotel Valbona Crown</h1>
<p class='lead'>Komoditet, elegancë dhe pamje fantastike për pushimet tuaja perfekte.</p>
<a href='/contact' class='btn btn-warning btn-lg mt-2'>Rezervo tani</a></div></header>
<main><section class='container py-5'><div class='row g-4'>{cards}</div></section>
<section class='container pb-5'><h2 class='mb-3'>Galeri Hoteli</h2><div class='row g-3'>{gallery_html}</div></section></main>
"""
    return render_page("Hotel Valbona Crown | Home", "home", body)


def about_html() -> str:
    body = """
<main class='container py-5'>
<section class='mb-4'><h1 class='mb-3'>Rreth Nesh</h1>
<p>Hotel Valbona Crown është krijuar për të ofruar një eksperiencë premium për çdo vizitor. Ne kombinojmë mikpritjen shqiptare me standarde moderne shërbimi.</p>
</section>
<section class='row g-4'>
<div class='col-md-6'><div class='p-4 bg-light rounded h-100 shadow-sm'><h2 class='h4'>Misioni ynë</h2><p>Të krijojmë kujtime të bukura për çdo mysafir përmes rehatisë, sigurisë dhe cilësisë.</p></div></div>
<div class='col-md-6'><div class='p-4 bg-light rounded h-100 shadow-sm'><h2 class='h4'>Shërbimet</h2><ul class='mb-0'><li>Recepsion 24/7</li><li>Restaurant & Bar</li><li>Spa dhe pishinë</li><li>Transport aeroporti</li></ul></div></div>
</section>
<div class='mt-4'><a href='/contact' class='btn btn-warning'>Na kontakto për rezervim</a></div></main>
"""
    return render_page("Hotel Valbona Crown | About us", "about", body)


def contact_html(flash: str = "", category: str = "success") -> str:
    db = sqlite3.connect(DB_PATH)
    rooms = db.execute("SELECT name FROM rooms ORDER BY id").fetchall()
    db.close()
    room_options = "".join(f"<option>{html.escape(r[0])}</option>" for r in rooms)
    flash_html = f"<div class='alert alert-{category}'>{html.escape(flash)}</div>" if flash else ""
    body = f"""
<main class='container py-5'><section class='row justify-content-center'><div class='col-lg-8'>
<h1 class='mb-3'>Kontakto / Rezervo</h1><p class='text-muted'>Plotëso formën më poshtë dhe ne do t'ju kontaktojmë sa më shpejt.</p>
{flash_html}
<form id='contactForm' class='needs-validation' novalidate method='post' action='/contact'>
<div class='row g-3'>
<div class='col-md-6'><label class='form-label' for='name'>Emri i plotë</label><input id='name' name='name' class='form-control' required minlength='3' /><div class='invalid-feedback'>Ju lutem shkruani emrin (min 3 karaktere).</div></div>
<div class='col-md-6'><label class='form-label' for='email'>Email</label><input id='email' name='email' type='email' class='form-control' required /><div class='invalid-feedback'>Vendosni një email valid.</div></div>
<div class='col-md-6'><label class='form-label' for='phone'>Telefoni</label><input id='phone' name='phone' class='form-control' pattern='[0-9+ ]{{8,15}}' required /><div class='invalid-feedback'>Vendosni një numër telefoni valid.</div></div>
<div class='col-md-6'><label class='form-label' for='room'>Lloji i dhomës</label><select id='room' name='room' class='form-select' required><option value=''>Zgjidh dhomën</option>{room_options}</select><div class='invalid-feedback'>Ju lutem zgjidhni llojin e dhomës.</div></div>
<div class='col-md-6'><label class='form-label' for='checkin'>Check-in</label><input id='checkin' name='checkin' type='date' class='form-control' required /></div>
<div class='col-md-6'><label class='form-label' for='checkout'>Check-out</label><input id='checkout' name='checkout' type='date' class='form-control' required /></div>
<div class='col-12'><label class='form-label' for='message'>Mesazhi</label><textarea id='message' name='message' class='form-control' rows='4' required minlength='10'></textarea></div>
<div class='col-12'><button type='submit' class='btn btn-warning'>Submit</button></div>
</div></form>
<p class='mt-3'><a href='/admin/reservations'>Shiko rezervimet e ruajtura</a></p></div></section></main>
"""
    return render_page("Hotel Valbona Crown | Contact us", "contact", body)


def reservations_html() -> str:
    db = sqlite3.connect(DB_PATH)
    reservations = db.execute(
        "SELECT full_name, email, room_name, checkin_date, checkout_date, created_at FROM reservations ORDER BY id DESC"
    ).fetchall()
    db.close()
    if reservations:
        rows = "".join(
            f"<tr><td>{html.escape(r[0])}</td><td>{html.escape(r[1])}</td><td>{html.escape(r[2])}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td></tr>"
            for r in reservations
        )
        table = f"<div class='table-responsive'><table class='table table-striped'><thead><tr><th>Emri</th><th>Email</th><th>Dhomë</th><th>Check-in</th><th>Check-out</th><th>Krijuar</th></tr></thead><tbody>{rows}</tbody></table></div>"
    else:
        table = "<p>Ende nuk ka rezervime të ruajtura.</p>"
    return render_page("Hotel Valbona Crown | Reservations", "contact", f"<main class='container py-5'><h1 class='mb-4'>Rezervimet e ruajtura</h1>{table}</main>")


class HotelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            return self.respond_html(home_html())
        if path == "/about":
            return self.respond_html(about_html())
        if path == "/contact":
            return self.respond_html(contact_html())
        if path == "/admin/reservations":
            return self.respond_html(reservations_html())
        if path.startswith("/static/"):
            return self.serve_static(path)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/contact":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        data = {k: v[0] for k, v in parse_qs(body).items()}

        required = ["name", "email", "phone", "room", "checkin", "checkout", "message"]
        if any(not data.get(field, "").strip() for field in required):
            return self.respond_html(contact_html("Të gjitha fushat janë të detyrueshme.", "danger"), HTTPStatus.BAD_REQUEST)

        try:
            checkin = datetime.strptime(data["checkin"], "%Y-%m-%d")
            checkout = datetime.strptime(data["checkout"], "%Y-%m-%d")
            if checkout <= checkin:
                return self.respond_html(contact_html("Check-out duhet të jetë pas check-in.", "danger"), HTTPStatus.BAD_REQUEST)
        except ValueError:
            return self.respond_html(contact_html("Datat nuk janë valide.", "danger"), HTTPStatus.BAD_REQUEST)

        db = sqlite3.connect(DB_PATH)
        db.execute(
            """
            INSERT INTO reservations(full_name, email, phone, room_name, checkin_date, checkout_date, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"].strip(),
                data["email"].strip(),
                data["phone"].strip(),
                data["room"].strip(),
                data["checkin"],
                data["checkout"],
                data["message"].strip(),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        db.commit()
        db.close()

        self.respond_html(contact_html(f"Faleminderit {data['name']}! Kërkesa juaj u ruajt me sukses në database.", "success"))

    def serve_static(self, path: str) -> None:
        file_path = BASE_DIR / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "text/css" if file_path.suffix == ".css" else "application/javascript"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), HotelHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    server.serve_forever()
