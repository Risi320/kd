const form = document.getElementById("contactForm");
const result = document.getElementById("result");

if (form && result) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!form.checkValidity()) {
      event.stopPropagation();
      form.classList.add("was-validated");
      return;
    }

    const formData = new FormData(form);
    const checkin = new Date(formData.get("checkin"));
    const checkout = new Date(formData.get("checkout"));

    if (checkout <= checkin) {
      result.className = "alert alert-danger mt-3";
      result.textContent = "Check-out duhet të jetë pas check-in.";
      result.classList.remove("d-none");
      return;
    }

    const reservation = {
      name: formData.get("name"),
      email: formData.get("email"),
      phone: formData.get("phone"),
      room: formData.get("room"),
      checkin: formData.get("checkin"),
      checkout: formData.get("checkout"),
      message: formData.get("message"),
      createdAt: new Date().toISOString()
    };

    const reservations = JSON.parse(localStorage.getItem("hotelReservations") || "[]");
    reservations.push(reservation);
    localStorage.setItem("hotelReservations", JSON.stringify(reservations));

    result.className = "alert alert-success mt-3";
    result.textContent = `Faleminderit ${reservation.name}! Kërkesa juaj u dërgua me sukses.`;
    result.classList.remove("d-none");

    form.reset();
    form.classList.remove("was-validated");
  });
}
