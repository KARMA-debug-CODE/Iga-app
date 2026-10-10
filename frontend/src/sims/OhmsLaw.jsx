import { useEffect, useRef, useState } from "react";

import { Icon } from "../components/Icon";
import { useI18n } from "../i18n";
import { Slider } from "./canvas";
import { ohmsLaw, round } from "./physics";

const WIRE = "M60 40 H340 V220 H60 Z";

export default function OhmsLaw() {
  const { t, lang } = useI18n();
  const decimal = lang === "fr" ? "," : ".";
  const num = (value, digits = 2) => round(value, digits, decimal);
  const [voltage, setVoltage] = useState(6);
  const [resistance, setResistance] = useState(10);
  const [readings, setReadings] = useState([]);
  const { current, power } = ohmsLaw({ voltage, resistance });
  const flow = useRef(null);
  const offset = useRef(0);

  // Animate the "electrons" along the wire at a speed proportional to the current.
  useEffect(() => {
    let frame;
    let last = performance.now();
    const tick = (now) => {
      offset.current -= (now - last) * current * 0.12;
      last = now;
      if (flow.current) flow.current.setAttribute("stroke-dashoffset", offset.current.toFixed(1));
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [current]);

  const glow = Math.min(1, power / 6);

  return (
    <div className="lab">
      <svg viewBox="0 0 400 260" role="img" aria-label={t("sim.ohms.aria", { voltage: num(voltage, 1), resistance, current: num(current, 3) })}>
        <path d={WIRE} fill="none" stroke="var(--text-soft)" strokeWidth="6" strokeLinejoin="round" />
        <path ref={flow} d={WIRE} fill="none" stroke="#00A1DE" strokeWidth="6" strokeDasharray="4 18" strokeLinecap="round" />

        {/* Battery */}
        <rect x="40" y="105" width="40" height="50" fill="var(--surface)" />
        <line x1="44" y1="118" x2="76" y2="118" stroke="var(--text)" strokeWidth="4" />
        <line x1="52" y1="132" x2="68" y2="132" stroke="var(--text)" strokeWidth="4" />
        <line x1="44" y1="146" x2="76" y2="146" stroke="var(--text)" strokeWidth="4" />
        <text x="92" y="136" fontSize="15" fontWeight="700" fill="var(--text)">{num(voltage, 1)} V</text>

        {/* Resistor */}
        <rect x="150" y="26" width="100" height="28" fill="var(--surface)" />
        <polyline
          points="150,40 160,28 172,52 184,28 196,52 208,28 220,52 232,28 244,52 250,40"
          fill="none"
          stroke="#D97706"
          strokeWidth="4"
          strokeLinejoin="round"
        />
        <text x="200" y="76" fontSize="15" fontWeight="700" textAnchor="middle" fill="var(--text)">{resistance} Ω</text>

        {/* Bulb */}
        <circle cx="200" cy="220" r="34" fill="#FAD201" opacity={glow * 0.5} />
        <circle cx="200" cy="220" r="18" fill="var(--surface)" stroke="var(--text)" strokeWidth="3" />
        <circle cx="200" cy="220" r="14" fill="#FAD201" opacity={0.15 + glow * 0.85} />

        {/* Ammeter */}
        <circle cx="340" cy="130" r="24" fill="var(--surface)" stroke="var(--text)" strokeWidth="3" />
        <text x="340" y="136" fontSize="18" fontWeight="800" textAnchor="middle" fill="var(--text)">A</text>
        <text x="300" y="175" fontSize="15" fontWeight="700" textAnchor="end" fill="var(--text)">{num(current, 3)} A</text>
      </svg>

      <div className="lab-controls">
        <Slider label={t("sim.ohms.voltage")} value={voltage} min={0} max={12} step={0.5} unit=" V" onChange={setVoltage} />
        <Slider label={t("sim.ohms.resistance")} value={resistance} min={1} max={100} step={1} unit=" Ω" onChange={setResistance} />
      </div>
      <div className="lab-readout" aria-live="polite">
        <div>
          {t("sim.ohms.current")} <strong>{num(current, 3)} A</strong>
          <span className="small muted">I = V / R</span>
        </div>
        <div>
          {t("sim.ohms.power")} <strong>{num(power, 2)} W</strong>
          <span className="small muted">P = V × I</span>
        </div>
      </div>
      <div className="row">
        <button className="btn btn-secondary btn-sm" onClick={() => setReadings((r) => [...r, { voltage, resistance, current }].slice(-8))}>
          <Icon name="plus" size={16} /> {t("sim.ohms.record")}
        </button>
        {readings.length > 0 && (
          <button className="btn btn-ghost btn-sm" onClick={() => setReadings([])}>
            {t("sim.ohms.clear")}
          </button>
        )}
      </div>
      {readings.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>V (V)</th>
                <th>R (Ω)</th>
                <th>I (A)</th>
                <th>V ÷ I</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((r, i) => (
                <tr key={i}>
                  <td>{num(r.voltage, 1)}</td>
                  <td>{r.resistance}</td>
                  <td>{num(r.current, 3)}</td>
                  <td>{r.current ? num(r.voltage / r.current, 1) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
