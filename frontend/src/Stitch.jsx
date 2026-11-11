import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "./api";
import catalogueArt from "./assets/catalogue/manifest.json";
import "@fontsource/syne/600.css";
import "@fontsource/syne/700.css";
import "@fontsource/syne/800.css";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "./stitch.css";

const artwork = import.meta.glob("./assets/catalogue/*.webp", {
  eager: true,
  query: "?url",
  import: "default",
});
const spotlightArt = import.meta.glob("./assets/stitch/*.webp", {
  eager: true,
  query: "?url",
  import: "default",
});
const spotlightNames = {
  1: "orbital",
  2: "coast",
  3: "teahouse",
  4: "observatory",
  5: "particles",
  6: "city",
};
export function StitchArtwork({ id, large = false, backdrop = false }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [id]);
  const entry = catalogueArt[String(id)];
  const wide =
    backdrop &&
    spotlightNames[id] &&
    spotlightArt[`./assets/stitch/${spotlightNames[id]}.webp`];
  const src = wide || (entry && artwork[`./assets/catalogue/${entry.file}`]);
  if (!src || failed) {
    const hue = (Number(id) * 137.508) % 360;
    return (
      <div
        className="cinema-artwork generated-cover"
        style={{
          background: `linear-gradient(${Number(id) * 23}deg, hsl(${hue} 30% 12%), hsl(${hue + 40} 38% 36%))`,
        }}
        aria-hidden="true"
      >
        <span>{String(id).padStart(3, "0")}</span>
      </div>
    );
  }
  return (
    <img
      className={`cinema-artwork${entry.official ? " official-poster" : ""}`}
      src={src}
      alt=""
      loading={large ? "eager" : "lazy"}
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

export function CoverLabel({ id }) {
  return catalogueArt[String(id)]?.official ? null : (
    <span className="poster-index">Illustrative cover</span>
  );
}

function Summary({ title }) {
  return (
    <>
      <p className="stitch-description">
        {title.description ||
          (title.teaser
            ? title.teaser.replace(/\s+\S*$/, "") + "…"
            : "Explore this title in the BingeBox collection.")}
      </p>
      <div className="stitch-audio">
        <span aria-hidden="true">◎</span> Audio:{" "}
        {title.audio_languages?.length
          ? title.audio_languages.join(", ")
          : "Unknown"}
      </div>
    </>
  );
}

function QuickLook({ title, onClose, returnFocus }) {
  const dialog = useRef(null);
  useEffect(() => {
    const overflow = document.body.style.overflow;
    dialog.current.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
      if (returnFocus?.isConnected) returnFocus.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="stitch-dialog"
      aria-labelledby="quick-title"
      onClose={onClose}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const controls = [
          ...dialog.current.querySelectorAll(
            "button:not(:disabled), a[href], [tabindex='0']",
          ),
        ];
        const first = controls[0],
          last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }}
    >
      <div className="stitch-dialog-art">
        <StitchArtwork id={title.title_id} large />
      </div>
      <button
        className="quiet stitch-close"
        aria-label="Close quick look"
        onClick={() => dialog.current.close()}
        autoFocus
      >
        ×
      </button>
      <div className="stitch-dialog-copy">
        <p className="eyebrow">A CLOSER LOOK</p>
        <h2 id="quick-title">{title.name}</h2>
        <p className="stitch-tags">
          {title.release_year} · {title.genres?.join(" · ")}
        </p>
        <Summary title={title} />
        <Link className="button stitch-primary" to={`/title/${title.title_id}`}>
          Open title <span aria-hidden="true">↗</span>
        </Link>
        <p className="stitch-disclaimer">
          Illustrative concept artwork. Full videos are labelled course-demo
          placeholders.
        </p>
      </div>
    </dialog>
  );
}

export function StitchHero({ user }) {
  const [titles, setTitles] = useState([]);
  const [active, setActive] = useState(0);
  const [error, setError] = useState("");
  const [quick, setQuick] = useState(false);
  const quickTrigger = useRef(null);
  const hero = useRef(null);
  useEffect(() => {
    let cancelled = false;
    api("/catalog?limit=6&page=1")
      .then((data) => {
        if (!cancelled) {
          setTitles(data.items);
          setActive(0);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [user.profile?.profile_id, user.kind]);
  useEffect(() => {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    const draw = () => {
      frame = 0;
      const offset = reduce.matches
        ? 0
        : Math.min(
            90,
            Math.max(0, -(hero.current?.getBoundingClientRect().top || 0)) *
              0.16,
          );
      hero.current?.style.setProperty("--stitch-depth", `${offset}px`);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(draw);
    };
    window.addEventListener("scroll", schedule, { passive: true });
    reduce.addEventListener("change", schedule);
    draw();
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      reduce.removeEventListener("change", schedule);
    };
  }, []);
  const title = titles[active];
  const next = titles[(active + 1) % titles.length];
  return (
    <>
      <section
        className="stitch-hero"
        ref={hero}
        aria-label="Featured collection"
      >
        <div className="stitch-backdrop" key={title?.title_id || 0}>
          <StitchArtwork id={title?.title_id || 1} large backdrop />
        </div>
        <div className="stitch-hero-shade" />
        <div className="stitch-hero-grid">
          <div className="stitch-feature-copy" key={title?.title_id || 0}>
            <div className="stitch-badges">
              <span>IN THE SPOTLIGHT</span>
              {title && (
                <>
                  <span>{title.release_year}</span>
                  <span>{title.title_type === "S" ? "SERIES" : "FILM"}</span>
                  {title.imdb_rating != null && (
                    <span>★ IMDb {title.imdb_rating}</span>
                  )}
                </>
              )}
            </div>
            <p className="stitch-subtitle">
              {title?.genres?.join(" / ") || "A collection to get lost in"}
            </p>
            <h1>{title?.name || "Your next great story."}</h1>
            {title ? (
              <Summary title={title} />
            ) : (
              <p className="stitch-description">
                Discover films and series, one good story at a time.
              </p>
            )}
            <div className="actions">
              {title && (
                <>
                  <Link
                    className="button stitch-primary"
                    to={`/title/${title.title_id}`}
                  >
                    <span aria-hidden="true">▶</span> Explore title
                  </Link>
                  <button
                    ref={quickTrigger}
                    className="quiet"
                    onClick={() => setQuick(true)}
                  >
                    <span aria-hidden="true">ⓘ</span> Quick look
                  </button>
                </>
              )}
              <a href="#collection" className="stitch-browse">
                Browse collection <span aria-hidden="true">↓</span>
              </a>
            </div>
            <p className="stitch-disclaimer">
              Illustrative artwork · Course-demo videos
            </p>
            {error && (
              <p role="status">
                Spotlight unavailable. Browse the collection below.
              </p>
            )}
          </div>
          {next && (
            <aside className="stitch-next">
              <div className="stitch-next-label">
                <span>MORE TO DISCOVER</span>
                <span>{next.title_type === "S" ? "Series" : "Film"}</span>
              </div>
              <Link
                to={`/title/${next.title_id}`}
                className="stitch-next-art"
                aria-label={`Explore ${next.name}`}
              >
                <StitchArtwork id={next.title_id} large backdrop />
                <span aria-hidden="true">↗</span>
              </Link>
              <h2>{next.name}</h2>
              <p>{next.genres?.join(" · ")}</p>
              <div className="stitch-next-footer">
                <span>{next.release_year}</span>
                <button
                  className="quiet"
                  onClick={() => setActive((active + 1) % titles.length)}
                >
                  Feature this <span aria-hidden="true">→</span>
                </button>
              </div>
            </aside>
          )}
        </div>
        <div className="stitch-hero-bottom">
          <span>
            {user.profile
              ? `Watching as ${user.profile.name}`
              : "Guest preview"}
          </span>
          <a href="#collection">
            Discover your next chapter <span aria-hidden="true">↓</span>
          </a>
          <span>
            {String(active + 1).padStart(2, "0")} /{" "}
            {String(titles.length || 1).padStart(2, "0")}
          </span>
        </div>
      </section>
      {quick && title && (
        <QuickLook
          title={title}
          onClose={() => setQuick(false)}
          returnFocus={quickTrigger.current}
        />
      )}
    </>
  );
}

export function StitchOutro() {
  return (
    <section className="stitch-membership section">
      <div>
        <p className="eyebrow">YOUR STORIES, YOUR WAY</p>
        <h2>Make room for your next favourite.</h2>
        <p>Personal profiles. Flexible plans. A collection to come back to.</p>
      </div>
      <Link className="button" to="/plans">
        Compare plans <span aria-hidden="true">↗</span>
      </Link>
    </section>
  );
}
