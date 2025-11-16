let lastOutputCollapsed = false;
let restoreTargetFile = null;
let restoreTargetName = null;

function toggleLastOutput() {
  const body = document.getElementById("lastOutputBody");
  const toggle = document.getElementById("lastOutputToggle");
  lastOutputCollapsed = !lastOutputCollapsed;
  if (lastOutputCollapsed) {
    body.style.display = "none";
    toggle.textContent = "▶";
  } else {
    body.style.display = "block";
    toggle.textContent = "▼";
  }
}

function updateLastOutput(message) {
  const box = document.getElementById("lastOutputContent");
  const ts = new Date().toLocaleString();
  box.textContent = `[${ts}]\n${message}`;
  const body = document.getElementById("lastOutputBody");
  body.scrollTop = body.scrollHeight;
}

// -------- System & status --------

async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const sys = data.system || {};
    const drive = data.drive || {};
    const upd = data.update || {};

    const systemEl = document.getElementById("systemStatusContainer");
    const timeEl = document.getElementById("statusTime");

    const frigateIcon = sys.frigate_ok
      ? '<span class="badge badge-green">Frigate ✓</span>'
      : '<span class="badge badge-red">Frigate ✖</span>';

    const coralIcon = sys.coral_ok
      ? '<span class="badge badge-green">Coral ✓</span>'
      : '<span class="badge badge-red">Coral ✖</span>';

    let driveBadge = "";
    if (!drive.enabled) {
      driveBadge = '<span class="badge badge-grey">Drive: Off</span>';
    } else if (!drive.configured) {
      driveBadge = '<span class="badge badge-yellow">Drive: Not configured</span>';
    } else {
      driveBadge = '<span class="badge badge-green">Drive: Connected</span>';
    }

    let updateBadge = "";
    if (upd.available) {
      updateBadge = '<span class="badge badge-yellow">Update available</span>';
    } else {
      updateBadge = '<span class="badge badge-green">Up to date</span>';
    }

    const restartBadge = sys.restart_required
      ? '<span class="badge badge-yellow">Restart recommended</span>'
      : "";

    systemEl.innerHTML = `
      <div class="system-row">
        <span class="system-label">Hostname</span>
        <span class="system-value">${sys.hostname || "-"}</span>
      </div>
      <div class="system-row">
        <span class="system-label">OS</span>
        <span class="system-value">${sys.os || "-"}</span>
      </div>
      <div class="system-row">
        <span class="system-label">Frigate</span>
        <span class="system-value">${frigateIcon}</span>
      </div>
      <div class="system-row">
        <span class="system-label">Coral</span>
        <span class="system-value">${coralIcon}</span>
      </div>
      <div class="system-row">
        <span class="system-label">Google Drive</span>
        <span class="system-value">${driveBadge}</span>
      </div>
      <div class="system-row">
        <span class="system-label">Updates</span>
        <span class="system-value">${updateBadge}</span>
      </div>
      <div class="system-row">
        <span class="system-label">Status</span>
        <span class="system-value">${restartBadge || "-"}</span>
      </div>
    `;

    timeEl.textContent = "Updated: " + (data.timestamp || "");

    // Sync header toggle with current Drive enabled state
    const toggle = document.getElementById("gdriveToggle");
    if (toggle) {
      toggle.checked = !!drive.enabled;
    }
  } catch (e) {
    console.error(e);
    document.getElementById("systemStatusContainer").innerHTML =
      "<span class='error'>Failed to load system status</span>";
  }
}

// -------- Backups --------

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return v.toFixed(1) + " " + units[i];
}

async function loadBackups() {
  try {
    const res = await fetch("/api/backups");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const files = data.files || [];
    const list = document.getElementById("backupList");

    if (!files.length) {
      list.innerHTML = '<div style="padding:0.7rem;"><i>No backups found</i></div>';
      return;
    }

    list.innerHTML = files
      .map((b) => {
        const driveField =
          b.drive === "na"
            ? "N/A"
            : b.drive
            ? "✓"
            : "✖";
        const localField = b.local ? "✓" : "✖";

        return `
          <div class="backup-row">
            <div class="backup-icon">💾</div>
            <div class="backup-main">
              <div class="backup-title-line">
                <span class="backup-name">${b.name || b.filename}</span>
                <span class="backup-date">${b.timestamp || ""}</span>
              </div>
              <div class="backup-meta">
                <span><span class="meta-label">File:</span> <span class="meta-value">${b.filename}</span></span>
                <span><span class="meta-label">Size:</span> <span class="meta-value">${formatSize(b.size_bytes)}</span></span>
                <span><span class="meta-label">Local:</span> <span class="meta-value">${localField}</span></span>
                <span><span class="meta-label">Drive:</span> <span class="meta-value">${driveField}</span></span>
              </div>
            </div>
            <div class="backup-actions">
              <button class="icon-button" title="Restore" onclick="openRestoreModal('${b.filename}', '${b.name || b.filename}')">
                ⟳
              </button>
              <button class="icon-button" title="Download" onclick="downloadBackup('${b.filename}')">
                ⬇
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  } catch (e) {
    console.error("loadBackups failed", e);
    document.getElementById("backupList").innerHTML =
      '<div style="padding:0.7rem;" class="error">Failed to load backups</div>';
  }
}

async function runBackup() {
  const status = document.getElementById("backupStatus");
  status.textContent = "Running backup...";
  updateLastOutput("Backup started...");
  try {
    const res = await fetch("/api/backup/run", { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const msg = data.message || data.error || "Backup failed.";
      status.textContent = "❌ " + msg;
      updateLastOutput(msg);
      return;
    }
    status.textContent = "✅ Backup complete!";
    updateLastOutput(data.message || "Backup completed successfully.");
    loadBackups();
  } catch (e) {
    status.textContent = "❌ Backup failed";
    updateLastOutput("Backup failed: " + e);
    console.error(e);
  }
}

function downloadBackup(filename) {
  updateLastOutput("Downloading backup: " + filename);
  window.open("/api/backups/download?file=" + encodeURIComponent(filename), "_blank");
}

// -------- System actions --------

async function runSystemAction(action) {
  updateLastOutput("System action requested: " + action);
  let endpoint = "";
  if (action === "update_os") endpoint = "/api/system/update_os";
  else if (action === "restart_frigate") endpoint = "/api/system/restart_frigate";
  else if (action === "reboot") endpoint = "/api/system/reboot";
  else return;

  try {
    const res = await fetch(endpoint, { method: "POST" });
    const data = await res.json();
    const msg = data.message || (data.ok ? "Action completed." : "Action failed.");
    updateLastOutput(msg);
    loadStatus();
  } catch (e) {
    const msg = "Action failed: " + e;
    updateLastOutput(msg);
    console.error(e);
  }
}

// -------- Init --------

loadStatus();
loadBackups();

// Check system status every 5 minutes
setInterval(loadStatus, 300000);

// Refresh backups list every 5 minutes
setInterval(loadBackups, 300000);
