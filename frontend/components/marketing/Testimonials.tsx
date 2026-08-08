"use client";

import { motion } from "framer-motion";
import { Quote } from "lucide-react";

const testimonials = [
  {
    quote:
      "I stopped opening four grocery apps just to compare the same basket.",
    name: "Demo shopper 01",
    context: "Fictional development feedback",
    initials: "01",
  },
  {
    quote:
      "The useful part is seeing the total, not just a cheaper price on one item.",
    name: "Demo shopper 02",
    context: "Fictional development feedback",
    initials: "02",
  },
  {
    quote:
      "A clearer way to decide whether splitting the cart is actually worth it.",
    name: "Demo shopper 03",
    context: "Fictional development feedback",
    initials: "03",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonials" className="border-y border-border/60 bg-muted/20 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
            Demo feedback
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            Less comparing. More confidence.
          </h2>
          <p className="mt-6 text-base leading-8 text-muted-foreground sm:text-lg">
            A preview of the kind of everyday friction Cartel is designed to remove.
          </p>
        </motion.div>

        <div className="mx-auto mt-14 grid max-w-6xl gap-5 md:grid-cols-3">
          {testimonials.map((testimonial, index) => (
            <motion.figure
              key={testimonial.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: index * 0.08, ease: "easeOut" }}
              className="flex h-full flex-col rounded-2xl border border-border bg-card p-6 sm:p-7"
            >
              <Quote className="h-5 w-5 text-primary" aria-hidden="true" />
              <blockquote className="mt-6 flex-1 text-base leading-7 text-foreground">
                “{testimonial.quote}”
              </blockquote>
              <figcaption className="mt-8 flex items-center gap-3 border-t border-border pt-5">
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
                  aria-hidden="true"
                >
                  {testimonial.initials}
                </div>
                <div>
                  <p className="text-sm font-semibold">{testimonial.name}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {testimonial.context}
                  </p>
                </div>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}
