"use client";

import { useEffect } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

// A white "card" container with padding and a soft shadow.
export function Card({ children, className = "" }) {
  return (
    <section
      className={`mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}
    >
      {children}
    </section>
  );
}

// A numbered section heading.
export function SectionTitle({ step, title, right }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs text-white">
          {step}
        </span>
        {title}
      </h2>
      {right}
    </div>
  );
}

// A styled text input that gently lifts while you type in it.
// whileFocus animates ONLY transform (scale) — cheap for the GPU, so it stays smooth.
export function Input(props) {
  const { className = "", ...rest } = props;
  return (
    <motion.input
      {...rest}
      whileFocus={{ scale: 1.015 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 ${className}`}
    />
  );
}

// A styled button that presses down when tapped.
export function Button({ children, onClick, type = "button", variant = "dark", className = "" }) {
  const styles = {
    dark: "bg-slate-900 text-white hover:bg-slate-700",
    green: "bg-green-600 text-white hover:bg-green-700",
    ghost: "bg-slate-100 text-slate-700 hover:bg-slate-200",
  };
  return (
    <motion.button
      type={type}
      onClick={onClick}
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
    red: "bg-red-100 text-red-700",
    green: "bg-green-100 text-green-700",
    slate: "bg-slate-100 text-slate-700",
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

// A dollar number that smoothly "counts up/down" to its new value using a spring.
// useSpring gives physics-based motion (60fps); useTransform formats it as money.
export function AnimatedMoney({ value, className = "" }) {
  const spring = useSpring(value, { stiffness: 120, damping: 20 });
  const text = useTransform(spring, (v) => `$${v.toFixed(2)}`);

  // Whenever the target value changes, tell the spring to glide to it.
  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return <motion.span className={className}>{text}</motion.span>;
}
