"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Fades/slides children in as they scroll into view.
 *
 * Fail-safe by construction: content is visible until this effect runs. Content
 * already on screen is never hidden; only below-the-fold content is armed and
 * revealed later by an IntersectionObserver.
 */
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  /** stagger, in milliseconds */
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const inView = el.getBoundingClientRect().top < window.innerHeight * 0.95;
    if (inView || typeof IntersectionObserver === "undefined") return;

    el.classList.add("reveal-armed");
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          el.classList.add("is-visible");
          io.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ "--reveal-delay": `${delay}ms` } as React.CSSProperties}
      className={`reveal ${className}`}
    >
      {children}
    </div>
  );
}
