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
SELF_FILE = BASE_DIR / "app.py"

DOWNLOADABLE_FILES = {
    "app.py": BASE_DIR / "app.py",
    "index.html": BASE_DIR / "index.html",
    "about.html": BASE_DIR / "about.html",
    "contact.html": BASE_DIR / "contact.html",
    "styles.css": BASE_DIR / "styles.css",
    "script.js": BASE_DIR / "script.js",
    "static/styles.css": BASE_DIR / "static" / "styles.css",
    "static/script.js": BASE_DIR / "static" / "script.js",
}

INLINE_CSS = """
body { font-family: Arial, Helvetica, sans-serif; }
.hero {
  min-height: 56vh;
  background: linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,.45)),
  url('https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1800&q=80') center/cover no-repeat;
}
.card-img-top { height: 220px; object-fit: cover; }
.room-link { color: inherit; text-decoration: none; display: inline-block; }
.room-link:hover { text-decoration: underline; }
@media (max-width: 576px) { .hero { min-height: 48vh; } }
"""

INLINE_JS = """
const form = document.getElementById('contactForm');
if (form) {
  form.addEventListener('submit', (event) => {
    if (!form.checkValidity()) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.classList.add('was-validated');
  });
}
"""


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                long_description TEXT NOT NULL,
                price_eur INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                beds INTEGER NOT NULL,
                guests INTEGER NOT NULL
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
                room_id INTEGER NOT NULL,
                checkin_date TEXT NOT NULL,
                checkout_date TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(room_id) REFERENCES rooms(id)
            )
            """
        )
        if db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
            db.executemany(
                """
                INSERT INTO rooms(name, description, long_description, price_eur, image_url, beds, guests)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Dhomë Standarte",
                        "Wi-Fi falas, minibar dhe ambient i rehatshëm.",
                        "Dhomë moderne me ndriçim natyral, banjo private, tavolinë pune dhe pamje nga kopshti.",
                        75,
                        "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
                        1,
                        2,
                    ),
                    (
                        "Suitë Deluxe",
                        "Suitë moderne me sallon privat dhe pamje panoramike.",
                        "Suitë premium me sallon të ndarë, krevat king-size, balkon privat dhe shërbim room-service.",
                        130,
                        "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                        1,
                        3,
                    ),
                    (
                        "Dhomë Familjare",
                        "Hapësirë e madhe dhe komoditet maksimal për familje.",
                        "Dhomë e bollshme me 2 krevate dhe hapësirë të madhe për familje.",
                        105,
                        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                        2,
                        4,
                    ),
                ],
            )


def render_page(title: str, active: str, content: str) -> str:
    nav = f"""
    <nav class='navbar navbar-expand-lg navbar-dark bg-dark sticky-top'>
      <div class='container'>
        <a class='navbar-brand fw-bold' href='/'>Hotel Valbona Crown</a>
        <button class='navbar-toggler' type='button' data-bs-toggle='collapse' data-bs-target='#mainNav'>
          <span class='navbar-toggler-icon'></span>
        </button>
        <div class='collapse navbar-collapse' id='mainNav'>
          <ul class='navbar-nav ms-auto'>
            <li class='nav-item'><a class='nav-link {'active' if active == 'home' else ''}' href='/'>Home</a></li>
            <li class='nav-item'><a class='nav-link {'active' if active == 'rooms' else ''}' href='/rooms'>Dhomat</a></li>
            <li class='nav-item'><a class='nav-link {'active' if active == 'about' else ''}' href='/about'>About us</a></li>
            <li class='nav-item'><a class='nav-link {'active' if active == 'contact' else ''}' href='/contact'>Contact us</a></li>
          </ul>
        </div>
      </div>
    </nav>
    """
    return f"""<!doctype html>
<html lang='sq'><head>
<meta charset='UTF-8' />
<meta name='viewport' content='width=device-width, initial-scale=1' />
<title>{title}</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet' />
<style>{INLINE_CSS}</style>
</head><body>
{nav}
{content}
<footer class='bg-dark text-white text-center py-3 mt-5'><div class='container'><small>© 2026 Hotel Valbona Crown • Të gjitha të drejtat e rezervuara.</small></div></footer>
<script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'></script>
<script>{INLINE_JS}</script>
</body></html>"""


def room_card(room: sqlite3.Row) -> str:
    rid = int(room["id"])
    return f"""
    <div class='col-md-4'>
      <div class='card h-100 shadow-sm'>
        <a href='/rooms/{rid}' class='room-link'><img src='{html.escape(room['image_url'])}' class='card-img-top' alt='{html.escape(room['name'])}' /></a>
        <div class='card-body d-flex flex-column'>
          <h2 class='h5'><a href='/rooms/{rid}' class='room-link'>{html.escape(room['name'])}</a></h2>
          <p>{html.escape(room['description'])}</p>
          <p class='small text-muted mb-2'>{room['beds']} krevat(e) • Deri {room['guests']} persona</p>
          <p class='fw-bold text-primary'>Nga {room['price_eur']}€ / natë</p>
          <div class='mt-auto d-flex gap-2'>
            <a class='btn btn-outline-primary' href='/rooms/{rid}'>Shiko dhomën</a>
            <a class='btn btn-warning' href='/contact?room_id={rid}'>Rezervo</a>
          </div>
        </div>
      </div>
    </div>
    """


def home_html() -> str:
    with db_connect() as db:
        rooms = db.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    cards = "".join(room_card(room) for room in rooms)
    body = f"""
<header class='hero text-white text-center d-flex align-items-center'><div class='container py-5'>
  <h1 class='display-5 fw-bold'>Mirë se vini në Hotel Valbona Crown</h1>
  <p class='lead'>Gjithçka tani është në një file të vetëm: <code>app.py</code>.</p>
  <a href='/rooms' class='btn btn-warning btn-lg mt-2'>Shiko dhomat</a>
  <a href='/downloads' class='btn btn-light btn-lg mt-2 ms-2'>Shkarko filet</a>
</div></header>
<main class='container py-5'><h2 class='mb-3'>Dhomat Kryesore</h2><div class='row g-4'>{cards}</div></main>
"""
    return render_page("Hotel Valbona Crown | Home", "home", body)


def rooms_html() -> str:
    with db_connect() as db:
        rooms = db.execute("SELECT * FROM rooms ORDER BY price_eur ASC").fetchall()
    return render_page("Hotel Valbona Crown | Dhomat", "rooms", f"<main class='container py-5'><h1 class='mb-3'>Dhomat</h1><div class='row g-4'>{''.join(room_card(r) for r in rooms)}</div></main>")


def room_detail_html(room_id: int) -> str:
    with db_connect() as db:
        room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None:
        return render_page("Nuk u gjet", "rooms", "<main class='container py-5'><h1>Dhoma nuk u gjet.</h1></main>")
    body = f"""
<main class='container py-5'><div class='row g-4'>
<div class='col-lg-6'><img class='img-fluid rounded shadow-sm' src='{html.escape(room['image_url'])}' alt='{html.escape(room['name'])}' /></div>
<div class='col-lg-6'><h1>{html.escape(room['name'])}</h1><p>{html.escape(room['long_description'])}</p>
<p><strong>Krevate:</strong> {room['beds']}</p><p><strong>Kapaciteti:</strong> {room['guests']} persona</p>
<p class='fw-bold text-primary fs-5'>Nga {room['price_eur']}€ / natë</p>
<a class='btn btn-warning' href='/contact?room_id={room_id}'>Rezervo këtë dhomë</a>
</div></div></main>
"""
    return render_page(f"Hotel Valbona Crown | {room['name']}", "rooms", body)


def about_html() -> str:
    return render_page("Hotel Valbona Crown | About us", "about", "<main class='container py-5'><h1>Rreth Nesh</h1><p>Hotel modern me komoditet dhe mikpritje profesionale.</p></main>")


def contact_html(msg: str = "", kind: str = "success", selected_room_id: int | None = None) -> str:
    with db_connect() as db:
        rooms = db.execute("SELECT id, name FROM rooms ORDER BY id").fetchall()
    options = ["<option value=''>Zgjidh dhomën</option>"]
    for room in rooms:
        sel = " selected" if selected_room_id == int(room["id"]) else ""
        options.append(f"<option value='{room['id']}'{sel}>{html.escape(room['name'])}</option>")
    alert = f"<div class='alert alert-{kind}'>{html.escape(msg)}</div>" if msg else ""
    body = f"""
<main class='container py-5'><div class='row justify-content-center'><div class='col-lg-8'>
<h1>Kontakto / Rezervo</h1>{alert}
<form id='contactForm' method='post' action='/contact' class='needs-validation' novalidate>
<div class='row g-3'>
<div class='col-md-6'><input class='form-control' name='name' placeholder='Emri i plotë' required /></div>
<div class='col-md-6'><input class='form-control' type='email' name='email' placeholder='Email' required /></div>
<div class='col-md-6'><input class='form-control' name='phone' placeholder='Telefoni' required /></div>
<div class='col-md-6'><select name='room_id' class='form-select' required>{''.join(options)}</select></div>
<div class='col-md-6'><input class='form-control' type='date' name='checkin' required /></div>
<div class='col-md-6'><input class='form-control' type='date' name='checkout' required /></div>
<div class='col-12'><textarea class='form-control' name='message' rows='4' required></textarea></div>
<div class='col-12'><button class='btn btn-warning' type='submit'>Submit</button></div>
</div></form>
<p class='mt-3'><a href='/admin/reservations'>Shiko rezervimet</a></p>
</div></div></main>
"""
    return render_page("Hotel Valbona Crown | Contact us", "contact", body)


def reservations_html() -> str:
    with db_connect() as db:
        rows = db.execute(
            """
            SELECT r.full_name, r.email, rooms.name AS room_name, r.checkin_date, r.checkout_date, r.created_at
            FROM reservations r JOIN rooms ON rooms.id = r.room_id ORDER BY r.id DESC
            """
        ).fetchall()
    if not rows:
        table = "<p>Nuk ka rezervime.</p>"
    else:
        trs = "".join(
            f"<tr><td>{html.escape(r['full_name'])}</td><td>{html.escape(r['email'])}</td><td>{html.escape(r['room_name'])}</td><td>{r['checkin_date']}</td><td>{r['checkout_date']}</td><td>{r['created_at']}</td></tr>"
            for r in rows
        )
        table = f"<div class='table-responsive'><table class='table table-striped'><thead><tr><th>Emri</th><th>Email</th><th>Dhomë</th><th>Check-in</th><th>Check-out</th><th>Krijuar</th></tr></thead><tbody>{trs}</tbody></table></div>"
    return render_page("Rezervimet", "contact", f"<main class='container py-5'><h1>Rezervimet</h1>{table}</main>")


def downloads_html() -> str:
    links = "".join(
        f"<li><a href='/download/{html.escape(name)}' download>{html.escape(name)}</a></li>"
        for name in DOWNLOADABLE_FILES
    )
    content = f"""
<main class='container py-5'>
  <h1 class='mb-3'>Shkarko filet e projektuara</h1>
  <p>Zgjidh file-in që do të shkarkosh:</p>
  <ul>{links}</ul>
</main>
"""
    return render_page("Shkarkimet", "home", content)


class HotelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            return self.respond_html(home_html())
        if path == "/rooms":
            return self.respond_html(rooms_html())
        if path.startswith("/rooms/"):
            room_id = path.removeprefix("/rooms/")
            if room_id.isdigit():
                return self.respond_html(room_detail_html(int(room_id)))
            return self.respond_html("ID jo valide", HTTPStatus.BAD_REQUEST)
        if path == "/about":
            return self.respond_html(about_html())
        if path == "/contact":
            q = parse_qs(parsed.query)
            room_id = q.get("room_id", [""])[0]
            selected = int(room_id) if room_id.isdigit() else None
            return self.respond_html(contact_html(selected_room_id=selected))
        if path == "/admin/reservations":
            return self.respond_html(reservations_html())
        if path == "/downloads":
            return self.respond_html(downloads_html())
        if path.startswith('/download/'):
            file_key = path.removeprefix('/download/')
            if file_key in DOWNLOADABLE_FILES:
                return self.download_file(DOWNLOADABLE_FILES[file_key], file_key.replace('/', '-'))
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/contact":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}

        required = ["name", "email", "phone", "room_id", "checkin", "checkout", "message"]
        if any(not form.get(field, "").strip() for field in required):
            return self.respond_html(contact_html("Plotëso të gjitha fushat.", "danger"), HTTPStatus.BAD_REQUEST)

        if not form["room_id"].isdigit():
            return self.respond_html(contact_html("Dhoma nuk është valide.", "danger"), HTTPStatus.BAD_REQUEST)

        room_id = int(form["room_id"])

        try:
            checkin = datetime.strptime(form["checkin"], "%Y-%m-%d")
            checkout = datetime.strptime(form["checkout"], "%Y-%m-%d")
        except ValueError:
            return self.respond_html(contact_html("Datat nuk janë valide.", "danger", room_id), HTTPStatus.BAD_REQUEST)

        if checkout <= checkin:
            return self.respond_html(contact_html("Check-out duhet të jetë pas check-in.", "danger", room_id), HTTPStatus.BAD_REQUEST)

        with db_connect() as db:
            exists = db.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone()
            if not exists:
                return self.respond_html(contact_html("Dhoma nuk ekziston.", "danger"), HTTPStatus.BAD_REQUEST)
            db.execute(
                """
                INSERT INTO reservations(full_name, email, phone, room_id, checkin_date, checkout_date, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form["name"].strip(),
                    form["email"].strip(),
                    form["phone"].strip(),
                    room_id,
                    form["checkin"],
                    form["checkout"],
                    form["message"].strip(),
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )

        return self.respond_html(contact_html(f"Faleminderit {form['name']}! Rezervimi u ruajt me sukses.", "success", room_id))

    def download_file(self, path: Path, download_name: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/x-python")
        self.send_header("Content-Disposition", f"attachment; filename={download_name}")
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
