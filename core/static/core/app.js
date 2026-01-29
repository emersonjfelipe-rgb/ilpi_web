// ===== UX helpers =====

// Toast simples
function showToast(msg, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast-app toast-${type}`;
  toast.innerText = msg;
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add("show"), 50);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Confirmação antes de excluir
function confirmDelete(msg) {
  return confirm(msg || "Tem certeza que deseja excluir?");
}

// Manter aba ativa
document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (!tab) return;

  const btn = document.querySelector(`[data-bs-target="#tab-${tab}"]`);
  if (btn) btn.click();
});
