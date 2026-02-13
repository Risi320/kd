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

        room_columns = {row[1] for row in db.execute("PRAGMA table_info(rooms)").fetchall()}
        if "long_description" not in room_columns:
            db.execute("ALTER TABLE rooms ADD COLUMN long_description TEXT NOT NULL DEFAULT ''")
        if "beds" not in room_columns:
            db.execute("ALTER TABLE rooms ADD COLUMN beds INTEGER NOT NULL DEFAULT 1")
        if "guests" not in room_columns:
            db.execute("ALTER TABLE rooms ADD COLUMN guests INTEGER NOT NULL DEFAULT 2")

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

        reservation_columns = {row[1] for row in db.execute("PRAGMA table_info(reservations)").fetchall()}
        if "room_id" not in reservation_columns:
            db.execute("ALTER TABLE reservations RENAME TO reservations_legacy")
            db.execute(
                """
                CREATE TABLE reservations (
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
            default_room_id = db.execute("SELECT id FROM rooms ORDER BY id LIMIT 1").fetchone()[0]
            db.execute(
                """
                INSERT INTO reservations(full_name, email, phone, room_id, checkin_date, checkout_date, message, created_at)
                SELECT full_name, email, phone, ?, checkin_date, checkout_date, message, created_at
                FROM reservations_legacy
                """,
                (default_room_id,),
            )
            db.execute("DROP TABLE reservations_legacy")

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
                        "Dhomë e bollshme me 2 krevate, kënd lojërash për fëmijë dhe hapësirë për valixhe.",
                        105,
                        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                        2,
                        4,
                    ),
                ],
            )

        db.execute(
            """
            UPDATE rooms
            SET long_description = description
            WHERE long_description IS NULL OR TRIM(long_description) = ''
            """
        )


def render_page(title: str, active: str, content: str) -> str:
    nav = f"""
    <nav class=\"navbar navbar-expand-lg navbar-dark bg-dark sticky-top\">
      <div class=\"container\">
        <a class=\"navbar-brand fw-bold\" href=\"/\">Hotel Valbona Crown</a>
        <button class=\"navbar-toggler\" type=\"button\" data-bs-toggle=\"collapse\" data-bs-target=\"#mainNav\">
          <span class=\"navbar-toggler-icon\"></span>
        </button>
        <div class=\"collapse navbar-collapse\" id=\"mainNav\">
          <ul class=\"navbar-nav ms-auto\">
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'home' else ''}\" href=\"/\">Home</a></li>
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'rooms' else ''}\" href=\"/rooms\">Dhomat</a></li>
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'about' else ''}\" href=\"/about\">About us</a></li>
            <li class=\"nav-item\"><a class=\"nav-link {'active' if active == 'contact' else ''}\" href=\"/contact\">Contact us</a></li>
          </ul>
        </div>
      </div>
    </nav>
    """

    return f"""<!doctype html>
<html lang=\"sq\"><head>
<meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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


def room_card(room: sqlite3.Row) -> str:
    room_id = int(room["id"])
    room_name = html.escape(room["name"])
    room_image = html.escape(room["image_url"])
    room_description = html.escape(room["description"])
    return f"""
    <div class='col-md-4'>
      <div class='card h-100 shadow-sm'>
        <a href='/rooms/{room_id}' class='room-link'>
          <img src='{room_image}' class='card-img-top' alt='{room_name}' />
        </a>
        <div class='card-body d-flex flex-column'>
          <h2 class='h5'><a href='/rooms/{room_id}' class='room-link'>{room_name}</a></h2>
          <p>{room_description}</p>
          <p class='small text-muted mb-2'>{room["beds"]} krevat(e) • Deri {room["guests"]} persona</p>
          <p class='fw-bold text-primary'>Nga {room["price_eur"]}€ / natë</p>
          <div class='mt-auto d-flex gap-2'>
            <a class='btn btn-outline-primary' href='/rooms/{room_id}'>Shiko dhomën</a>
            <a class='btn btn-warning' href='/contact?room_id={room_id}'>Rezervo</a>
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
  <p class='lead'>Komoditet, elegancë dhe pamje fantastike për pushimet tuaja perfekte.</p>
  <a href='/rooms' class='btn btn-warning btn-lg mt-2'>Shiko të gjitha dhomat</a>
</div></header>
<main>
  <section class='container py-5'>
    <h2 class='mb-3'>Dhomat Kryesore</h2>
    <div class='row g-4'>{cards}</div>
  </section>
</main>
"""
    return render_page("Hotel Valbona Crown | Home", "home", body)


def rooms_html() -> str:
    with db_connect() as db:
        rooms = db.execute("SELECT * FROM rooms ORDER BY price_eur ASC").fetchall()
    cards = "".join(room_card(room) for room in rooms)
    body = f"""
<main class='container py-5'>
  <h1 class='mb-3'>Dhomat që ofrojmë</h1>
  <p class='text-muted'>Kliko në secilën dhomë për detaje dhe rezervim.</p>
  <div class='row g-4'>{cards}</div>
</main>
"""
    return render_page("Hotel Valbona Crown | Dhomat", "rooms", body)


def room_detail_html(room_id: int) -> str:
    with db_connect() as db:
        room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()

    if room is None:
        return render_page("Nuk u gjet", "rooms", "<main class='container py-5'><h1>Dhoma nuk u gjet.</h1></main>")

    body = f"""
<main class='container py-5'>
  <div class='row g-4 align-items-start'>
    <div class='col-lg-6'>
      <img class='img-fluid rounded shadow-sm' src='{html.escape(room["image_url"])}' alt='{html.escape(room["name"])}' />
    </div>
    <div class='col-lg-6'>
      <h1>{html.escape(room["name"])}</h1>
      <p>{html.escape(room["long_description"])}</p>
      <p class='mb-1'><strong>Krevate:</strong> {room["beds"]}</p>
      <p class='mb-1'><strong>Kapaciteti:</strong> {room["guests"]} persona</p>
      <p class='fw-bold text-primary fs-5'>Nga {room["price_eur"]}€ / natë</p>
      <a class='btn btn-warning' href='/contact?room_id={room_id}'>Rezervo këtë dhomë</a>
      <a class='btn btn-outline-secondary ms-2' href='/rooms'>Kthehu</a>
    </div>
  </div>
</main>
"""
    return render_page(f"Hotel Valbona Crown | {room['name']}", "rooms", body)


def about_html() -> str:
    body = """
<main class='container py-5'>
<section class='mb-4'><h1 class='mb-3'>Rreth Nesh</h1>
<p>Hotel Valbona Crown ofron mikpritje profesionale, komoditet modern dhe ambient relaksues për turistë dhe familje.</p>
</section>
<section class='row g-4'>
<div class='col-md-6'><div class='p-4 bg-light rounded h-100 shadow-sm'><h2 class='h4'>Misioni ynë</h2><p>Të krijojmë kujtime të bukura për çdo mysafir përmes rehatisë dhe cilësisë së lartë.</p></div></div>
<div class='col-md-6'><div class='p-4 bg-light rounded h-100 shadow-sm'><h2 class='h4'>Shërbimet</h2><ul class='mb-0'><li>Recepsion 24/7</li><li>Restaurant & Bar</li><li>Spa dhe pishinë</li><li>Transport aeroporti</li></ul></div></div>
</section>
</main>
"""
    return render_page("Hotel Valbona Crown | About us", "about", body)


def contact_html(flash: str = "", category: str = "success", selected_room_id: int | None = None) -> str:
    with db_connect() as db:
        rooms = db.execute("SELECT id, name FROM rooms ORDER BY id").fetchall()

    options = ["<option value=''>Zgjidh dhomën</option>"]
    for room in rooms:
        selected = " selected" if selected_room_id == int(room["id"]) else ""
        options.append(f"<option value='{room['id']}'{selected}>{html.escape(room['name'])}</option>")

    flash_html = f"<div class='alert alert-{category}'>{html.escape(flash)}</div>" if flash else ""
    body = f"""
<main class='container py-5'><section class='row justify-content-center'><div class='col-lg-8'>
<h1 class='mb-3'>Kontakto / Rezervo</h1><p class='text-muted'>Plotëso formën dhe rezervimi ruhet në databazë.</p>
{flash_html}
<form id='contactForm' class='needs-validation' novalidate method='post' action='/contact'>
<div class='row g-3'>
<div class='col-md-6'><label class='form-label' for='name'>Emri i plotë</label><input id='name' name='name' class='form-control' required minlength='3' /></div>
<div class='col-md-6'><label class='form-label' for='email'>Email</label><input id='email' name='email' type='email' class='form-control' required /></div>
<div class='col-md-6'><label class='form-label' for='phone'>Telefoni</label><input id='phone' name='phone' class='form-control' pattern='[0-9+ ]{{8,15}}' required /></div>
<div class='col-md-6'><label class='form-label' for='room_id'>Dhoma</label><select id='room_id' name='room_id' class='form-select' required>{''.join(options)}</select></div>
<div class='col-md-6'><label class='form-label' for='checkin'>Check-in</label><input id='checkin' name='checkin' type='date' class='form-control' required /></div>
<div class='col-md-6'><label class='form-label' for='checkout'>Check-out</label><input id='checkout' name='checkout' type='date' class='form-control' required /></div>
<div class='col-12'><label class='form-label' for='message'>Mesazhi</label><textarea id='message' name='message' class='form-control' rows='4' required minlength='10'></textarea></div>
<div class='col-12'><button type='submit' class='btn btn-warning'>Submit</button></div>
</div></form>
<p class='mt-3'><a href='/admin/reservations'>Shiko rezervimet</a></p>
</div></section></main>
"""
    return render_page("Hotel Valbona Crown | Contact us", "contact", body)


def reservations_html() -> str:
    with db_connect() as db:
        reservations = db.execute(
            """
            SELECT r.full_name, r.email, rooms.name AS room_name, r.checkin_date, r.checkout_date, r.created_at
            FROM reservations r
            JOIN rooms ON rooms.id = r.room_id
            ORDER BY r.id DESC
            """
        ).fetchall()

    if reservations:
        rows = "".join(
            f"<tr><td>{html.escape(r['full_name'])}</td><td>{html.escape(r['email'])}</td><td>{html.escape(r['room_name'])}</td><td>{r['checkin_date']}</td><td>{r['checkout_date']}</td><td>{r['created_at']}</td></tr>"
            for r in reservations
        )
        table = f"<div class='table-responsive'><table class='table table-striped'><thead><tr><th>Emri</th><th>Email</th><th>Dhomë</th><th>Check-in</th><th>Check-out</th><th>Krijuar</th></tr></thead><tbody>{rows}</tbody></table></div>"
    else:
        table = "<p>Ende nuk ka rezervime të ruajtura.</p>"

    return render_page("Hotel Valbona Crown | Reservations", "contact", f"<main class='container py-5'><h1 class='mb-4'>Rezervimet</h1>{table}</main>")


class HotelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            return self.respond_html(home_html())
        if path == "/rooms":
            return self.respond_html(rooms_html())
        if path.startswith("/rooms/"):
            room_id_text = path.removeprefix("/rooms/")
            if room_id_text.isdigit():
                return self.respond_html(room_detail_html(int(room_id_text)))
            return self.respond_html(render_page("Gabim", "rooms", "<main class='container py-5'><h1>ID jo valide.</h1></main>"), HTTPStatus.BAD_REQUEST)
        if path == "/about":
            return self.respond_html(about_html())
        if path == "/contact":
            query = parse_qs(parsed.query)
            room_id = query.get("room_id", [""])[0]
            selected = int(room_id) if room_id.isdigit() else None
            return self.respond_html(contact_html(selected_room_id=selected))
        if path == "/admin/reservations":
            return self.respond_html(reservations_html())
        if path.startswith("/static/"):
            return self.serve_static(path)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/contact":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}

        required = ["name", "email", "phone", "room_id", "checkin", "checkout", "message"]
        if any(not form.get(field, "").strip() for field in required):
            return self.respond_html(contact_html("Të gjitha fushat janë të detyrueshme.", "danger"), HTTPStatus.BAD_REQUEST)

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
            room_exists = db.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone()
            if room_exists is None:
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

        self.respond_html(contact_html(f"Faleminderit {form['name']}! Rezervimi u ruajt me sukses.", "success"))

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
