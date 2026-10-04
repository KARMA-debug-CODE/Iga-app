import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";

/** Fetch `path` on mount and whenever `deps` change. Returns {data, error, loading, reload, setData}. */
export function useApi(path, { params, skip = false } = {}, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: !skip });
  const key = JSON.stringify([path, params]);
  const counter = useRef(0);

  const load = useCallback(async () => {
    if (skip || !path) return;
    const id = ++counter.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await api(path, { params });
      if (id === counter.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (id === counter.current) setState({ data: null, error, loading: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, skip]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, ...deps]);

  const setData = useCallback((updater) => {
    setState((s) => ({ ...s, data: typeof updater === "function" ? updater(s.data) : updater }));
  }, []);

  return { ...state, reload: load, setData };
}

export function useOnline() {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

const LOCALES = { en: "en-GB", fr: "fr-FR" };

/** A calendar date with the year ("4 October 2026"), for subscriptions, receipts and periods. */
export function formatDay(value, lang = "en") {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat(LOCALES[lang] || "en-GB", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleDateString();
  }
}

/** An amount of money in the reader's format (whole francs for RWF). */
export function formatMoney(amount, currency, lang = "en") {
  const value = Number(amount);
  try {
    return new Intl.NumberFormat(LOCALES[lang] || "en-GB", {
      style: "currency",
      currency,
      maximumFractionDigits: currency === "RWF" ? 0 : 2,
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

export function formatDate(value, lang = "en") {
  if (!value) return "";
  const locale = LOCALES[lang] || "en-GB";
  try {
    return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
}
