import {
  Brain,
  ShoppingCart,
  IndianRupee,
  BarChart3,
} from "lucide-react";

const features = [
  {
    icon: ShoppingCart,
    title: "One Cart. Multiple Stores.",
    description:
      "Add groceries once. Cartel automatically splits your cart across multiple platforms to find the lowest possible total price.",
  },
  {
    icon: IndianRupee,
    title: "Real Savings.",
    description:
      "Every comparison includes delivery fees, memberships, platform offers and hidden charges. No misleading discounts.",
  },
  {
    icon: Brain,
    title: "Learns Your Shopping.",
    description:
      "Frequently bought items appear instantly, reducing search time and making repeat grocery shopping effortless.",
  },
  {
    icon: BarChart3,
    title: "Track Every Rupee.",
    description:
      "See your lifetime savings, shopping trends, favourite platforms and yearly Cartel Wrapped in one place.",
  },
];

export default function Features() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-4xl font-bold tracking-tight md:text-5xl">
          Why use Cartel?
        </h2>

        <p className="mt-6 text-lg text-muted-foreground">
          Cartel removes the hassle of comparing grocery prices manually.
          One cart. Every platform. Lowest possible price.
        </p>
      </div>

      <div className="mt-16 grid gap-8 md:grid-cols-2 xl:grid-cols-4">
        {features.map((feature) => {
          const Icon = feature.icon;

          return (
            <div
              key={feature.title}
              className="rounded-3xl border border-border bg-card p-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
            >
              <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Icon className="h-6 w-6" />
              </div>

              <h3 className="text-xl font-semibold">
                {feature.title}
              </h3>

              <p className="mt-4 leading-7 text-muted-foreground">
                {feature.description}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}