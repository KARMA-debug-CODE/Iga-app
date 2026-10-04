import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
import { drawAxes, makeView, palette, Slider, useCanvas } from "./canvas";
import { marketAtPrice, marketEquilibrium, round } from "./physics";

const B = 2;
const D = 2;

export default function Market() {
  const { t, lang } = useI18n();
  const decimal = lang === "fr" ? "," : ".";
  const num = (value, digits = 2) => round(value, digits, decimal);
  const [demandShift, setDemandShift] = useState(100);
  const [supplyShift, setSupplyShift] = useState(20);
  const [price, setPrice] = useState(25);
  const [canvasRef, size] = useCanvas(0.7, 260);

  const model = { a: demandShift, b: B, c: supplyShift, d: D };
  const eq = marketEquilibrium(model);
  const atPrice = marketAtPrice(model, price);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const colors = palette();
    const view = makeView({ width: size.width, height: size.height, xMin: 0, xMax: 160, yMin: 0, yMax: 70 });
    drawAxes(ctx, view, { xStep: 20, yStep: 10, xLabel: t("sim.market.quantity"), yLabel: t("sim.market.priceAxis"), colors, decimal });

    const line = (qOf, colour, label) => {
      ctx.strokeStyle = colour;
      ctx.lineWidth = 3;
      ctx.beginPath();
      let started = false;
      for (let p = 0; p <= 70; p += 0.5) {
        const q = qOf(p);
        if (q < 0 || q > 160) {
          started = false;
          continue;
        }
        if (!started) ctx.moveTo(view.x(q), view.y(p));
        else ctx.lineTo(view.x(q), view.y(p));
        started = true;
      }
      ctx.stroke();
      ctx.fillStyle = colour;
      ctx.font = "700 13px system-ui, sans-serif";
      const pLabel = label === "D" ? 8 : 60;
      const q = qOf(pLabel);
      if (q >= 0 && q <= 160) ctx.fillText(label, view.x(q) + 6, view.y(pLabel));
    };
    line((p) => model.a - model.b * p, colors.blue, "D");
    line((p) => model.c + model.d * p, colors.green, "S");

    // Chosen price and the gap at that price.
    ctx.setLineDash([6, 5]);
    ctx.strokeStyle = colors.red;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(view.x(0), view.y(price));
    ctx.lineTo(view.x(160), view.y(price));
    ctx.stroke();
    ctx.setLineDash([]);
    if (atPrice.status !== "equilibrium") {
      ctx.strokeStyle = atPrice.status === "shortage" ? colors.red : colors.yellow;
      ctx.lineWidth = 6;
      ctx.globalAlpha = 0.6;
      ctx.beginPath();
      ctx.moveTo(view.x(atPrice.demanded), view.y(price));
      ctx.lineTo(view.x(atPrice.supplied), view.y(price));
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    if (eq.price >= 0 && eq.quantity >= 0) {
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = colors.text;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(view.x(0), view.y(eq.price));
      ctx.lineTo(view.x(eq.quantity), view.y(eq.price));
      ctx.lineTo(view.x(eq.quantity), view.y(0));
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = colors.strong;
      ctx.beginPath();
      ctx.arc(view.x(eq.quantity), view.y(eq.price), 6, 0, Math.PI * 2);
      ctx.fill();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasRef, size, demandShift, supplyShift, price, t, decimal]);

  const statusText = {
    equilibrium: t("sim.market.equilibrium"),
    shortage: t("sim.market.shortage", { n: num(atPrice.gap, 0) }),
    surplus: t("sim.market.surplus", { n: num(atPrice.gap, 0) }),
  }[atPrice.status];

  return (
    <div className="lab">
      <canvas ref={canvasRef} aria-label={t("sim.market.aria")} />
      <div className="lab-controls">
        <Slider label={t("sim.market.demand")} value={demandShift} min={60} max={150} step={5} onChange={setDemandShift} />
        <Slider label={t("sim.market.supply")} value={supplyShift} min={-20} max={70} step={5} onChange={setSupplyShift} />
        <Slider label={t("sim.market.price")} value={price} min={0} max={60} step={1} onChange={setPrice} />
      </div>
      <div className="lab-readout" aria-live="polite">
        <div>
          {t("sim.market.eqPrice")} <strong>{num(eq.price, 1)}</strong>
        </div>
        <div>
          {t("sim.market.eqQuantity")} <strong>{num(eq.quantity, 1)}</strong>
        </div>
        <div>
          {t("sim.market.atPrice", { price })} <strong>{num(atPrice.demanded, 0)}</strong>
          <span className="small muted">{t("sim.market.supplied", { n: num(atPrice.supplied, 0) })}</span>
        </div>
      </div>
      <div className={`alert ${atPrice.status === "equilibrium" ? "alert-success" : "alert-warn"}`}>{statusText}</div>
      <p className="small muted" style={{ margin: 0 }}>
        {t("sim.market.model", { a: demandShift, c: supplyShift })}
      </p>
    </div>
  );
}
