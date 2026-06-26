"use client";

import { useState, useEffect } from "react";

// useLocalStorage — a custom "hook" (reusable function that plugs into React).
// It behaves exactly like useState, but it also SAVES the value into the
// browser's built-in storage box (localStorage), so the data survives a refresh.
//
// Usage:  const [people, setPeople] = useLocalStorage("people", ["Alex"]);
export function useLocalStorage(key, initialValue) {
  // The live value, kept in React's memory.
  const [value, setValue] = useState(initialValue);

  // On first load, try to read a previously saved value from the browser.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(key);
      if (saved !== null) {
        setValue(JSON.parse(saved)); // JSON.parse turns saved text back into data
      }
    } catch {
      // If anything goes wrong (e.g. corrupted data), we just keep the default.
    }
    // We only want this to run once, for this key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Whenever the value changes, write it back into the browser's storage.
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Ignore write errors (e.g. storage full or disabled).
    }
  }, [key, value]);

  return [value, setValue];
}
