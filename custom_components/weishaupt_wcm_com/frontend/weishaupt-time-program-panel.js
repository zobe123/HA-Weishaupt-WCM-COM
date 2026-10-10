const DOMAIN = "weishaupt_wcm_com";
const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const STRINGS = {
  en: {
    title: "Weishaupt time programs", loading_info: "Loading weekly programs", querying: "Querying WCM-COM …",
    load_failed: "Loading failed: {error}", schedule_failed: "The time program could not be loaded: {error}",
    heating_program: "HC{circuit} · Heating program {number}{active}", active: " · active", hot_water: "Hot water",
    circulation: "Circulation", circulation_missing: "Circulation · not detected", time_program: "Time program",
    read_only_title: "Read only:", read_only: "Enable writes in the integration options to apply changes.",
    optional: "Optional", show_circulation: "Show circulation", loading_schedule: "Loading weekly program …",
    no_schedule: "No weekly program available.", remove_window: "Remove time window", no_window: "No enabled time window",
    template: "Template", copy_weekdays: "to Mon–Fri", copy_weekend: "to Sat–Sun", copy_all: "to all days",
    discard: "Discard", apply: "Apply", apply_days: "Apply {count} day(s)", discard_confirm: "Discard unapplied changes?",
    pending: "Unapplied changes", copied: "{day} was copied", max_windows: "{day}: no more than three time windows",
    end_after_start: "{day}: the end must be after the start", overlap: "{day}: time windows must not overlap",
    writing: "Writing and verifying changes …", write_success: "Time program applied and verified",
    write_failed: "Applying changes failed: {error}", card_description: "View and edit WCM-COM weekly programs",
    monday: "Monday", tuesday: "Tuesday", wednesday: "Wednesday", thursday: "Thursday", friday: "Friday",
    saturday: "Saturday", sunday: "Sunday",
    mode_program_1: "Program 1", mode_program_2: "Program 2", mode_program_3: "Program 3", mode_standby: "Standby",
    mode_summer: "Summer", mode_reduced: "Reduced", mode_normal: "Normal", mode_control_center: "Control center",
    mode_hot_water_program: "Hot-water program",
  },
  de: {
    title: "Weishaupt Zeitprogramme", loading_info: "Wochenprogramme werden geladen", querying: "WCM-COM wird abgefragt …",
    load_failed: "Laden fehlgeschlagen: {error}", schedule_failed: "Zeitprogramm konnte nicht geladen werden: {error}",
    heating_program: "HK{circuit} · Heizprogramm {number}{active}", active: " · aktiv", hot_water: "Warmwasser",
    circulation: "Zirkulation", circulation_missing: "Zirkulation · nicht erkannt", time_program: "Zeitprogramm",
    read_only_title: "Nur Lesen:", read_only: "Zum Übernehmen muss in den Integrationsoptionen „Schreibzugriffe erlauben“ aktiviert sein.",
    optional: "Optional", show_circulation: "Zirkulation anzeigen", loading_schedule: "Lade Wochenplan …",
    no_schedule: "Kein Wochenplan verfügbar.", remove_window: "Zeitfenster entfernen", no_window: "Keine Freigabezeit",
    template: "Vorlage", copy_weekdays: "auf Mo–Fr", copy_weekend: "auf Sa–So", copy_all: "auf alle Tage",
    discard: "Verwerfen", apply: "Übernehmen", apply_days: "{count} Tag(e) übernehmen", discard_confirm: "Nicht übernommene Änderungen verwerfen?",
    pending: "Nicht übernommene Änderungen", copied: "{day} wurde kopiert", max_windows: "{day}: maximal drei Zeitfenster",
    end_after_start: "{day}: Ende muss nach Beginn liegen", overlap: "{day}: Zeitfenster überschneiden sich",
    writing: "Änderungen werden geschrieben und geprüft …", write_success: "Zeitprogramm erfolgreich übernommen und geprüft",
    write_failed: "Übernehmen fehlgeschlagen: {error}", card_description: "WCM-COM-Wochenprogramme anzeigen und bearbeiten",
    monday: "Montag", tuesday: "Dienstag", wednesday: "Mittwoch", thursday: "Donnerstag", friday: "Freitag",
    saturday: "Samstag", sunday: "Sonntag",
    mode_program_1: "Programm 1", mode_program_2: "Programm 2", mode_program_3: "Programm 3", mode_standby: "Standby",
    mode_summer: "Sommer", mode_reduced: "Absenk", mode_normal: "Normal", mode_control_center: "Wie Leitstelle",
    mode_hot_water_program: "Warmwasserprogramm",
  },
};

class WeishauptTimeProgramPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._info = null;
    this._target = null;
    this._schedule = null;
    this._dirty = new Set();
    this._showOptional = false;
    this._busy = false;
    this._status = "";
    this._statusIsError = false;
  }

  set hass(value) {
    this._hass = value;
    if (!this._info && !this._busy) this._loadInfo();
  }

  set panel(value) {
    this._panel = value;
  }

  setConfig(config) {
    this._config = config || {};
    if (this._hass && !this._busy) this._loadInfo();
  }

  getCardSize() {
    return 9;
  }

  _t(key, values = {}) {
    const language = (this._hass?.language || "en").split("-")[0];
    let text = (STRINGS[language] || STRINGS.en)[key] || STRINGS.en[key] || key;
    for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, value);
    return text;
  }

  connectedCallback() {
    this._render();
  }

  async _loadInfo() {
    if (!this._hass) return;
    this._busy = true;
    this._render();
    try {
      const request = {
        type: `${DOMAIN}/time_programs/info`,
      };
      if (this._config?.entry_id) request.entry_id = this._config.entry_id;
      this._info = await this._hass.callWS(request);
      const active = this._info.circuits["1"].active_program || "heating_1";
      this._target = { circuit: 1, program: active };
      await this._loadSchedule();
    } catch (error) {
      this._status = this._t("load_failed", { error: error.message || error });
      this._statusIsError = true;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _loadSchedule() {
    if (!this._hass || !this._target) return;
    this._busy = true;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: `${DOMAIN}/time_programs/get`,
        entry_id: this._info.entry_id,
        heating_circuit: this._target.circuit,
        program: this._target.program,
      });
      this._schedule = structuredClone(response.schedule);
      this._dirty.clear();
      this._status = "";
      this._statusIsError = false;
    } catch (error) {
      this._schedule = null;
      this._status = this._t("schedule_failed", { error: error.message || error });
      this._statusIsError = true;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _targets() {
    if (!this._info) return [];
    const targets = [];
    for (const circuit of [1, 2]) {
      for (let number = 1; number <= 3; number += 1) {
        const program = `heating_${number}`;
        const active = this._info.circuits[String(circuit)].active_program === program;
        targets.push({
          circuit,
          program,
          label: this._t("heating_program", {
            circuit,
            number,
            active: active ? this._t("active") : "",
          }),
        });
      }
    }
    targets.push({ circuit: 1, program: "hot_water", label: this._t("hot_water") });
    if (this._info.circulation_supported || this._showOptional) {
      targets.push({
        circuit: 1,
        program: "circulation",
        label: this._info.circulation_supported
          ? this._t("circulation")
          : this._t("circulation_missing"),
      });
    }
    return targets;
  }

  _targetKey(target) {
    return `${target.circuit}:${target.program}`;
  }

  _currentLabel() {
    return this._targets().find(
      (target) => this._targetKey(target) === this._targetKey(this._target),
    )?.label || this._t("time_program");
  }

  _modeSummary() {
    if (!this._info) return "";
    return [1, 2]
      .map((circuit) => {
        const mode = this._info.circuits[String(circuit)].mode;
        return `HK${circuit}: ${this._t(`mode_${mode}`)}`;
      })
      .join(" · ");
  }

  _gasMeterSummary() {
    const meter = this._info?.external_gas_meter;
    if (!meter) return "";
    return `${meter.name}: ${meter.state}${meter.unit ? ` ${meter.unit}` : ""}`;
  }

  _timeOptions(selected, isEnd) {
    const options = [];
    const first = isEnd ? 1 : 0;
    const last = isEnd ? 96 : 95;
    for (let quarter = first; quarter <= last; quarter += 1) {
      const hour = Math.floor(quarter / 4);
      const minute = (quarter % 4) * 15;
      const value = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
      options.push(`<option value="${value}" ${value === selected ? "selected" : ""}>${value}</option>`);
    }
    return options.join("");
  }

  _render() {
    if (!this.shadowRoot) return;
    const targets = this._targets();
    const selectedKey = this._target ? this._targetKey(this._target) : "";
    const writable = Boolean(this._info?.allow_write);
    const cardMode = this.localName === "weishaupt-time-program-card";
    const title = this._config?.title || this._t("title");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; color:var(--primary-text-color); background:var(--primary-background-color); min-height:100%; }
        * { box-sizing:border-box; }
        .page { max-width:1180px; margin:0 auto; padding:24px; }
        .page.dashboard-card { max-width:none; padding:16px; background:var(--ha-card-background, var(--card-background-color)); border-radius:var(--ha-card-border-radius, 12px); box-shadow:var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.18)); }
        .page.dashboard-card .card { box-shadow:none; padding:0; }
        .header { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; margin-bottom:18px; }
        h1 { margin:0 0 6px; font-size:28px; font-weight:500; }
        .subtle { color:var(--secondary-text-color); font-size:14px; }
        .card { background:var(--card-background-color); border-radius:12px; box-shadow:var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.18)); padding:20px; }
        .toolbar { display:flex; flex-wrap:wrap; align-items:end; gap:12px; margin-bottom:18px; }
        label { display:flex; flex-direction:column; gap:6px; color:var(--secondary-text-color); font-size:12px; }
        select, input[type=time] { color:var(--primary-text-color); background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; padding:9px 10px; font:inherit; }
        select { min-width:270px; }
        select.time-input { min-width:88px; width:auto; padding:8px; }
        button { border:0; border-radius:8px; padding:9px 14px; font:inherit; cursor:pointer; background:var(--secondary-background-color); color:var(--primary-text-color); }
        button.primary { background:var(--primary-color); color:var(--text-primary-color, white); }
        button.danger { color:var(--error-color); }
        button.icon { padding:7px 10px; min-width:36px; }
        button:disabled { opacity:.45; cursor:not-allowed; }
        .warning { margin:0 0 16px; padding:12px 14px; border-left:4px solid var(--warning-color, #ffa600); background:var(--secondary-background-color); border-radius:6px; }
        .status { margin-top:14px; min-height:20px; color:var(--secondary-text-color); }
        .status.error { color:var(--error-color); }
        .grid { display:grid; grid-template-columns:130px 1fr auto; border-top:1px solid var(--divider-color); }
        .row { display:contents; }
        .day, .windows, .actions { padding:12px 8px; border-bottom:1px solid var(--divider-color); }
        .day { font-weight:500; display:flex; align-items:center; }
        .windows { display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
        .window { display:flex; align-items:center; gap:6px; background:var(--secondary-background-color); border-radius:9px; padding:6px; }
        .actions { display:flex; align-items:center; }
        .copybar { display:flex; flex-wrap:wrap; align-items:end; gap:8px; margin:18px 0 0; }
        .copybar select { min-width:150px; }
        .footer { display:flex; justify-content:flex-end; gap:10px; margin-top:20px; }
        .spinner { opacity:.75; }
        @media (max-width:760px) {
          .page { padding:12px; }
          .header { display:block; }
          .grid { display:block; }
          .row { display:block; border-bottom:1px solid var(--divider-color); padding:10px 0; }
          .day, .windows, .actions { border:0; padding:5px 0; }
          .actions { justify-content:flex-end; }
          select { width:100%; min-width:0; }
        }
      </style>
      <div class="page ${cardMode ? "dashboard-card" : ""}">
        <div class="header">
          <div>
            <h1>${title}</h1>
            <div class="subtle">${this._info ? this._modeSummary() : this._t("loading_info")}</div>
          </div>
          <div class="subtle">${this._busy ? this._t("querying") : this._gasMeterSummary()}</div>
        </div>
        <div class="card">
          ${!writable && this._info ? `<div class="warning"><b>${this._t("read_only_title")}</b> ${this._t("read_only")}</div>` : ""}
          <div class="toolbar">
            <label>${this._t("time_program")}
              <select id="target" ${this._busy ? "disabled" : ""}>
                ${targets.map((target) => `<option value="${this._targetKey(target)}" ${this._targetKey(target) === selectedKey ? "selected" : ""}>${target.label}</option>`).join("")}
              </select>
            </label>
            ${!this._info?.circulation_supported ? `<label><span>${this._t("optional")}</span><span><input id="optional" type="checkbox" ${this._showOptional ? "checked" : ""}> ${this._t("show_circulation")}</span></label>` : ""}
          </div>
          ${this._schedule ? this._renderSchedule() : `<div class="spinner">${this._busy ? this._t("loading_schedule") : this._t("no_schedule")}</div>`}
          <div class="status ${this._statusIsError ? "error" : ""}">${this._status}</div>
        </div>
      </div>`;
    this._bindEvents();
  }

  _renderSchedule() {
    return `
      <div class="grid">
        ${DAYS.map((day) => {
          const intervals = this._schedule[day] || [];
          return `<div class="row" data-day="${day}">
            <div class="day">${this._t(day)}</div>
            <div class="windows">
              ${intervals.map((interval, slot) => `<div class="window">
                <select class="time-input" data-day="${day}" data-slot="${slot}" data-kind="start">${this._timeOptions(interval[0], false)}</select>
                <span>–</span>
                <select class="time-input" data-day="${day}" data-slot="${slot}" data-kind="end">${this._timeOptions(interval[1], true)}</select>
                <button class="icon danger remove" data-day="${day}" data-slot="${slot}" title="${this._t("remove_window")}">×</button>
              </div>`).join("")}
              ${intervals.length === 0 ? `<span class="subtle">${this._t("no_window")}</span>` : ""}
            </div>
            <div class="actions"><button class="icon add" data-day="${day}" ${intervals.length >= 3 ? "disabled" : ""}>＋</button></div>
          </div>`;
        }).join("")}
      </div>
      <div class="copybar">
        <label>${this._t("template")}
          <select id="copy-source">${DAYS.map((day) => `<option value="${day}">${this._t(day)}</option>`).join("")}</select>
        </label>
        <button class="copy" data-group="weekdays">${this._t("copy_weekdays")}</button>
        <button class="copy" data-group="weekend">${this._t("copy_weekend")}</button>
        <button class="copy" data-group="all">${this._t("copy_all")}</button>
      </div>
      <div class="footer">
        <button id="discard" ${this._dirty.size === 0 || this._busy ? "disabled" : ""}>${this._t("discard")}</button>
        <button id="apply" class="primary" ${this._dirty.size === 0 || this._busy || !this._info.allow_write ? "disabled" : ""}>${this._dirty.size ? this._t("apply_days", { count: this._dirty.size }) : this._t("apply")}</button>
      </div>`;
  }

  _bindEvents() {
    const root = this.shadowRoot;
    root.querySelector("#target")?.addEventListener("change", async (event) => {
      if (this._dirty.size && !confirm(this._t("discard_confirm"))) {
        event.target.value = this._targetKey(this._target);
        return;
      }
      const [circuit, program] = event.target.value.split(":");
      this._target = { circuit: Number(circuit), program };
      await this._loadSchedule();
    });
    root.querySelector("#optional")?.addEventListener("change", (event) => {
      this._showOptional = event.target.checked;
      this._render();
    });
    root.querySelectorAll("select.time-input").forEach((input) => {
      input.addEventListener("change", (event) => {
        const { day, slot, kind } = event.target.dataset;
        this._schedule[day][Number(slot)][kind === "start" ? 0 : 1] = event.target.value;
        this._markDirty(day);
      });
    });
    root.querySelectorAll("button.add").forEach((button) => {
      button.addEventListener("click", () => {
        const day = button.dataset.day;
        const previous = this._schedule[day].at(-1);
        const start = previous?.[1] && previous[1] < "23:45" ? previous[1] : "06:00";
        const endHour = Math.min(Number(start.slice(0, 2)) + 1, 24);
        this._schedule[day].push([start, `${String(endHour).padStart(2, "0")}:00`]);
        this._markDirty(day, true);
      });
    });
    root.querySelectorAll("button.remove").forEach((button) => {
      button.addEventListener("click", () => {
        const { day, slot } = button.dataset;
        this._schedule[day].splice(Number(slot), 1);
        this._markDirty(day, true);
      });
    });
    root.querySelectorAll("button.copy").forEach((button) => {
      button.addEventListener("click", () => this._copyDay(button.dataset.group));
    });
    root.querySelector("#discard")?.addEventListener("click", () => this._loadSchedule());
    root.querySelector("#apply")?.addEventListener("click", () => this._apply());
  }

  _markDirty(day, rerender = false) {
    this._dirty.add(day);
    this._status = this._t("pending");
    this._statusIsError = false;
    if (rerender) this._render();
    else {
      const apply = this.shadowRoot.querySelector("#apply");
      const discard = this.shadowRoot.querySelector("#discard");
      if (apply) {
        apply.disabled = !this._info.allow_write;
        apply.textContent = this._t("apply_days", { count: this._dirty.size });
      }
      if (discard) discard.disabled = false;
      const status = this.shadowRoot.querySelector(".status");
      if (status) status.textContent = this._status;
    }
  }

  _copyDay(group) {
    const source = this.shadowRoot.querySelector("#copy-source")?.value || "monday";
    const targets = group === "weekdays"
      ? DAYS.slice(0, 5)
      : group === "weekend"
        ? DAYS.slice(5)
        : DAYS;
    for (const day of targets) {
      if (day === source) continue;
      this._schedule[day] = structuredClone(this._schedule[source]);
      this._dirty.add(day);
    }
    this._status = this._t("copied", { day: this._t(source) });
    this._statusIsError = false;
    this._render();
  }

  _validatedIntervals(day) {
    const intervals = structuredClone(this._schedule[day] || [])
      .filter(([start, end]) => start && end)
      .sort((a, b) => a[0].localeCompare(b[0]));
    if (intervals.length > 3) throw new Error(this._t("max_windows", { day: this._t(day) }));
    for (let index = 0; index < intervals.length; index += 1) {
      const [start, end] = intervals[index];
      if (start >= end) throw new Error(this._t("end_after_start", { day: this._t(day) }));
      if (index && intervals[index - 1][1] > start) {
        throw new Error(this._t("overlap", { day: this._t(day) }));
      }
    }
    return intervals;
  }

  async _apply() {
    if (!this._info.allow_write || !this._dirty.size) return;
    this._busy = true;
    this._status = this._t("writing");
    this._statusIsError = false;
    this._render();
    try {
      for (const day of DAYS) {
        if (!this._dirty.has(day)) continue;
        const intervals = this._validatedIntervals(day);
        const data = {
          config_entry_id: this._info.entry_id,
          heating_circuit: this._target.circuit,
          program: this._target.program,
          day,
        };
        intervals.forEach(([start, end], index) => {
          data[`start_${index + 1}`] = start;
          data[`end_${index + 1}`] = end;
        });
        await this._hass.callService(DOMAIN, "set_time_program_day", data);
      }
      this._status = this._t("write_success");
      await this._loadSchedule();
    } catch (error) {
      this._status = this._t("write_failed", { error: error.message || error });
      this._statusIsError = true;
      this._busy = false;
      this._render();
    }
  }
}

if (!customElements.get("weishaupt-time-program-panel")) {
  customElements.define("weishaupt-time-program-panel", WeishauptTimeProgramPanel);
}

class WeishauptTimeProgramCard extends WeishauptTimeProgramPanel {}

if (!customElements.get("weishaupt-time-program-card")) {
  customElements.define("weishaupt-time-program-card", WeishauptTimeProgramCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "weishaupt-time-program-card")) {
  window.customCards.push({
    type: "weishaupt-time-program-card",
    name: "Weishaupt time programs / Zeitprogramme",
    description: "View and edit WCM-COM weekly programs",
  });
}
