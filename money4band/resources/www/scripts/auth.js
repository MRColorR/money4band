/**
 * M4B Dashboard authentication helper.
 *
 * - Reads ?token=<key> from the URL, logs in via cookie, and strips the param.
 * - Exposes window.m4bFetch() - a fetch() wrapper that auto-handles 401s by
 *   showing a login prompt and retrying once after successful authentication.
 * - On first load, probes /api/status to check if auth is needed. If 401,
 *   prompts immediately so the page data loads on the first visit.
 * - Injects a Logout button into the page when authenticated.
 */
(function () {
  "use strict";

  /* ---------- helpers -------------------------------------------------- */

  function getCookie(name) {
    var match = document.cookie.match(
      new RegExp("(?:^|; )" + name + "=([^;]*)")
    );
    return match ? decodeURIComponent(match[1]) : null;
  }

  /** POST the token to /api/auth/login - sets an httpOnly cookie. */
  function serverLogin(token) {
    return fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
    }).then(function (r) {
      if (!r.ok) throw new Error("Invalid API key");
      // Set a non-httpOnly marker so JS knows we're logged in.
      document.cookie = "m4b_logged_in=1;path=/;samesite=strict";
      return r.json();
    });
  }

  /** POST /api/auth/logout - clears the httpOnly cookie. */
  function serverLogout() {
    return fetch("/api/auth/logout", { method: "POST" }).then(function () {
      document.cookie = "m4b_logged_in=;path=/;max-age=0";
      window.location.reload();
    });
  }

  /** Show a simple prompt, attempt login, resolve true/false. */
  function promptLogin() {
    var key = prompt(
      "This dashboard requires an API key.\n" +
        'Run "m4b dashboard show-key" to get yours.'
    );
    if (!key) return Promise.resolve(false);
    return serverLogin(key.trim()).then(
      function () {
        return true;
      },
      function () {
        alert("Invalid API key. Try again.");
        return false;
      }
    );
  }

  /* ---------- logout button ------------------------------------------- */

  /** Inject a small Logout button in the top-right corner. */
  function showLogoutButton() {
    if (document.getElementById("m4b-logout-btn")) return;
    var btn = document.createElement("button");
    btn.id = "m4b-logout-btn";
    btn.textContent = "Logout";
    btn.style.cssText =
      "position:fixed;top:12px;right:16px;z-index:99999;" +
      "padding:6px 16px;border:none;border-radius:4px;cursor:pointer;" +
      "background:#e74c3c;color:#fff;font-size:13px;font-family:inherit;" +
      "opacity:0.9;transition:opacity .2s";
    btn.onmouseenter = function () { btn.style.opacity = "1"; };
    btn.onmouseleave = function () { btn.style.opacity = "0.9"; };
    btn.onclick = serverLogout;
    document.body.appendChild(btn);
  }

  /* ---------- m4bFetch ------------------------------------------------- */

  /**
   * Drop-in replacement for fetch() that retries once on 401
   * after prompting the user for the API key.
   */
  window.m4bFetch = function m4bFetch(url, opts) {
    return fetch(url, opts).then(function (response) {
      if (response.status !== 401) return response;
      // Got 401 - ask for the key and retry once.
      return promptLogin().then(function (ok) {
        if (!ok) return response; // user cancelled
        return fetch(url, opts);
      });
    });
  };

  /* ---------- auto-login from ?token= --------------------------------- */

  var params = new URLSearchParams(window.location.search);
  var urlToken = params.get("token");
  if (urlToken) {
    // Strip the token from the visible URL to avoid leaking it in history.
    params.delete("token");
    var clean =
      window.location.pathname +
      (params.toString() ? "?" + params.toString() : "") +
      window.location.hash;
    window.history.replaceState(null, "", clean);

    serverLogin(urlToken).catch(function () {
      /* ignore - will prompt later if needed */
    });
  }

  /* ---------- probe on first load -------------------------------------- */

  if (!getCookie("m4b_logged_in") && !urlToken) {
    fetch("/api/status").then(function (r) {
      if (r.status === 401) {
        promptLogin().then(function (ok) {
          if (ok) window.location.reload();
        });
      } else {
        // Auth not required (localhost) - no logout button needed.
      }
    });
  } else {
    // We have a cookie - show the logout button.
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", showLogoutButton);
    } else {
      showLogoutButton();
    }
  }
})();
