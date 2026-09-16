function togglePassword() {
  const input = document.getElementById("password");
  const button = document.querySelector(".show-btn");
  if (input.type === "password") {
    input.type = "text";
    button.textContent = "Hide";
  } else {
    input.type = "password";
    button.textContent = "Show";
  }
}

document.getElementById("loginForm")?.addEventListener("submit", function (e) {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const message = document.getElementById("loginMessage");

  if (!email || !password) {
    message.textContent = "Please enter your email and password.";
    return;
  }

  // Demo login: this front-end page does not validate against a database.
  message.style.color = "#2d9d62";
  message.textContent = "Login successful. Opening Smart Campus...";
  setTimeout(() => window.location.href = "home.html", 500);
});

function logout() {
  window.location.href = "login.html";
}

function demoAction(name) {
  alert(name + " page can be connected to your Flask/Python backend next.");
}

function searchItems() {
  const input = document.getElementById("searchInput").value.trim();
  const category = document.getElementById("category").value;
  const result = document.getElementById("searchResult");

  if (!input && !category) {
    result.textContent = "Enter an item name or choose a category to search.";
    return;
  }

  const query = input || "all items";
  result.textContent = `Demo search: showing results for "${query}"${category ? " in " + category : ""}. Connect this form to your database to show real reports.`;
}
