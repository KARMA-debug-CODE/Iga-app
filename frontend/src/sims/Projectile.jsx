import { useCallback, useEffect, useRef, useState } from "react";

import { drawAxes, makeView, palette, Slider, useCanvas } from "./canvas";
import { GRAVITY, niceStep, positionAt, projectile, round } from "./physics";

const TRAIL_COLOURS = ["#00A1DE", "#2E8B57", "#D97706", "#9333EA", "#D64545"];

export default function Projectile() {
  const [angle, setAngle] = useState(45);
  const [speed, setSpeed] = useState(20);
  const [planet, setPlanet] = useState("earth");
  const [trails, setTrails] = useState([]);
  const [flying, setFlying] = useState(null);
  const [canvasRef, size] = useCanvas(0.55);
  const frame = useRef(0);

  const g = GRAVITY[planet];
  const prediction = projectile({ speed, angleDeg: angle, g });
  // Fit the view to the furthest/highest shot possible at this speed and gravity.
  const maxRange = Math.max((speed * speed) / g, ...trails.map((t) => t.range), 10);
  const maxHeight = Math.max((speed * speed) / (2 * g), ...trails.map((t) => t.maxHeight), 5);

  const draw = useCallback(
    (ball) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const colors = palette();
      const xMax = maxRange * 1.08;
      const yMax = Math.max(maxHeight * 1.25, xMax * 0.15);
      const view = makeView({ width: size.width, height: size.height, xMin: 0, xMax, yMin: 0, yMax });
      drawAxes(ctx, view, { xStep: niceStep(xMax), yStep: niceStep(yMax, 5), xLabel: "x (m)", yLabel: "y (m)", colors });

      const path = (shot, colour, upTo = shot.time) => {
        ctx.strokeStyle = colour;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        const steps = 80;
        for (let i = 0; i <= steps; i++) {
          const t = (upTo * i) / steps;
          const p = positionAt(shot, t, shot.g);
          if (i === 0) ctx.moveTo(view.x(p.x), view.y(p.y));
          else ctx.lineTo(view.x(p.x), view.y(Math.max(0, p.y)));
        }
        ctx.stroke();
      };
      trails.forEach((shot, i) => path(shot, TRAIL_COLOURS[i % TRAIL_COLOURS.length]));

      // Launcher
      const rad = (angle * Math.PI) / 180;
      ctx.strokeStyle = colors.strong;
      ctx.lineWidth = 6;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(view.x(0), view.y(0));
      ctx.lineTo(view.x(0) + 34 * Math.cos(rad), view.y(0) - 34 * Math.sin(rad));
      ctx.stroke();

      if (ball) {
        path(ball.shot, colors.yellow, ball.t);
        const p = positionAt(ball.shot, ball.t, ball.shot.g);
        ctx.fillStyle = colors.red;
        ctx.beginPath();
        ctx.arc(view.x(p.x), view.y(Math.max(0, p.y)), 7, 0, Math.PI * 2);
        ctx.fill();
      }
    },
    [canvasRef, size, trails, angle, maxRange, maxHeight],
  );

  useEffect(() => {
    if (!flying) draw(null);
  }, [draw, flying]);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  function launch() {
    cancelAnimationFrame(frame.current);
    const shot = { ...projectile({ speed, angleDeg: angle, g }), g, angle, speed };
    const startTime = performance.now();
    // Play in real time, but never take longer than 4 s on screen.
    const playback = Math.max(1, shot.time / 4);
    const tick = (now) => {
      const t = Math.min(shot.time, ((now - startTime) / 1000) * playback);
      setFlying({ shot, t });
      draw({ shot, t });
      if (t < shot.time) frame.current = requestAnimationFrame(tick);
      else {
        setFlying(null);
        setTrails((prev) => [...prev.slice(-4), shot]);
      }
    };
    frame.current = requestAnimationFrame(tick);
  }

  const last = trails[trails.length - 1];

  return (
    <div className="lab">
      <canvas ref={canvasRef} aria-label={`Projectile launched at ${angle} degrees and ${speed} metres per second`} />
      <div className="lab-controls">
        <Slider label="Launch angle θ" value={angle} min={5} max={85} unit="°" onChange={setAngle} />
        <Slider label="Launch speed u" value={speed} min={5} max={40} unit=" m/s" onChange={setSpeed} />
        <label>
          Gravity g
          <select value={planet} onChange={(e) => setPlanet(e.target.value)}>
            <option value="earth">Earth (9.8 m/s²)</option>
            <option value="moon">Moon (1.6 m/s²)</option>
            <option value="mars">Mars (3.7 m/s²)</option>
          </select>
        </label>
      </div>
      <div className="row">
        <button className="btn btn-success" onClick={launch} disabled={!!flying}>
          🚀 Launch
        </button>
        <button className="btn btn-secondary" onClick={() => setTrails([])} disabled={!trails.length}>
          Clear paths
        </button>
      </div>
      <div className="lab-readout" aria-live="polite">
        <div>
          Time of flight <strong>{round(prediction.time)} s</strong>
          <span className="small muted">T = 2u sinθ / g</span>
        </div>
        <div>
          Max height <strong>{round(prediction.maxHeight)} m</strong>
          <span className="small muted">H = u² sin²θ / 2g</span>
        </div>
        <div>
          Range <strong>{round(prediction.range)} m</strong>
          <span className="small muted">R = u² sin2θ / g</span>
        </div>
        {last && (
          <div>
            Last shot <strong>{last.angle}° · {last.speed} m/s</strong>
            <span className="small muted">landed at {round(last.range)} m</span>
          </div>
        )}
      </div>
    </div>
  );
}
