"use client";

import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

interface AnimatedNumberProps {
  value: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  className?: string;
}

export default function AnimatedNumber({
  value,
  prefix = "",
  suffix = "",
  duration = 2,
  className = "",
}: AnimatedNumberProps) {
  const motionValue = useMotionValue(0);
  const roundedValue = useTransform(motionValue, Math.round);

  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const unsubscribe = roundedValue.on("change", (latest) => {
      setDisplayValue(latest);
    });

    const controls = animate(motionValue, value, {
      duration,
      ease: "easeOut",
    });

    return () => {
      unsubscribe();
      controls.stop();
    };
  }, [motionValue, roundedValue, value, duration]);

  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {prefix}
      {displayValue.toLocaleString("en-IN")}
      {suffix}
    </motion.span>
  );
}