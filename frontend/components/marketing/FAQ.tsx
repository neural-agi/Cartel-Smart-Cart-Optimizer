"use client";

import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";

const questions = [
  {
    question: "What does Cartel do?",
    answer:
      "Cartel compares a grocery cart across supported platforms and helps identify a lower practical total, including the costs and benefits represented in the comparison.",
  },
  {
    question: "Which platforms does Cartel support?",
    answer:
      "The current marketing preview represents Blinkit, Zepto, Swiggy Instamart, and BigBasket. Support can expand as more platform integrations are made available.",
  },
  {
    question: "Can Cartel split one cart across platforms?",
    answer:
      "The product is designed to compare both single-platform and split-cart combinations when the available information supports that comparison.",
  },
  {
    question: "What does Cartel compare besides item prices?",
    answer:
      "The comparison is designed to account for represented delivery fees, platform fees, offers, and membership benefits rather than looking at item prices alone.",
  },
  {
    question: "Does Cartel place the order for me?",
    answer:
      "Cartel is designed to help you decide where and how to buy your cart. Ordering and checkout behavior will depend on the integrations available in the product.",
  },
  {
    question: "Are the prices always the same?",
    answer:
      "Grocery prices, fees, offers, and availability can change. Cartel's comparison is based on the information available for the evaluation at that time.",
  },
];

export default function FAQ() {
  return (
    <section id="faq" className="border-y border-border/60 bg-muted/20 py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">FAQ</p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            A few useful answers.
          </h2>
        </motion.div>

        <div className="mt-12 divide-y divide-border rounded-2xl border border-border bg-card px-6 sm:px-8">
          {questions.map((item, index) => (
            <motion.details
              key={item.question}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.4, delay: index * 0.05, ease: "easeOut" }}
              className="group py-5"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-left text-base font-semibold marker:hidden [&::-webkit-details-marker]:hidden">
                {item.question}
                <ChevronDown className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <p className="max-w-3xl pt-4 text-sm leading-7 text-muted-foreground">{item.answer}</p>
            </motion.details>
          ))}
        </div>
      </div>
    </section>
  );
}
