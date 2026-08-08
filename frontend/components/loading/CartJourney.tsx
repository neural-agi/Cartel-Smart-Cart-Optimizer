"use client";

import { useEffect, useMemo, useState } from "react";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, ShoppingCart } from "lucide-react";

const platforms = [
  {
    id: "blinkit",
    name: "Blinkit",
    status: "Comparing prices...",
  },
  {
    id: "zepto",
    name: "Zepto",
    status: "Comparing prices...",
  },
  {
    id: "instamart",
    name: "Swiggy Instamart",
    status: "Comparing prices...",
  },
  {
    id: "bigbasket",
    name: "BigBasket",
    status: "Comparing prices...",
  },
] as const;

export default function CartJourney() {
  const [currentPlatform, setCurrentPlatform] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPlatform((current) =>
        current === platforms.length - 1 ? 0 : current + 1
      );
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  const progress = useMemo(() => {
    if (platforms.length <= 1) {
      return 0;
    }

    return currentPlatform / (platforms.length - 1);
  }, [currentPlatform]);

  return (
    <section
      aria-label="Cart optimization progress"
      className="space-y-8"
    >
      {/* Journey Track */}

      <div className="relative rounded-3xl border border-border bg-muted/20 px-4 py-5">
        <div className="relative h-16">
          <div className="absolute left-8 right-8 top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-border" />

          {/* Checkpoints */}

          <div className="absolute inset-0 flex items-center justify-between px-6">
            {platforms.map((platform, index) => {
              const completed = index < currentPlatform;
              const active = index === currentPlatform;

              return (
                <div
                  key={platform.id}
                  className="flex flex-col items-center gap-2"
                >
                  <motion.div
                    initial={false}
                    animate={{
                      scale: active ? 1.15 : 1,
                      y: active ? -2 : 0,
                      opacity: completed || active ? 1 : 0.45,
                    }}
                    transition={{
                      duration: 0.3,
                    }}
                    className={`h-2.5 w-2.5 rounded-full border ${
                      completed
                        ? "border-green-500 bg-green-500"
                        : active
                          ? "border-primary bg-primary"
                          : "border-border bg-background"
                    }`}
                  />

                  <span
                    className={`hidden text-xs font-medium sm:block ${
                      completed
                        ? "text-foreground"
                        : active
                          ? "text-primary"
                          : "text-muted-foreground"
                    }`}
                  >
                    {platform.name}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Animated Cart */}
          <motion.div
            animate={{
              left: `calc(${progress * 100}% - 18px)`,
            }}
            transition={{
              type: "spring",
              stiffness: 140,
              damping: 18,
            }}
            className="absolute top-1/2 -translate-y-1/2"
          >
            <motion.div
              animate={{
                y: [0, -2, 0],
              }}
              transition={{
                duration: 0.9,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="flex items-center justify-center rounded-xl border border-primary/20 bg-background px-3 py-2 shadow-md"
            >
              <ShoppingCart className="h-5 w-5 text-primary" />
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Platform Cards */}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {platforms.map((platform, index) => {
          const completed = index < currentPlatform;
          const active = index === currentPlatform;

          return (
            <motion.div
              key={platform.id}
              initial={false}
              animate={{
                scale: active ? 1.04 : 1,
                y: active ? -4 : 0,
                opacity: completed || active ? 1 : 0.55,
                boxShadow: active
                  ? "0 0 28px rgba(59,130,246,0.18)"
                  : "0 0 0 rgba(0,0,0,0)",
              }}
              transition={{
                duration: 0.35,
              }}
              className={`rounded-2xl border p-5 transition-colors ${
                completed
                  ? "border-green-500/40 bg-green-500/10"
                  : active
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card"
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="font-semibold">{platform.name}</p>

                <AnimatePresence mode="wait">
                  {completed ? (
                    <motion.div
                      key="completed"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 350,
                        damping: 18,
                      }}
                    >
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    </motion.div>
                  ) : active ? (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="waiting"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-5 w-5 rounded-full border border-border"
                    />
                  )}
                </AnimatePresence>
              </div>

              <p className="mt-4 text-sm text-muted-foreground">
                {completed
                  ? "Price collected"
                  : active
                    ? platform.status
                    : "Waiting"}
              </p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}