import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Progressive motion only: native scrolling and all existing application actions remain intact.
export function DiscoveryMotion() {
  const { pathname } = useLocation();
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const main = document.querySelector("main");
    const seen = new WeakSet();
    let observer;
    let pending = 0;
    const reveal = (el) => {
      el.dataset.cinemaReveal = "visible";
      observer?.unobserve(el);
    };
    const scan = () => {
      pending = 0;
      if (media.matches || !observer) return;
      main
        ?.querySelectorAll(".card, .section-heading, .stitch-membership, .plan")
        .forEach((el, i) => {
          if (seen.has(el)) return;
          seen.add(el);
          if (el.getBoundingClientRect().top < window.innerHeight - 30) return;
          el.dataset.cinemaReveal = "pending";
          el.style.setProperty("--reveal-delay", `${(i % 4) * 45}ms`);
          observer.observe(el);
        });
    };
    const schedule = () => {
      if (!pending) pending = requestAnimationFrame(scan);
    };
    const configure = () => {
      observer?.disconnect();
      main?.querySelectorAll("[data-cinema-reveal]").forEach(reveal);
      if (media.matches || !("IntersectionObserver" in window)) return;
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) reveal(entry.target);
          });
        },
        { threshold: 0.06, rootMargin: "0px 0px -24px 0px" },
      );
      scan();
    };
    const focus = (event) => {
      const target = event.target.closest("[data-cinema-reveal]");
      if (target) reveal(target);
    };
    configure();
    const mutations = new MutationObserver(schedule);
    if (main) mutations.observe(main, { childList: true, subtree: true });
    media.addEventListener("change", configure);
    main?.addEventListener("focusin", focus);
    return () => {
      cancelAnimationFrame(pending);
      observer?.disconnect();
      mutations.disconnect();
      media.removeEventListener("change", configure);
      main?.removeEventListener("focusin", focus);
      main
        ?.querySelectorAll("[data-cinema-reveal]")
        .forEach((el) => delete el.dataset.cinemaReveal);
    };
  }, [pathname]);
  return null;
}
