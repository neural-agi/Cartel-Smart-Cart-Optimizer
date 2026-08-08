import Navbar from "@/components/marketing/Navbar";
import Hero from "@/components/marketing/Hero";
import Problem from "@/components/marketing/Problem";
import HowItWorks from "@/components/marketing/HowItWorks";
import Features from "@/components/marketing/Features";
import SupportedPlatforms from "@/components/marketing/SupportedPlatforms";
import Testimonials from "@/components/marketing/Testimonials";
import Pricing from "@/components/marketing/Pricing";
import FAQ from "@/components/marketing/FAQ";
import CTA from "@/components/marketing/CTA";
import Footer from "@/components/marketing/Footer";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <Hero />
      <Problem />
      <HowItWorks />
      <Features />
      <SupportedPlatforms />
      <Testimonials />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </>
  );
}
