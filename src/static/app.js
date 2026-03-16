document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const authStatus = document.getElementById("auth-status");
  const messageDiv = document.getElementById("message");
  const emailInput = document.getElementById("email");

  let authToken = localStorage.getItem("authToken") || "";
  let currentUser = null;

  function setMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function getAuthHeaders() {
    if (!authToken) {
      return {};
    }

    return {
      Authorization: `Bearer ${authToken}`,
    };
  }

  function updateSignupEmailState() {
    if (currentUser && currentUser.role === "student") {
      emailInput.value = currentUser.email;
      emailInput.readOnly = true;
    } else {
      emailInput.readOnly = false;
      emailInput.value = "";
    }
  }

  function updateAuthStatus() {
    if (currentUser) {
      authStatus.textContent = `Logged in as ${currentUser.email} (${currentUser.role})`;
      authStatus.className = "success";
    } else {
      authStatus.textContent =
        "Not logged in. Write actions require authentication.";
      authStatus.className = "info";
    }

    updateSignupEmailState();
  }

  async function fetchCurrentUser() {
    if (!authToken) {
      currentUser = null;
      updateAuthStatus();
      return;
    }

    try {
      const response = await fetch("/auth/me", {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        authToken = "";
        localStorage.removeItem("authToken");
        currentUser = null;
        updateAuthStatus();
        return;
      }

      currentUser = await response.json();
      updateAuthStatus();
    } catch (error) {
      console.error("Error validating session:", error);
      currentUser = null;
      updateAuthStatus();
    }
  }

  async function handleLogin(event) {
    event.preventDefault();

    const loginEmail = document.getElementById("login-email").value;
    const loginPassword = document.getElementById("login-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        setMessage(result.detail || "Login failed", "error");
        return;
      }

      authToken = result.token;
      localStorage.setItem("authToken", authToken);
      currentUser = result.user;
      updateAuthStatus();
      setMessage(result.message, "success");
      fetchActivities();
    } catch (error) {
      console.error("Error logging in:", error);
      setMessage("Failed to login. Please try again.", "error");
    }
  }

  async function handleLogout() {
    if (authToken) {
      try {
        await fetch("/auth/logout", {
          method: "POST",
          headers: getAuthHeaders(),
        });
      } catch (error) {
        console.error("Error logging out:", error);
      }
    }

    authToken = "";
    localStorage.removeItem("authToken");
    currentUser = null;
    updateAuthStatus();
    setMessage("Logged out", "info");
    fetchActivities();
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        currentUser
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    if (!currentUser) {
      setMessage("Please login to unregister participants.", "error");
      return;
    }

    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        setMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        setMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      console.error("Error unregistering:", error);
      setMessage("Failed to unregister. Please try again.", "error");
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Please login to sign up for an activity.", "error");
      return;
    }

    const email = emailInput.value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        setMessage(result.message, "success");
        signupForm.reset();
        updateSignupEmailState();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        setMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      console.error("Error signing up:", error);
      setMessage("Failed to sign up. Please try again.", "error");
    }
  });

  loginForm.addEventListener("submit", handleLogin);
  logoutButton.addEventListener("click", handleLogout);

  // Initialize app
  fetchCurrentUser().then(fetchActivities);
});
