// -------- Restore modal --------

function openRestoreModal(filename, name) {
  restoreTargetFile = filename;
  restoreTargetName = name;
  const modal = document.getElementById("restoreModal");
  const body = document.getElementById("restoreModalBody");
  body.innerHTML = `
    <p>You are about to restore backup:</p>
    <p><strong>${name}</strong></p>
    <p style="font-size:0.85rem;color:#ccc;">File: ${filename}</p>
    <p style="margin-top:0.6rem;font-size:0.85rem;color:#f3c969;">
      ⚠ This will overwrite the current configuration.
      Frigate should be restarted after the restore is complete.
    </p>
  `;
  modal.style.display = "flex";
}

function closeRestoreModal() {
  restoreTargetFile = null;
  restoreTargetName = null;
  document.getElementById("restoreModal").style.display = "none";
}

async function confirmRestore() {
  if (!restoreTargetFile) {
    closeRestoreModal();
    return;
  }
  updateLastOutput("Restore requested for " + restoreTargetFile + "...");
  const status = document.getElementById("backupStatus");
  status.textContent = "Restoring " + restoreTargetFile + "...";

  try {
    const res = await fetch("/api/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: restoreTargetFile }),
    });
    const data = await res.json();
    const msg = data.message || (data.ok ? "Restore successful." : "Restore failed.");
    status.textContent = data.ok ? "✅ " + msg : "❌ " + msg;
    updateLastOutput(msg);
    closeRestoreModal();
    loadStatus();
  } catch (e) {
    const msg = "Restore error: " + e;
    status.textContent = "❌ Restore error";
    updateLastOutput(msg);
    console.error(e);
    closeRestoreModal();
  }
}

// -------- Hostname modal --------

function openHostnameModal() {
  document.getElementById("hostnameStatus").textContent = "";
  document.getElementById("hostnameInput").value = "";
  document.getElementById("hostnameModal").style.display = "flex";
}

function closeHostnameModal() {
  document.getElementById("hostnameModal").style.display = "none";
}

async function applyHostname() {
  const box = document.getElementById("hostnameInput");
  const status = document.getElementById("hostnameStatus");
  const newName = box.value.trim();

  if (!newName) {
    const msg = "Hostname cannot be empty.";
    status.textContent = msg;
    updateLastOutput(msg);
    return;
  }

  status.textContent = "Applying hostname...";
  updateLastOutput("Hostname change requested: " + newName);

  try {
    const res = await fetch("/api/system/set_hostname", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hostname: newName }),
    });

    const data = await res.json();
    const msg =
      data.message || (data.ok ? "Hostname changed." : "Hostname change failed.");

    if (data.ok) {
      status.textContent = `✅ Hostname changed to "${data.hostname}". Reboot required.`;
      status.style.color = "#ffcc00";
    } else {
      status.textContent = `❌ Failed: ${data.error || "Unknown error"}`;
      status.style.color = "#ff5555";
    }
    updateLastOutput(msg);
    loadStatus();
  } catch (e) {
    const msg = "Error setting hostname: " + e;
    status.textContent = "❌ Error setting hostname.";
    status.style.color = "#ff5555";
    updateLastOutput(msg);
    console.error(e);
  }
}

// -------- Update modal --------

function openUpdateModal() {
  document.getElementById("updateModalBody").textContent = "Loading...";
  document.getElementById("updateModal").style.display = "flex";
  loadUpdateModal();
}

function closeUpdateModal() {
  document.getElementById("updateModal").style.display = "none";
}

async function loadUpdateModal() {
  try {
    const res = await fetch("/api/update/status");
    const data = await res.json();
    const body = document.getElementById("updateModalBody");

    if (!data.ok) {
      body.innerHTML = `<p class="error">Update check failed: ${data.error || "Unknown error"}</p>`;
      return;
    }

    body.innerHTML = `
      <p><strong>Channel:</strong> ${data.channel || "-"}</p>
      <p><strong>Current version:</strong> ${data.local_version || "unknown"}</p>
      <p><strong>Latest version:</strong> ${data.remote_version || "unknown"}</p>
      <p><strong>Last checked:</strong> ${data.checked_at || "-"}</p>
      <p style="margin-top:0.6rem;font-size:0.85rem;color:#aaa;">
        Downloading the latest update stores a ZIP under <code>/data/updates</code>.<br/>
        Apply updates on the host using your <code>update.sh</code> script.
      </p>
    `;
  } catch (e) {
    document.getElementById("updateModalBody").innerHTML =
      '<p class="error">Error loading update status.</p>';
    console.error(e);
  }
}

async function downloadUpdate() {
  updateLastOutput("Downloading latest update package...");
  try {
    const res = await fetch("/api/update/download", { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      updateLastOutput(data.message || "Update download failed.");
    } else {
      updateLastOutput(data.message || "Update package downloaded.");
    }
  } catch (e) {
    updateLastOutput("Update download error: " + e);
    console.error(e);
  }
}
