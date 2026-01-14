function proverka() {
  return confirm("Видалити дане поле? ");
}

function delete_item() {
  return alert(" Видалити неможливо! Даний кабінет використовуться!");
}

/**
 * Legacy show/hide (залишив, якщо десь ще використовується).
 */
function my_func(i) {
  const myPsw = document.getElementById("remove-heli-" + i);
  const displaySetting = myPsw.style.display;
  const clockButton = document.getElementById("btn" + i);
  if (displaySetting === "block") {
    myPsw.style.display = "none";
    clockButton.innerHTML = "Show";
  } else {
    myPsw.style.display = "block";
    clockButton.innerHTML = "Hide";
  }
}

/**
 * CSRF helper
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * New: Lazy decrypt + copy to clipboard.
 *
 * Usage in template:
 *   onclick="decryptAndCopy({id: {{i.id}}, model: 'pay', field: 'password'})"
 *
 * Also supports positional call:
 *   decryptAndCopy({{i.id}}, 'password', 'pay')
 */
async function decryptAndCopy(arg1, fieldArg, modelArg) {
  let id, field, model;

  // Support object style: decryptAndCopy({id, field, model})
  if (typeof arg1 === "object" && arg1 !== null) {
    id = arg1.id;
    field = arg1.field;
    model = arg1.model;
  } else {
    id = arg1;
    field = fieldArg;
    model = modelArg;
  }

  if (!id || !field || !model) {
    console.error("decryptAndCopy: missing params", { id, field, model });
    return;
  }

  const valueElId = `${model}-${field}-val-${id}`;
  const btnId = `${model}-${field}-btn-${id}`;

  const valueEl = document.getElementById(valueElId);
  const btn = document.getElementById(btnId);

  if (!valueEl || !btn) {
    console.error("decryptAndCopy: DOM elements not found", { valueElId, btnId });
    return;
  }

  // Toggle hide
  const isVisible = valueEl.getAttribute("data-visible") === "1";
  if (isVisible) {
    valueEl.textContent = "*****";
    valueEl.setAttribute("data-visible", "0");
    btn.textContent = "Show";
    return;
  }

  // If already decrypted once -> reuse, just show + copy
  const cached = valueEl.getAttribute("data-decrypted");
  if (cached && cached.length > 0) {
    valueEl.textContent = cached;
    valueEl.setAttribute("data-visible", "1");
    btn.textContent = "Hide";
    try {
      await navigator.clipboard.writeText(cached);
    } catch (e) {
      console.warn("Clipboard copy failed:", e);
    }
    return;
  }

  // Fetch decrypt from backend
  try {
    const resp = await fetch("/decrypt_item/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        model: model,
        id: id,
        field: field,
      }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      alert(data.error || "Decrypt error");
      return;
    }

    const plain = data.value;

    valueEl.textContent = plain;
    valueEl.setAttribute("data-visible", "1");
    valueEl.setAttribute("data-decrypted", plain);
    btn.textContent = "Hide";

    try {
      await navigator.clipboard.writeText(plain);
    } catch (e) {
      console.warn("Clipboard copy failed:", e);
    }
  } catch (err) {
    console.error(err);
    alert("Request failed");
  }
}
/**
 * Generate a strong password using crypto-grade randomness.
 * Length: 14-20.
 */
function generateStrongPassword(length = null) {
  // Safe-ish special chars for most services (no spaces/quotes/backticks).
  const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const LOWER = "abcdefghijkmnopqrstuvwxyz";
  const DIGIT = "0123456789";
  const SPECIAL = "!@#$%^&*_-+=:,.?";

  const ALL = UPPER + LOWER + DIGIT + SPECIAL;

  const randIntInclusive = (min, max) => {
    const arr = new Uint32Array(1);
    window.crypto.getRandomValues(arr);
    return min + (arr[0] % (max - min + 1));
  };

  // If length not provided -> random 14..20
  const len = (length === null || length === undefined)
    ? randIntInclusive(14, 20)
    : Math.max(Number(length) || 0, 12);

  // Pick at least 1 char from each bucket.
  const picks = [UPPER, LOWER, DIGIT, SPECIAL];
  const out = [];

  const pickOne = (chars) => {
    const arr = new Uint32Array(1);
    window.crypto.getRandomValues(arr);
    return chars[arr[0] % chars.length];
  };

  for (const bucket of picks) out.push(pickOne(bucket));
  while (out.length < len) out.push(pickOne(ALL));

  // Fisher–Yates shuffle.
  for (let i = out.length - 1; i > 0; i--) {
    const arr = new Uint32Array(1);
    window.crypto.getRandomValues(arr);
    const j = arr[0] % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }

  return out.join("");
}

async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    // fall through
  }

  // Legacy fallback
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    console.warn("Clipboard copy failed:", e);
    return false;
  }
}

function injectPasswordGenStylesOnce() {
  if (document.getElementById("pay-password-gen-style")) return;

  const style = document.createElement("style");
  style.id = "pay-password-gen-style";
  style.textContent = `
    .pay-gen-wrap{display:inline-flex;align-items:stretch;gap:0;}
    .pay-gen-wrap input{margin:0;border-top-right-radius:0;border-bottom-right-radius:0;}
    .pay-gen-btn{
      padding:0 10px;margin:0;min-width:34px;line-height:1;
      display:inline-flex;align-items:center;justify-content:center;
      border-top-left-radius:0;border-bottom-left-radius:0;
    }
    .pay-gen-btn i{pointer-events:none;}
    .pay-password-generated{outline:2px solid #7fff00;transition:outline-color .3s;}
  `;
  document.head.appendChild(style);
}

function isPayAppFormInput(input) {
  // Hard gate: only on our forms, never on auth/login pages.
  const form = input.closest("form");
  if (!form) return false;
  return form.classList.contains("form_pay") || form.classList.contains("form_cabinet");
}

/**
 * DOM-injection: find inputs by name and add a small key button next to them.
 */
function attachPasswordGenerators() {
  injectPasswordGenStylesOnce();

  const names = ["password", "email_password"];
  const selector = names.map((n) => `input[name="${n}"]`).join(",");
  const inputs = document.querySelectorAll(selector);

  inputs.forEach((input) => {
    if (!isPayAppFormInput(input)) return;          // <-- FIX: no login page
    if (input.dataset.genAttached === "1") return;
    input.dataset.genAttached = "1";

    const wrap = document.createElement("span");
    wrap.className = "pay-gen-wrap";

    const parent = input.parentElement;
    if (parent) {
      parent.insertBefore(wrap, input);
      wrap.appendChild(input);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn_pay_yellow pay-gen-btn";
    button.title = "Generate password";
    button.setAttribute("aria-label", `Generate ${input.name}`);
    button.innerHTML = '<i class="fa-solid fa-key"></i>'; // <-- icon instead of text

    wrap.appendChild(button);

    button.addEventListener("click", async () => {
      if (!window.crypto || !window.crypto.getRandomValues) {
        alert("Crypto API is not available in this browser.");
        return;
      }

      const pwd = generateStrongPassword();
      input.value = pwd;

      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));

      input.classList.add("pay-password-generated");
      setTimeout(() => input.classList.remove("pay-password-generated"), 900);

      await copyToClipboard(pwd);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  attachPasswordGenerators();
});