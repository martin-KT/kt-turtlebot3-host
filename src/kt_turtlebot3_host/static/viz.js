(function () {
  const canvas = document.getElementById("viz");
  const hud = document.getElementById("hud");
  const ctx = canvas.getContext("2d");
  const imuCanvas = document.getElementById("imu-traces");
  const imuCtx = imuCanvas.getContext("2d");
  const imuLegend = document.getElementById("imu-legend");
  const batteryCard = document.getElementById("battery-card");
  const batteryBody = document.getElementById("battery-body");
  const jointsBody = document.getElementById("joints-body");
  const sensorBody = document.getElementById("sensor-body");
  const sidebar = document.getElementById("sidebar");
  const linearSlider = document.getElementById("linear-slider");
  const angularSlider = document.getElementById("angular-slider");
  const linearVal = document.getElementById("linear-val");
  const angularVal = document.getElementById("angular-val");

  const TRACE_DEFS = [
    { key: "acc_x", label: "acc.x", unit: "m/s²", color: "#ef5350", group: "acc" },
    { key: "acc_y", label: "acc.y", unit: "m/s²", color: "#ffca28", group: "acc" },
    { key: "acc_z", label: "acc.z", unit: "m/s²", color: "#66bb6a", group: "acc" },
    { key: "gyro_x", label: "gyro.x", unit: "rad/s", color: "#42a5f5", group: "gyro" },
    { key: "gyro_y", label: "gyro.y", unit: "rad/s", color: "#ab47bc", group: "gyro" },
    { key: "gyro_z", label: "gyro.z", unit: "rad/s", color: "#26c6da", group: "gyro" },
  ];

  let config = {
    max_range_m: 3.5,
    robot_icon_radius_m: 0.15,
    base_frame: "base_link",
    sidebar_width_percent: 25,
    max_linear_m_s: 0.22,
    max_angular_rad_s: 2.84,
    imu_plot_window_s: 5.0,
  };

  let cmdLinear = 0;
  let cmdAngular = 0;
  let cmdVelWs = null;

  function applySidebarWidth() {
    const pct = Number(config.sidebar_width_percent);
    const w = Number.isFinite(pct) ? pct : 25;
    sidebar.style.width = `${w}%`;
  }

  function applyVelSliderBounds() {
    const maxLin = Number(config.max_linear_m_s) || 0.22;
    const maxAng = Number(config.max_angular_rad_s) || 2.84;
    linearSlider.min = String(-maxLin);
    linearSlider.max = String(maxLin);
    linearSlider.step = String(Math.max(0.001, maxLin / 50));
    angularSlider.min = String(-maxAng);
    angularSlider.max = String(maxAng);
    angularSlider.step = String(Math.max(0.01, maxAng / 50));
  }

  function formatVel(v, digits) {
    return Number(v).toFixed(digits);
  }

  function syncVelUi() {
    linearSlider.value = String(cmdLinear);
    angularSlider.value = String(cmdAngular);
    linearVal.textContent = formatVel(cmdLinear, 3);
    angularVal.textContent = formatVel(cmdAngular, 3);
  }

  function clampCmd(linear, angular) {
    const maxLin = Number(config.max_linear_m_s) || 0.22;
    const maxAng = Number(config.max_angular_rad_s) || 2.84;
    return {
      linear_x: Math.min(maxLin, Math.max(-maxLin, linear)),
      angular_z: Math.min(maxAng, Math.max(-maxAng, angular)),
    };
  }

  function sendCmdVel() {
    const body = clampCmd(cmdLinear, cmdAngular);
    cmdLinear = body.linear_x;
    cmdAngular = body.angular_z;
    syncVelUi();
    const payload = JSON.stringify(body);
    if (cmdVelWs && cmdVelWs.readyState === WebSocket.OPEN) {
      cmdVelWs.send(payload);
      return;
    }
    fetch("/cmd_vel.json", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
    }).catch(() => {});
  }

  function setCmdVelFromSliders() {
    cmdLinear = Number(linearSlider.value);
    cmdAngular = Number(angularSlider.value);
    syncVelUi();
    sendCmdVel();
  }

  function nudgeCmdVel(deltaLinear, deltaAngular) {
    cmdLinear += deltaLinear;
    cmdAngular += deltaAngular;
    const c = clampCmd(cmdLinear, cmdAngular);
    cmdLinear = c.linear_x;
    cmdAngular = c.angular_z;
    syncVelUi();
    sendCmdVel();
  }

  linearSlider.addEventListener("input", setCmdVelFromSliders);
  angularSlider.addEventListener("input", setCmdVelFromSliders);

  document.addEventListener("keydown", (ev) => {
    if (ev.target && (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA")) {
      return;
    }
    const fine = ev.shiftKey ? 0.25 : 1;
    const dLin = (Number(config.max_linear_m_s) || 0.22) * 0.05 * fine;
    const dAng = (Number(config.max_angular_rad_s) || 2.84) * 0.05 * fine;
    let handled = false;
    switch (ev.key) {
      case "ArrowUp":
      case "w":
      case "W":
        nudgeCmdVel(dLin, 0);
        handled = true;
        break;
      case "ArrowDown":
      case "s":
      case "S":
        nudgeCmdVel(-dLin, 0);
        handled = true;
        break;
      case "ArrowLeft":
      case "a":
      case "A":
        nudgeCmdVel(0, dAng);
        handled = true;
        break;
      case "ArrowRight":
      case "d":
      case "D":
        nudgeCmdVel(0, -dAng);
        handled = true;
        break;
      case " ":
        cmdLinear = 0;
        cmdAngular = 0;
        syncVelUi();
        sendCmdVel();
        handled = true;
        break;
      default:
        break;
    }
    if (handled) {
      ev.preventDefault();
    }
  });

  class ImuTraceBuffer {
    constructor(windowS, maxSamples) {
      this.windowMs = windowS * 1000;
      this.maxSamples = maxSamples;
      this.samples = [];
    }

    pushFromTelemetry(telemetry) {
      const imu = telemetry && telemetry.imu;
      if (!imu) {
        return;
      }
      const t = performance.now();
      const acc = imu.acc || {};
      const gyro = imu.gyro || {};
      function axis(vec, key) {
        const v = Number(vec[key]);
        return Number.isFinite(v) ? v : null;
      }
      this.samples.push({
        t,
        acc_x: axis(acc, "x"),
        acc_y: axis(acc, "y"),
        acc_z: axis(acc, "z"),
        gyro_x: axis(gyro, "x"),
        gyro_y: axis(gyro, "y"),
        gyro_z: axis(gyro, "z"),
      });
      const cutoff = t - this.windowMs;
      while (this.samples.length > this.maxSamples || (this.samples.length && this.samples[0].t < cutoff)) {
        this.samples.shift();
      }
    }

    latestValues() {
      if (!this.samples.length) {
        return {};
      }
      return this.samples[this.samples.length - 1];
    }
  }

  let imuBuffer = new ImuTraceBuffer(config.imu_plot_window_s || 5, 300);
  let imuRedrawScheduled = false;
  let lastImuDrawMs = 0;

  function scheduleImuRedraw() {
    if (imuRedrawScheduled) {
      return;
    }
    imuRedrawScheduled = true;
    requestAnimationFrame(() => {
      imuRedrawScheduled = false;
      const now = performance.now();
      if (now - lastImuDrawMs < 50) {
        scheduleImuRedraw();
        return;
      }
      lastImuDrawMs = now;
      drawImuPlot(imuCtx, imuBuffer, config);
    });
  }

  function groupMinMax(buffer, group) {
    const keys = TRACE_DEFS.filter((d) => d.group === group).map((d) => d.key);
    let min = Infinity;
    let max = -Infinity;
    for (const s of buffer.samples) {
      for (const k of keys) {
        const v = s[k];
        if (v === null || !Number.isFinite(v)) {
          continue;
        }
        min = Math.min(min, v);
        max = Math.max(max, v);
      }
    }
    if (!Number.isFinite(min)) {
      return { min: -1, max: 1 };
    }
    if (min === max) {
      min -= 0.5;
      max += 0.5;
    }
    const pad = (max - min) * 0.08 || 0.1;
    return { min: min - pad, max: max + pad };
  }

  function drawImuPlot(context, buffer, cfg) {
    const dpr = window.devicePixelRatio || 1;
    const rect = imuCanvas.getBoundingClientRect();
    imuCanvas.width = Math.floor(rect.width * dpr);
    imuCanvas.height = Math.floor(rect.height * dpr);
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    const w = rect.width;
    const h = rect.height;
    context.fillStyle = "#0e0e12";
    context.fillRect(0, 0, w, h);

    const padL = 28;
    const padR = 28;
    const padT = 6;
    const padB = 14;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;

    if (!buffer.samples.length) {
      context.fillStyle = "#555";
      context.font = "11px system-ui";
      context.textAlign = "center";
      context.fillText("No IMU", w / 2, h / 2);
      imuLegend.textContent = "";
      return;
    }

    const t0 = buffer.samples[0].t;
    const t1 = buffer.samples[buffer.samples.length - 1].t;
    const tSpan = Math.max(t1 - t0, 1);
    const accScale = groupMinMax(buffer, "acc");
    const gyroScale = groupMinMax(buffer, "gyro");

    context.strokeStyle = "#2a2a32";
    context.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padT + (plotH * i) / 4;
      context.beginPath();
      context.moveTo(padL, y);
      context.lineTo(padL + plotW, y);
      context.stroke();
    }

    context.fillStyle = "#666";
    context.font = "9px ui-monospace, monospace";
    context.textAlign = "right";
    context.fillText("acc", padL - 4, padT + 8);
    context.textAlign = "left";
    context.fillText("ω", padL + plotW + 4, padT + 8);

    for (const def of TRACE_DEFS) {
      const scale = def.group === "acc" ? accScale : gyroScale;
      context.strokeStyle = def.color;
      context.lineWidth = 1.25;
      context.beginPath();
      let started = false;
      for (const s of buffer.samples) {
        const v = s[def.key];
        if (v === null || !Number.isFinite(v)) {
          started = false;
          continue;
        }
        const x = padL + ((s.t - t0) / tSpan) * plotW;
        const yn = (v - scale.min) / (scale.max - scale.min);
        const y = padT + plotH * (1 - yn);
        if (!started) {
          context.moveTo(x, y);
          started = true;
        } else {
          context.lineTo(x, y);
        }
      }
      context.stroke();
    }

    const latest = buffer.latestValues();
    imuLegend.innerHTML = TRACE_DEFS.map((def) => {
      const v = latest[def.key];
      const txt = v === null || !Number.isFinite(v) ? "—" : v.toFixed(3);
      return `<span style="color:${def.color}">${def.label}=${txt}</span>`;
    }).join("  ");
  }

  function renderSidebar(telemetry) {
    if (!telemetry) {
      return;
    }
    if (telemetry.imu) {
      imuBuffer.pushFromTelemetry(telemetry);
      scheduleImuRedraw();
    }

    const bat = telemetry.battery;
    const staleBat = telemetry.stale && telemetry.stale.battery;
    batteryCard.classList.toggle("stale", !!staleBat || !bat);
    if (!bat) {
      batteryBody.textContent = "No data";
    } else {
      const pct = Math.min(100, Math.max(0, Number(bat.percentage) || 0));
      const status = bat.supply_status || "—";
      const cur =
        bat.current !== undefined ? `  I=${Number(bat.current).toFixed(2)} A` : "";
      batteryBody.innerHTML =
        `<div class="battery-bar-wrap"><div class="battery-bar" style="width:${pct}%"></div></div>` +
        `${pct.toFixed(0)}%  ${Number(bat.voltage).toFixed(2)} V  ${status}${cur}`;
    }

    const joints = telemetry.joints;
    if (!joints || !joints.length) {
      jointsBody.textContent = "No wheel joints";
    } else {
      let html =
        '<table class="joints-table"><thead><tr><th>name</th><th>ω</th><th>pos</th></tr></thead><tbody>';
      for (const j of joints) {
        const pos =
          j.position !== undefined ? Number(j.position).toFixed(3) : "—";
        html += `<tr><td>${j.name}</td><td>${Number(j.velocity).toFixed(3)}</td><td>${pos}</td></tr>`;
      }
      html += "</tbody></table>";
      jointsBody.innerHTML = html;
    }

    const sensor = telemetry.sensor_state;
    if (!sensor) {
      sensorBody.textContent = "No data";
    } else {
      const count = sensor.count != null ? sensor.count : (sensor.elements || []).length;
      const els = JSON.stringify(sensor.elements || []);
      sensorBody.innerHTML =
        `<div>${count} element(s)</div>` +
        `<details class="sensor-raw"><summary>Raw elements</summary><pre>${els}</pre></details>`;
    }
  }

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  window.addEventListener("resize", () => {
    resize();
    draw(lastPayload);
    scheduleImuRedraw();
  });

  function worldToScreen(x, y, cx, cy, ppm) {
    return { sx: cx + y * ppm, sy: cy - x * ppm };
  }

  function colourForIntensity(intensity, range, maxRange, scale) {
    if (!Number.isFinite(intensity)) {
      const u = Math.min(1, range / maxRange);
      const r = Math.floor(40 + 215 * u);
      return `rgb(${r},${120},${255 - Math.floor(180 * u)})`;
    }
    const t = Math.min(1, Math.max(0, intensity / scale));
    const r = Math.floor(80 + 175 * t);
    const g = Math.floor(120 + 80 * (1 - t));
    const b = Math.floor(200 * (1 - t));
    return `rgb(${r},${g},${b})`;
  }

  function intensityScale(points) {
    let max = 0;
    for (const pt of points) {
      const value = Number(pt[2]);
      if (Number.isFinite(value) && value > max) {
        max = value;
      }
    }
    if (max <= 0) {
      return 1;
    }
    return Math.min(255, max);
  }

  let lastPayload = null;
  let lastScanUnixNs = null;
  let pollTimer = null;
  let wsOpen = false;

  function drawGrid(cx, cy, ppm, maxRange) {
    ctx.strokeStyle = "#2a2a32";
    ctx.lineWidth = 1;
    const rings = Math.ceil(maxRange);
    for (let m = 1; m <= rings; m++) {
      ctx.beginPath();
      ctx.arc(cx, cy, m * ppm, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.strokeStyle = "#3a3a44";
    ctx.beginPath();
    ctx.moveTo(cx - maxRange * ppm, cy);
    ctx.lineTo(cx + maxRange * ppm, cy);
    ctx.moveTo(cx, cy - maxRange * ppm);
    ctx.lineTo(cx, cy + maxRange * ppm);
    ctx.stroke();
  }

  // TurtleBot3 Waffle Pi collision sizes, metres, base_link.
  // turtlebot3_waffle_pi.urdf. +X is up the screen.
  const WAFFLE_PI = {
    base: { x: -0.064, y: 0, length: 0.266, width: 0.266 },
    wheel: { x: 0, y: 0.144, length: 0.066, width: 0.018 },
    caster: { x: -0.177, y: 0.064, length: 0.03, width: 0.009 },
    lidar: { x: -0.049, y: 0, radius: 0.055 },
    camera: { x: 0.078, y: 0, length: 0.015, width: 0.03 },
  };

  function fillBox(cx, cy, ppm, x, y, length, width) {
    const left = cx + (y - width / 2) * ppm;
    const top = cy - (x + length / 2) * ppm;
    ctx.fillRect(left, top, width * ppm, length * ppm);
  }

  function drawRobot(cx, cy, ppm, radiusM) {
    void radiusM;
    ctx.fillStyle = "#3a3a44";
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.wheel.x, WAFFLE_PI.wheel.y,
      WAFFLE_PI.wheel.length, WAFFLE_PI.wheel.width,
    );
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.wheel.x, -WAFFLE_PI.wheel.y,
      WAFFLE_PI.wheel.length, WAFFLE_PI.wheel.width,
    );
    ctx.fillStyle = "#4a4a55";
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.base.x, WAFFLE_PI.base.y,
      WAFFLE_PI.base.length, WAFFLE_PI.base.width,
    );
    ctx.fillStyle = "#2a2a32";
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.caster.x, WAFFLE_PI.caster.y,
      WAFFLE_PI.caster.length, WAFFLE_PI.caster.width,
    );
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.caster.x, -WAFFLE_PI.caster.y,
      WAFFLE_PI.caster.length, WAFFLE_PI.caster.width,
    );
    const lidar = worldToScreen(WAFFLE_PI.lidar.x, WAFFLE_PI.lidar.y, cx, cy, ppm);
    ctx.fillStyle = "#5c5c68";
    ctx.beginPath();
    ctx.arc(lidar.sx, lidar.sy, WAFFLE_PI.lidar.radius * ppm, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#c4a574";
    fillBox(
      cx, cy, ppm,
      WAFFLE_PI.camera.x, WAFFLE_PI.camera.y,
      WAFFLE_PI.camera.length, WAFFLE_PI.camera.width,
    );
    const nose = worldToScreen(0.12, 0, cx, cy, ppm);
    const origin = worldToScreen(0, 0, cx, cy, ppm);
    ctx.strokeStyle = "#81c784";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(origin.sx, origin.sy);
    ctx.lineTo(nose.sx, nose.sy);
    ctx.stroke();
  }

  function draw(payload) {
    resize();
    const w = canvas.getBoundingClientRect().width;
    const h = canvas.getBoundingClientRect().height;
    ctx.fillStyle = "#121216";
    ctx.fillRect(0, 0, w, h);

    const maxRange = config.max_range_m || 3.5;
    const ppm = (Math.min(w, h) * 0.45) / maxRange;
    const cx = w / 2;
    const cy = h / 2;

    drawGrid(cx, cy, ppm, maxRange);
    drawRobot(cx, cy, ppm, config.robot_icon_radius_m || 0.15);

    if (payload && payload.points) {
      const scale = intensityScale(payload.points);
      for (const pt of payload.points) {
        const x = pt[0];
        const y = pt[1];
        const intensity = Number(pt[2]);
        const range = Math.hypot(x, y);
        const { sx, sy } = worldToScreen(x, y, cx, cy, ppm);
        ctx.fillStyle = colourForIntensity(intensity, range, maxRange, scale);
        ctx.fillRect(sx, sy, 1, 1);
      }
    }
  }

  function updateHud(payload, transportHint) {
    if (!payload) {
      hud.textContent = transportHint || "Waiting for scan…";
      return;
    }
    const n = payload.points ? payload.points.length : 0;
    const via = transportHint ? `  via=${transportHint}` : "";
    let extra = "";
    const tel = payload.telemetry;
    if (tel && tel.battery && tel.battery.percentage != null) {
      extra += `  bat=${Number(tel.battery.percentage).toFixed(0)}%`;
    }
    if (tel && tel.imu && tel.imu.gyro) {
      extra += `  gz=${Number(tel.imu.gyro.z).toFixed(3)}`;
    }
    hud.textContent =
      `frame=${payload.frame || config.base_frame}  link=${payload.link || "—"}  ` +
      `scan_unix_ns=${payload.scan_unix_ns}  beams=${n}${extra}${via}`;
  }

  function mergePayload(incoming) {
    if (!incoming) {
      return lastPayload;
    }
    const base = lastPayload ? { ...lastPayload } : {};
    for (const [key, val] of Object.entries(incoming)) {
      if (key === "telemetry" && base.telemetry && val) {
        base.telemetry = { ...base.telemetry, ...val };
      } else {
        base[key] = val;
      }
    }
    return base;
  }

  function onPayload(payload, transportHint) {
    const merged = mergePayload(payload);
    const tel = (payload && payload.telemetry) || (merged && merged.telemetry);
    if (tel) {
      renderSidebar(tel);
    }
    const ns = merged && merged.scan_unix_ns != null ? merged.scan_unix_ns : 0;
    const scanChanged = ns !== 0 && ns !== lastScanUnixNs;
    const hadNoPoints = !lastPayload || !lastPayload.points || !lastPayload.points.length;
    if (scanChanged || hadNoPoints) {
      if (ns !== 0) {
        lastScanUnixNs = ns;
      }
      lastPayload = merged;
      draw(merged);
    } else {
      lastPayload = merged;
    }
    updateHud(lastPayload, transportHint);
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function pollScanJson() {
    try {
      const response = await fetch("/scan.json", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      onPayload(payload, wsOpen ? null : "poll");
    } catch (_) {
      /* ignore transient fetch errors */
    }
  }

  function startPolling() {
    if (pollTimer !== null) {
      return;
    }
    void pollScanJson();
    pollTimer = setInterval(pollScanJson, 200);
  }

  fetch("/config.json")
    .then((r) => r.json())
    .then((c) => {
      config = { ...config, ...c };
      applySidebarWidth();
      applyVelSliderBounds();
      syncVelUi();
      sendCmdVel();
      imuBuffer = new ImuTraceBuffer(config.imu_plot_window_s || 5, 300);
      draw(null);
      scheduleImuRedraw();
      void pollScanJson();
    })
    .catch(() => {
      applySidebarWidth();
      applyVelSliderBounds();
      syncVelUi();
      draw(null);
    });

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${proto}//${location.host}/ws`;

  function showCameraFrame(msg) {
    const img = document.getElementById("camera");
    if (!img || !msg.jpeg_base64) {
      return;
    }
    img.src = "data:image/jpeg;base64," + msg.jpeg_base64;
  }

  function connect() {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      wsOpen = true;
      cmdVelWs = ws;
      sendCmdVel();
      startPolling();
      if (!lastPayload) {
        hud.textContent = "WebSocket connected — waiting for scan…";
      }
    };
    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch (_) {
        return;
      }
      if (msg && msg.type === "camera_jpeg") {
        showCameraFrame(msg);
        return;
      }
      onPayload(msg, "ws");
    };
    ws.onclose = () => {
      wsOpen = false;
      if (cmdVelWs === ws) {
        cmdVelWs = null;
      }
      if (lastPayload) {
        updateHud(lastPayload, "poll");
        hud.textContent += "  (WebSocket closed — polling /scan.json…)";
      } else {
        hud.textContent = "WebSocket closed — polling /scan.json…";
      }
      startPolling();
      setTimeout(connect, 1500);
    };
    ws.onerror = () => ws.close();
  }

  startPolling();
  connect();
})();
