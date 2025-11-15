// -------- Google Drive --------

async function toggleDriveEnabled() {
  const toggle = document.getElementById("gdriveToggle");
  const enabled = toggle && toggle.checked;
  updateLastOutput("Toggling Google Drive to " + (enabled ? "ON" : "OFF"));
  try {
    const res = await fetch("/api/gdrive/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const data = await res.json();
    const msg =
      data.message ||
      (data.ok ? "Drive config updated." : "Failed to update Drive config.");
    updateLastOutput(msg);
    loadStatus();
    loadBackups();
  } catch (e) {
    console.error(e);
    updateLastOutput("Drive toggle failed: " + e);
  }
}

function openDriveModal() {
  document.getElementById("driveModalStatus").textContent = "";
  document.getElementById("driveTokenText").value = "";
  document.getElementById("driveTokenFile").value = "";
  document.getElementById("driveModal").style.display = "flex";
}

function closeDriveModal() {
  document.getElementById("driveModal").style.display = "none";
}

async function saveDriveConfig() {
  const tokenText = document.getElementById("driveTokenText").value.trim();
  const statusEl = document.getElementById("driveModalStatus");
  statusEl.textContent = "Saving Drive configuration...";
  updateLastOutput("Saving Google Drive configuration...");

  try {
    if (tokenText) {
      // Save token & enable
      const res = await fetch("/api/gdrive/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: true, token_json: tokenText }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        statusEl.textContent = "❌ " + (data.message || "Failed to save config.");
        updateLastOutput(data.message || "Drive config failed.");
      } else {
        statusEl.textContent = "✅ " + (data.message || "Drive configuration updated.");
        updateLastOutput(data.message || "Drive configuration updated.");
      }
    } else {
      const fileInput = document.getElementById("driveTokenFile");
      if (fileInput.files.length > 0) {
        const fd = new FormData();
        fd.append("file", fileInput.files[0]);
        const resUpload = await fetch("/api/gdrive/upload_token", {
          method: "POST",
          body: fd,
        });
        const dataUpload = await resUpload.json();
        if (!resUpload.ok || !dataUpload.ok) {
          statusEl.textContent = "❌ " + (dataUpload.message || "Failed to upload token.");
          updateLastOutput(dataUpload.message || "Token upload failed.");
        } else {
          // After successful upload, enable Drive
          const resEnable = await fetch("/api/gdrive/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: true }),
          });
          const dataEnable = await resEnable.json();
          if (!resEnable.ok || !dataEnable.ok) {
            statusEl.textContent =
              "✅ Token uploaded, but enabling failed: " +
              (dataEnable.message || "Unknown error");
          } else {
            statusEl.textContent = "✅ Token uploaded and Drive enabled.";
          }
          updateLastOutput(
            dataUpload.message || "Token uploaded, Drive enable requested."
          );
        }
      } else {
        // No token, no file – just enable using existing config
        const res = await fetch("/api/gdrive/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: true }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          statusEl.textContent = "❌ " + (data.message || "Failed to enable Drive.");
          updateLastOutput(data.message || "Drive enable failed.");
        } else {
          statusEl.textContent = "✅ Drive enabled.";
          updateLastOutput(data.message || "Drive enabled.");
        }
      }
    }

    loadStatus();
    loadBackups();
  } catch (e) {
    statusEl.textContent = "❌ Error saving Drive config.";
    updateLastOutput("Drive config error: " + e);
    console.error(e);
  }
}
