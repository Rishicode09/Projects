"use client";

import { useState, useEffect } from "react";

// useLocalStorage — like useState, but also saves to the browser so data
// survives refreshes. Returns [value, setValue, hydrated].
//   hydrated = false until we've finished reading any saved value, so the
//   page can avoid briefly flashing the default data.
export function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(initialValue);
  const [hydrated, setHydrated] = useState(false);

  // On first load, read any previously saved value.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(key);
      if (saved !== null) setValue(JSON.parse(saved));
    } catch {
      // ignore corrupted/unavailable storage
    }
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Save on change — but only AFTER we've loaded, so we never overwrite
  // saved data with the default value during the very first render.
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // ignore write errors
    }
  }, [key, value, hydrated]);

  return [value, setValue, hydrated];
}
