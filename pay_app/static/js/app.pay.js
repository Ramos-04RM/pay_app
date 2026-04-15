function confirmDelete() {
  return confirm("Видалити дане поле? ");
}

function showDeleteBlocked() {
  alert("Видалити неможливо! Даний кабінет використовується.");
}

const SVG_NS = "http://www.w3.org/2000/svg";

const ICON_PATHS = {
  eye: [
    { d: "M1.5 12s3.5-7 10.5-7 10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12Z" },
    { d: "M12 16.25A4.25 4.25 0 1 0 12 7.75a4.25 4.25 0 0 0 0 8.5Z" },
  ],
  "eye-off": [
    { d: "M3 3l18 18" },
    { d: "M10.6 5.2A12.7 12.7 0 0 1 12 5c7 0 10.5 7 10.5 7a19.6 19.6 0 0 1-4.1 4.8" },
    { d: "M6.1 6.1A19.5 19.5 0 0 0 1.5 12s3.5 7 10.5 7c1.8 0 3.4-.4 4.8-1" },
    { d: "M9.9 9.9A3 3 0 0 0 9 12a3 3 0 0 0 3 3c.8 0 1.5-.3 2.1-.9" },
  ],
  key: [
    { d: "M14.5 3a6.5 6.5 0 1 0 4.7 11l1.8 1.8h2v2h2v2h2v-3.2l-4.7-4.7A6.5 6.5 0 0 0 14.5 3Z" },
    { d: "M8.5 12.5h.01" },
  ],
};

function createSvgIcon(name, extraClass = "") {
  const paths = ICON_PATHS[name];
  if (!paths) return document.createTextNode("");

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("class", extraClass ? `icon-svg ${extraClass}` : "icon-svg");

  paths.forEach((pathDef) => {
    const path = document.createElementNS(SVG_NS, "path");
    Object.entries(pathDef).forEach(([key, value]) => {
      path.setAttribute(key, value);
    });
    svg.appendChild(path);
  });

  return svg;
}

function replaceButtonIcon(button, iconName) {
  if (!button) return;

  const oldIcon = button.querySelector(".icon-svg, i");
  if (oldIcon) oldIcon.remove();

  button.prepend(createSvgIcon(iconName));
}

function my_func(i) {
  const target = document.getElementById("remove-heli-" + i);
  const button = document.getElementById("btn" + i);
  if (!target || !button) return;
  const isHidden = target.hasAttribute("hidden") || target.style.display === "none" || target.style.display === "";
  if (isHidden) {
    target.hidden = false;
    target.style.removeProperty("display");
    setIconButtonState(button, true);
    return;
  }
  target.hidden = true;
  target.style.display = "none";
  setIconButtonState(button, false);
}

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

let toastTimer = null;

function ensureToast() {
  let toast = document.getElementById("pay-app-toast");
  if (toast) return toast;

  toast = document.createElement("div");
  toast.id = "pay-app-toast";
  toast.className = "copy-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  toast.setAttribute("aria-atomic", "true");
  document.body.appendChild(toast);
  return toast;
}

function showToast(message, isError = false) {
  const toast = ensureToast();
  toast.textContent = message;
  toast.classList.toggle("is-error", Boolean(isError));
  toast.classList.add("is-visible");

  if (toastTimer) {
    clearTimeout(toastTimer);
  }

  toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 1900);
}

function setIconButtonState(button, isActive) {
  if (!button) return;

  const showLabel = button.dataset.showLabel || "Показати";
  const hideLabel = button.dataset.hideLabel || "Сховати";
  const label = isActive ? hideLabel : showLabel;
  const iconName = isActive ? "eye-off" : "eye";
  replaceButtonIcon(button, iconName);

  let hiddenText = button.querySelector(".visually-hidden");
  if (!hiddenText) {
    hiddenText = document.createElement("span");
    hiddenText.className = "visually-hidden";
    button.appendChild(hiddenText);
  }
  hiddenText.textContent = label;

  button.setAttribute("aria-label", label);
  button.setAttribute("title", label);
  if (button.hasAttribute("aria-expanded")) {
    button.setAttribute("aria-expanded", isActive ? "true" : "false");
  }
}

async function decryptAndCopy(arg1, fieldArg, modelArg) {
  let id;
  let field;
  let model;

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

  const isVisible = valueEl.getAttribute("data-visible") === "1";
  if (isVisible) {
    valueEl.textContent = "*****";
    valueEl.setAttribute("data-visible", "0");
    setIconButtonState(btn, false);
    return;
  }

  const cached = valueEl.getAttribute("data-decrypted");
  if (cached && cached.length > 0) {
    valueEl.textContent = cached;
    valueEl.setAttribute("data-visible", "1");
    setIconButtonState(btn, true);
    const copied = await copyToClipboard(cached);
    showToast(copied ? "Скопійовано в буфер обміну" : "Не вдалося скопіювати", !copied);
    return;
  }

  try {
    const resp = await fetch("/decrypt_item/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        model,
        id,
        field,
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
    setIconButtonState(btn, true);

    const copied = await copyToClipboard(plain);
    showToast(copied ? "Скопійовано в буфер обміну" : "Не вдалося скопіювати", !copied);
  } catch (error) {
    console.error(error);
    alert("Request failed");
  }
}

function generateStrongPassword(length = null) {
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

  const len = (length === null || length === undefined)
    ? randIntInclusive(14, 20)
    : Math.max(Number(length) || 0, 12);

  const picks = [UPPER, LOWER, DIGIT, SPECIAL];
  const out = [];

  const pickOne = (chars) => {
    const arr = new Uint32Array(1);
    window.crypto.getRandomValues(arr);
    return chars[arr[0] % chars.length];
  };

  for (const bucket of picks) out.push(pickOne(bucket));
  while (out.length < len) out.push(pickOne(ALL));

  for (let i = out.length - 1; i > 0; i -= 1) {
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
  } catch (error) {
    // fall through to fallback
  }

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
  } catch (error) {
    console.warn("Clipboard copy failed:", error);
    return false;
  }
}

function isPayAppFormInput(input) {
  const form = input.closest("form");
  if (!form) return false;
  return form.classList.contains("form_pay") || form.classList.contains("form_cabinet");
}

function attachPasswordGenerators() {
  const names = ["password", "email_password"];
  const selector = names.map((n) => `input[name="${n}"]`).join(",");
  const inputs = document.querySelectorAll(selector);

  inputs.forEach((input) => {
    if (!isPayAppFormInput(input)) return;
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
    button.className = "btn_pay_yellow pay-gen-btn icon-btn";
    button.title = "Згенерувати пароль";
    button.setAttribute("aria-label", `Generate ${input.name}`);
    button.appendChild(createSvgIcon("key"));

    const hiddenText = document.createElement("span");
    hiddenText.className = "visually-hidden";
    hiddenText.textContent = "Згенерувати пароль";
    button.appendChild(hiddenText);

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
      const copied = await copyToClipboard(pwd);
      showToast(copied ? "Пароль згенеровано і скопійовано" : "Пароль згенеровано", !copied);
    });
  });
}

function closeToggleTarget(button, target) {
  if (!button || !target) return;
  target.hidden = true;
  target.style.display = "none";
  setIconButtonState(button, false);
}

function openToggleTarget(button, target) {
  if (!button || !target) return;
  target.hidden = false;
  target.style.removeProperty("display");
  setIconButtonState(button, true);
}

function closeAllCabinetServiceLists(exceptTargetId = null) {
  document.querySelectorAll('[data-action="toggle-block"]').forEach((button) => {
    const targetId = button.dataset.targetId;
    if (!targetId || targetId === exceptTargetId) return;

    const target = document.getElementById(targetId);
    if (!target) return;

    const isOpen = !target.hasAttribute("hidden") && target.style.display !== "none";
    if (isOpen) {
      closeToggleTarget(button, target);
    }
  });
}

function restoreToggleStateFromHistory(state) {
  const targetId = state && state.payAppToggleOpen ? state.payAppToggleTargetId : null;

  closeAllCabinetServiceLists(targetId);

  if (!targetId) return;

  const button = document.querySelector(
    `[data-action="toggle-block"][data-target-id="${targetId}"]`
  );
  const target = document.getElementById(targetId);

  if (!button || !target) return;

  openToggleTarget(button, target);
}

function toggleTargetBlock(button) {
  const targetId = button.dataset.targetId;
  if (!targetId) return;

  const target = document.getElementById(targetId);
  if (!target) return;

  const isOpen = !target.hasAttribute("hidden") && target.style.display !== "none";

  if (isOpen) {
    closeToggleTarget(button, target);

    if (history.state && history.state.payAppToggleOpen && history.state.payAppToggleTargetId === targetId) {
      history.back();
    }
    return;
  }

  closeAllCabinetServiceLists(targetId);
  openToggleTarget(button, target);

  const url = new URL(window.location.href);
  url.hash = targetId;

  history.pushState(
    {
      payAppToggleOpen: true,
      payAppToggleTargetId: targetId,
    },
    "",
    url
  );
}

function syncCabinetSelectedTags() {
  const cabinetCreateForm = document.getElementById("cabinet-create-form");
  const cabinetTagCreateForm = document.getElementById("cabinet-tag-create-form");
  const hiddenContainer = document.getElementById("cabinet-selected-tags-hidden-container");

  if (!cabinetCreateForm || !cabinetTagCreateForm || !hiddenContainer) return;

  cabinetTagCreateForm.addEventListener("submit", () => {
    hiddenContainer.innerHTML = "";

    const checkedTags = cabinetCreateForm.querySelectorAll('input[name="tags"]:checked');
    checkedTags.forEach((checkbox) => {
      const hiddenInput = document.createElement("input");
      hiddenInput.type = "hidden";
      hiddenInput.name = "selected_tags";
      hiddenInput.value = checkbox.value;
      hiddenContainer.appendChild(hiddenInput);
    });
  });
}

function initCabinetHighlight() {
  const container = document.querySelector("[data-highlight-id]");
  if (!container) return;

  const highlightId = (container.dataset.highlightId || "").trim();
  if (!highlightId) return;

  const row = document.getElementById(`cabinet-${highlightId}`);
  if (!row) return;

  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("cabinet-pulse");
  setTimeout(() => row.classList.remove("cabinet-pulse"), 2000);
}

function togglePasswordInput(button) {
  const targetId = button.dataset.targetId;
  if (!targetId) return;
  const input = document.getElementById(targetId);
  if (!input) return;

  const show = input.type === "password";
  input.type = show ? "text" : "password";
  setIconButtonState(button, show);
}

function initIconButtons() {
  document.querySelectorAll('[data-action="decrypt-copy"]').forEach((button) => {
    const id = button.dataset.id;
    const model = button.dataset.model;
    const field = button.dataset.field;
    const valueEl = document.getElementById(`${model}-${field}-val-${id}`);
    const isVisible = valueEl ? valueEl.getAttribute("data-visible") === "1" : false;
    setIconButtonState(button, isVisible);
  });

  document.querySelectorAll('[data-action="toggle-block"]').forEach((button) => {
    const target = document.getElementById(button.dataset.targetId || "");
    const isOpen = Boolean(target && !target.hasAttribute("hidden") && target.style.display !== "none");
    setIconButtonState(button, isOpen);
  });

  document.querySelectorAll('[data-action="toggle-password-input"]').forEach((button) => {
    const target = document.getElementById(button.dataset.targetId || "");
    const isOpen = Boolean(target && target.type === "text");
    setIconButtonState(button, isOpen);
  });
}

function initStatisticsFilters() {
  const periodSelector = document.getElementById("statistics-period-selector");
  const customWrap = document.getElementById("statistics-custom-period");
  if (!periodSelector || !customWrap) return;

  const sync = () => {
    const isCustom = periodSelector.value === "custom";
    customWrap.hidden = !isCustom;
  };

  periodSelector.addEventListener("change", sync);
  sync();
}

document.addEventListener("click", async (event) => {
  const decryptBtn = event.target.closest('[data-action="decrypt-copy"]');
  if (decryptBtn) {
    event.preventDefault();
    await decryptAndCopy({
      id: decryptBtn.dataset.id,
      model: decryptBtn.dataset.model,
      field: decryptBtn.dataset.field,
    });
    return;
  }

 const copyBtn = event.target.closest('[data-action="copy-text"]');
 if (copyBtn) {
   event.preventDefault();
   const text = (copyBtn.dataset.copyText || "").trim();
   if (!text) return;

   const copied = await copyToClipboard(text);
   showToast(
     copied ? "Скопійовано в буфер обміну" : "Не вдалося скопіювати",
     !copied
   );
   return;
 }

  const toggleBtn = event.target.closest('[data-action="toggle-block"]');
  if (toggleBtn) {
    event.preventDefault();
    toggleTargetBlock(toggleBtn);
    return;
  }

  const togglePasswordBtn = event.target.closest('[data-action="toggle-password-input"]');
  if (togglePasswordBtn) {
    event.preventDefault();
    togglePasswordInput(togglePasswordBtn);
    return;
  }


  const confirmLink = event.target.closest('[data-action="confirm-navigation"]');
  if (confirmLink) {
    const message = confirmLink.dataset.confirmMessage || "Видалити дане поле?";
    if (!window.confirm(message)) {
      event.preventDefault();
    }
    return;
  }

  const alertBtn = event.target.closest('[data-action="alert"]');
  if (alertBtn) {
    event.preventDefault();
    const message = alertBtn.dataset.alertMessage || "Дію заборонено.";
    window.alert(message);
  }
});

window.addEventListener("popstate", (event) => {
  restoreToggleStateFromHistory(event.state);
});

document.addEventListener("DOMContentLoaded", () => {
  attachPasswordGenerators();
  syncCabinetSelectedTags();
  initCabinetHighlight();
  initIconButtons();
  initStatisticsFilters();
  restoreToggleStateFromHistory(history.state);
});