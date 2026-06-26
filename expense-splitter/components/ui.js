"use client";

import { useEffect } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

// A white (or dark) "card" container.
export function Card({ children, className = "" }) {
  return (
    <section
      className={`mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800 ${className}`}
    >
      {children}
    </section>
  );
}

// A section heading with a consistent emoji "badge" and optional right-side slot.
export function SectionTitle({ icon, title, right }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-base dark:bg-slate-700">
          {icon}
        </span>
        {title}
      </h2>
      {right}
    </div>
  );
}

// A text input that gently lifts while you type (animates transform only = 60fps).
export function Input(props) {
  const { className = "", ...rest } = props;
  return (
    <motion.input
      {...rest}
      whileFocus={{ scale: 1.015 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-slate-700 ${className}`}
    />
  );
}

// A button that presses down when tapped.
export function Button({ children, onClick, type = "button", variant = "dark", className = "", title }) {
  const styles = {
    dark: "bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white",
    green: "bg-green-600 text-white hover:bg-green-700",
    ghost: "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600",
  };
  return (
    <motion.button
      type={type}
      onClick={onClick}
      title={title}
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className={`h-10 shrink-0 rounded-md px-4 text-sm font-medium transition-colors ${styles[variant]} ${className}`}
    >
      {children}
    </motion.button>
  );
}

// A small colored circle showing a person's first initial.
export function Avatar({ name, tone = "slate" }) {
  const tones = {
    red: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
    green: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
    slate: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
  };
  const initial = name ? name.charAt(0).toUpperCase() : "?";
  return (
    <span
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${tones[tone]}`}
    >
      {initial}
    </span>
  );
}

// A money figure (given in CENTS) that smoothly counts to its new value.
export function AnimatedMoney({ cents, symbol = "$", className = "" }) {
  const spring = useSpring(cents, { stiffness: 120, damping: 20 });
  const text = useTransform(spring, (v) => `${symbol}${(v / 100).toFixed(2)}`);

  useEffect(() => {
    spring.set(cents);
  }, [spring, cents]);

  return <motion.span className={className}>{text}</motion.span>;
}
