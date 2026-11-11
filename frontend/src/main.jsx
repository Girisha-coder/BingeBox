import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  lazy,
  Suspense,
} from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  NavLink,
  useNavigate,
  useParams,
  useLocation,
} from "react-router-dom";
import { api, send, deviceId } from "./api";
import "./style.css";
import "./stitch-base.css";
import { StitchHero, StitchArtwork, StitchOutro, CoverLabel } from "./Stitch";
import { DiscoveryMotion } from "./DiscoveryMotion";

// Keep saved URLs working while serving one interface at the root.
const legacyPrefix = /^\/(?:stitch|cinematic|black-white)(?=\/|$)/;
if (legacyPrefix.test(window.location.pathname)) {
  const route = window.location.pathname.replace(legacyPrefix, "") || "/";
  window.history.replaceState(
    null,
    "",
    route + window.location.search + window.location.hash,
  );
}
document.documentElement.dataset.theme = "stitch";
document
  .querySelector('meta[name="theme-color"]')
  ?.setAttribute("content", "#0c0e18");

const Admin = lazy(() => import("./Admin"));
const CATALOGUE_PAGE_SIZE = 20;
const Session = createContext(null);
export const useSession = () => useContext(Session);
export function useLoad(path) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [tick, setTick] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    setData(null);
    api(path)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [path, tick]);
  return { data, error, reload: () => setTick((t) => t + 1) };
}
export function ErrorNote({ children }) {
  return children ? (
    <p className="notice error" role="alert">
      {children}
    </p>
  ) : null;
}
export function Loading() {
  return (
    <p className="loading" role="status">
      Getting things ready…
    </p>
  );
}
export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
export function Button({ busy, children, ...props }) {
  return (
    <button {...props} disabled={busy || props.disabled}>
      {busy ? "Please wait…" : children}
    </button>
  );
}
function Poster({ item, large = false }) {
  const id = Number(item.title_id) || 1;
  return (
    <div aria-hidden="true" className={"poster" + (large ? " large" : "")}>
      <StitchArtwork id={id} large={large} />
      <CoverLabel id={id} />
      <span className="poster-word">{item.name}</span>
      <span className="poster-foot">FILMS & STORIES</span>
    </div>
  );
}
export function Cards({ items = [] }) {
  return (
    <div className="cards">
      {items.map((t, i) => (
        <Link
          className="card"
          to={"/title/" + t.title_id}
          key={t.watch_id || t.title_id + "-" + i}
        >
          <Poster item={t} />
          <h3>{t.name}</h3>
          <p>
            {t.episode_name ||
              [
                t.release_year,
                t.title_type === "S"
                  ? "Series"
                  : t.title_type === "M"
                    ? "Film"
                    : null,
              ]
                .filter(Boolean)
                .join(" · ")}
          </p>
          {t.progress_sec != null && (
            <progress
              aria-label="Watch progress"
              max={t.runtime_sec}
              value={t.progress_sec}
            />
          )}
        </Link>
      ))}
    </div>
  );
}
function App() {
  const [user, setUser] = useState(null),
    [error, setError] = useState("");
  const refresh = () =>
    api("/me")
      .then((value) => {
        setUser(value);
        setError("");
      })
      .catch((e) => {
        setUser({ kind: "guest" });
        setError(e.message);
      });
  useEffect(() => {
    refresh();
  }, []);
  return (
    <Session.Provider value={{ user, refresh }}>
      <BrowserRouter>
        <DiscoveryMotion />
        <a className="skip" href="#main">
          Skip to content
        </a>
        <Layout />
        <main id="main">
          <ErrorNote>{error}</ErrorNote>
          {!user ? (
            <Loading />
          ) : (
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/" element={<Discover />} />
                <Route path="/title/:id" element={<Title />} />
                <Route path="/login" element={<Login />} />
                <Route path="/plans" element={<Plans />} />
                <Route path="/profiles" element={<Profiles />} />
                <Route path="/account" element={<Account />} />
                <Route path="/watch" element={<Player />} />
                <Route path="/admin" element={<Admin />} />
                <Route
                  path="*"
                  element={
                    <Empty>
                      Page not found.{" "}
                      <Link to="/">Return to the collection</Link>.
                    </Empty>
                  }
                />
              </Routes>
            </Suspense>
          )}
        </main>
        <footer>
          <Link className="brand" to="/">
            binge<span>box</span>
            <i>®</i>
          </Link>
          <p>Stories worth staying in for.</p>
          <small>
            DBMS course demonstration · Catalogue metadata and demo videos
          </small>
        </footer>
      </BrowserRouter>
    </Session.Provider>
  );
}
function Layout() {
  const { user, refresh } = useSession(),
    nav = useNavigate();
  return (
    <header>
      <Link className="brand" to="/" aria-label="BingeBox home">
        binge<span>box</span>
        <i>®</i>
      </Link>
      <nav aria-label="Main navigation">
        <NavLink to="/">Discover</NavLink>
        <NavLink to="/plans">Plans</NavLink>
        {user?.kind === "admin" ? (
          <NavLink to="/admin">Studio</NavLink>
        ) : user?.kind === "account" ? (
          <>
            <NavLink to="/profiles">
              {user.profile?.name || "Profiles"}
              {user.kids_locked ? " · Kids" : ""}
            </NavLink>
            {!user.kids_locked && <NavLink to="/account">Account</NavLink>}
          </>
        ) : null}
      </nav>
      <div className="header-end">
        {user?.kind === "guest" ? (
          <Link className="button compact" to="/login">
            Sign in <span aria-hidden="true">↗</span>
          </Link>
        ) : (
          user && (
            <button
              className="quiet compact"
              onClick={async () => {
                await send("/auth/logout");
                await refresh();
                nav("/");
              }}
            >
              Sign out
            </button>
          )
        )}
      </div>
    </header>
  );
}
function Discover() {
  const { user } = useSession();
  const [filters, setFilters] = useState({
      q: "",
      genre: "",
      audio: "",
      subtitle: "",
      min_runtime: "",
      max_runtime: "",
      min_rating: "",
    }),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1);
  const catalogue = useLoad(
      "/catalog?limit=" + CATALOGUE_PAGE_SIZE + "&page=" + page + "&" + query,
    ),
    options = useLoad("/catalog/filters");
  const hasProfile = !!user.profile;
  return (
    <>
      <StitchHero user={user} />
      {hasProfile && <HomeRows />}
      <section id="collection" className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">BROWSE AT YOUR OWN PACE</p>
            <h2>
              The collection
              <span className="count">{catalogue.data?.total ?? "—"}</span>
            </h2>
          </div>
          <p className="muted">
            {hasProfile
              ? `For ${user.profile.name} · age ${user.profile.max_age_rating} and below`
              : "A little preview of what’s waiting inside."}
          </p>
        </div>
        <form
          className="filters"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQuery(
              new URLSearchParams(
                Object.entries(filters).filter(([, v]) => v !== ""),
              ).toString(),
            );
          }}
        >
          <label className="search">
            Search the collection
            <input
              type="search"
              placeholder="A title, a mood, a story…"
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            />
          </label>
          {[
            ["genre", "Genre", "genres"],
            ["audio", "Audio", "audio"],
            ["subtitle", "Subtitles", "subtitle"],
          ].map(([key, label, list]) => (
            <label key={key}>
              {label}
              <select
                value={filters[key]}
                onChange={(e) =>
                  setFilters({ ...filters, [key]: e.target.value })
                }
              >
                <option value="">All {label.toLowerCase()}</option>
                {options.data?.[list].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          ))}
          <details className="advanced">
            <summary>More filters</summary>
            <div>
              {[
                ["min_runtime", "Min. runtime (min)", 0, 100000],
                ["max_runtime", "Max. runtime (min)", 0, 100000],
                ["min_rating", "Min. IMDb rating", 0, 10],
              ].map(([k, l, min, max]) => (
                <label key={k}>
                  {l}
                  <input
                    type="number"
                    min={min}
                    max={max}
                    step={k === "min_rating" ? "0.1" : 1}
                    value={filters[k]}
                    onChange={(e) =>
                      setFilters({ ...filters, [k]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
          </details>
          <button type="submit">Search</button>
          <button
            type="button"
            className="quiet"
            onClick={() => {
              setFilters({
                q: "",
                genre: "",
                audio: "",
                subtitle: "",
                min_runtime: "",
                max_runtime: "",
                min_rating: "",
              });
              setQuery("");
              setPage(1);
            }}
          >
            Reset
          </button>
        </form>
        <ErrorNote>{catalogue.error || options.error}</ErrorNote>
        {catalogue.data ? (
          <>
            {catalogue.data.items.length ? (
              <Cards items={catalogue.data.items} />
            ) : (
              <Empty>
                No stories match these filters. Try a broader search.
              </Empty>
            )}
            <div className="pagination">
              <button
                className="quiet"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Previous
              </button>
              <span>
                Page {page} of{" "}
                {Math.max(
                  1,
                  Math.ceil(catalogue.data.total / CATALOGUE_PAGE_SIZE),
                )}
              </span>
              <button
                className="quiet"
                disabled={page * CATALOGUE_PAGE_SIZE >= catalogue.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </>
        ) : (
          !catalogue.error && <Loading />
        )}
      </section>
      <StitchOutro />
    </>
  );
}
function HomeRows() {
  const { data, error } = useLoad("/home");
  const [genre, setGenre] = useState("");
  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!data) return <Loading />;
  const genres = [...new Set(data.top_genres.map((t) => t.genre))];
  return (
    <div className="home-rows">
      {[
        ["continue_watching", "Pick up where you left off"],
        ["up_next", "The next chapter"],
        ["recommendations", "Because of what you watched"],
      ].map(
        ([key, label]) =>
          data[key].length > 0 && (
            <section className="section" key={key}>
              <div className="section-heading">
                <h2>{label}</h2>
              </div>
              <Cards items={data[key]} />
            </section>
          ),
      )}
      {genres.length > 0 && (
        <section className="section">
          <div className="section-heading">
            <h2>Top ten, by genre</h2>
            <label>
              Genre
              <select
                value={genre || genres[0]}
                onChange={(e) => setGenre(e.target.value)}
              >
                {genres.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </label>
          </div>
          <Cards
            items={data.top_genres.filter(
              (t) => t.genre === (genre || genres[0]),
            )}
          />
        </section>
      )}
    </div>
  );
}
function Login() {
  const { refresh } = useSession(),
    nav = useNavigate();
  const [signup, setSignup] = useState(false),
    [staff, setStaff] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <section className="auth-page">
      <div className="auth-intro">
        <p className="eyebrow">YOUR EVENING, UPGRADED</p>
        <h1>
          Welcome
          <br />
          <em>to the story.</em>
        </h1>
        <p>One account. Your own profiles. A collection to get lost in.</p>
      </div>
      <form
        className="panel auth-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setError("");
          setBusy(true);
          try {
            await send("/auth/" + (signup ? "signup" : "login"), {
              email: f.get("email"),
              password: f.get("password"),
              staff,
            });
            await refresh();
            nav(staff ? "/admin" : signup ? "/plans" : "/profiles");
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="eyebrow">
          {staff ? "BINGEBOX STUDIO" : "MAKE YOURSELF AT HOME"}
        </p>
        <h2>{signup ? "Start your account" : "Sign in"}</h2>
        <label>
          Email address
          <input type="email" name="email" required autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            minLength={signup ? 8 : 1}
            maxLength={128}
            required
            autoComplete={signup ? "new-password" : "current-password"}
          />
        </label>
        {!signup && (
          <label className="check">
            <input
              type="checkbox"
              checked={staff}
              onChange={(e) => setStaff(e.target.checked)}
            />{" "}
            Staff account
          </label>
        )}
        <ErrorNote>{error}</ErrorNote>
        <Button busy={busy} type="submit">
          {signup ? "Create account" : "Sign in"}{" "}
          <span aria-hidden="true">→</span>
        </Button>
        <button
          type="button"
          className="quiet"
          onClick={() => {
            setSignup(!signup);
            setStaff(false);
            setError("");
          }}
        >
          {signup ? "Already a member? Sign in" : "New here? Create an account"}
        </button>
        <p className="muted fine">
          Course demo · Payment confirmation is simulated.
        </p>
      </form>
    </section>
  );
}
function Plans() {
  const { user } = useSession(),
    nav = useNavigate(),
    { data, error } = useLoad("/plans");
  const [fault, setFault] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <section className="section page">
      <p className="eyebrow">A LITTLE SOMETHING FOR EVERYONE</p>
      <h1>
        Your stories.
        <br />
        <em>Your kind of plan.</em>
      </h1>
      <p className="lede">
        Monthly plans, separate profiles and room for your favourite devices.
      </p>
      <ErrorNote>{error || fault}</ErrorNote>
      <div className="plans">
        {data?.map((p, i) => (
          <article
            className={"plan " + (i === 2 ? "featured" : "")}
            key={p.plan_id}
          >
            <span className="plan-number">0{i + 1} /</span>
            <h2>{p.name}</h2>
            <p className="price">
              ₹{Number(p.monthly_price)}
              <small>/ month</small>
            </p>
            <ul>
              <li>
                {p.max_profiles}{" "}
                {p.max_profiles === 1
                  ? "personal profile"
                  : "personal profiles"}
              </li>
              <li>
                {p.max_streams}{" "}
                {p.max_streams === 1
                  ? "simultaneous stream"
                  : "simultaneous streams"}
              </li>
              <li>Up to {p.max_quality} quality</li>
              <li>Movies and series</li>
            </ul>
            <Button
              busy={busy}
              onClick={async () => {
                if (user.kind === "guest") {
                  nav("/login");
                  return;
                }
                if (user.kind === "admin") {
                  setFault("Use an account login to choose a plan.");
                  return;
                }
                if (user.kids_locked) {
                  nav("/profiles");
                  return;
                }
                setBusy(true);
                setFault("");
                try {
                  const a = await api("/account");
                  await send(
                    "/account/" +
                      (["active", "past_due"].includes(a.status)
                        ? "change-plan"
                        : "subscribe"),
                    { plan_id: p.plan_id },
                  );
                  nav("/profiles");
                } catch (e) {
                  setFault(e.message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Choose {p.name} <span aria-hidden="true">↗</span>
            </Button>
          </article>
        ))}
      </div>
      <p className="muted fine">
        Demo prices in INR. Each period lasts one calendar month. Available
        video quality may be lower than your plan’s maximum.
      </p>
    </section>
  );
}
function Profiles() {
  const { user, refresh } = useSession();
  if (user.kind !== "account")
    return (
      <Empty>
        <Link to="/login">Sign in</Link> to choose a profile.
      </Empty>
    );
  return user.kids_locked ? (
    <Unlock />
  ) : (
    <ProfileManager refreshUser={refresh} />
  );
}
function Unlock() {
  const { refresh } = useSession(),
    [error, setError] = useState("");
  return (
    <section className="section narrow">
      <p className="eyebrow">A SPACE FOR LITTLE VIEWERS</p>
      <h1>Leave kids mode</h1>
      <p>Enter the account password to switch profiles or manage your plan.</p>
      <form
        className="panel stack"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await send("/account/unlock", {
              password: new FormData(e.currentTarget).get("password"),
            });
            await refresh();
          } catch (e) {
            setError(e.message);
          }
        }}
      >
        <label>
          Account password
          <input
            type="password"
            name="password"
            required
            autoComplete="current-password"
          />
        </label>
        <ErrorNote>{error}</ErrorNote>
        <button>Unlock account</button>
      </form>
    </section>
  );
}
function ProfileManager({ refreshUser }) {
  const { data, error, reload } = useLoad("/profiles"),
    nav = useNavigate();
  const [fault, setFault] = useState(""),
    [edit, setEdit] = useState(null),
    [busy, setBusy] = useState(false);
  return (
    <section className="section page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">EVERYONE GETS THEIR OWN WORLD</p>
          <h1>Who’s watching?</h1>
        </div>
        <Link to="/account" className="text-link">
          Manage account ↗
        </Link>
      </div>
      <ErrorNote>{error || fault}</ErrorNote>
      <div className="profiles">
        {data?.map((p, i) => (
          <article key={p.profile_id}>
            <button
              className={"avatar tone-" + (i % 6)}
              aria-label={"Watch as " + p.name}
              onClick={async () => {
                try {
                  await send("/profiles/" + p.profile_id + "/select");
                  await refreshUser();
                  nav("/");
                } catch (e) {
                  setFault(e.message);
                }
              }}
            >
              <span>{p.name.slice(0, 1)}</span>
              {p.is_kids && <small>KIDS</small>}
            </button>
            <h2>{p.name}</h2>
            <p className="muted">Ages {p.max_age_rating} and below</p>
            <button className="quiet compact" onClick={() => setEdit(p)}>
              Edit profile
            </button>
          </article>
        ))}
      </div>
      <form
        className="panel profile-form"
        key={edit?.profile_id || "new"}
        onSubmit={async (e) => {
          e.preventDefault();
          setFault("");
          setBusy(true);
          const form = e.currentTarget,
            f = new FormData(form),
            age = Number(f.get("age"));
          try {
            await send(
              "/profiles" + (edit ? "/" + edit.profile_id : ""),
              {
                name: f.get("name"),
                is_kids: f.get("kids") === "on",
                max_age_rating: age,
              },
              edit ? "PATCH" : "POST",
            );
            setEdit(null);
            form.reset();
            reload();
            await refreshUser();
          } catch (e) {
            setFault(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>{edit ? "Edit profile" : "Add a new viewer"}</h2>
        <div className="form-grid">
          <label>
            Profile name
            <input
              name="name"
              defaultValue={edit?.name || ""}
              required
              maxLength={30}
            />
          </label>
          <label>
            Age limit
            <select name="age" defaultValue={edit?.max_age_rating ?? 18}>
              {[0, 7, 13, 16, 18].map((a) => (
                <option key={a} value={a}>
                  {a} and below
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" name="kids" defaultChecked={edit?.is_kids} />{" "}
            Kids profile (age limit must be 0 or 7)
          </label>
        </div>
        <div className="actions">
          <Button busy={busy}>
            {edit ? "Save profile" : "Create profile"}
          </Button>
          {edit && (
            <>
              <button
                type="button"
                className="quiet"
                onClick={() => setEdit(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger quiet"
                onClick={async () => {
                  if (
                    !confirm(
                      "Delete this profile and its watch history and ratings?",
                    )
                  )
                    return;
                  try {
                    await send("/profiles/" + edit.profile_id, {}, "DELETE");
                    setEdit(null);
                    reload();
                    await refreshUser();
                  } catch (e) {
                    setFault(e.message);
                  }
                }}
              >
                Delete profile
              </button>
            </>
          )}
        </div>
        <p className="muted fine">
          Your plan sets the number of profiles. Kids profiles require a
          password to switch out.
        </p>
      </form>
    </section>
  );
}
function Title() {
  const { id } = useParams(),
    { data: t, error, reload } = useLoad("/catalog/" + id),
    { user } = useSession(),
    nav = useNavigate();
  const [fault, setFault] = useState(""),
    [busy, setBusy] = useState(false),
    [trailer, setTrailer] = useState(false);
  async function play(episode = null, replay = false) {
    setBusy(true);
    setFault("");
    try {
      const p = await send("/playback/start", {
        movie_id: episode ? null : t.title_id,
        episode_id: episode?.episode_id ?? null,
        device: deviceId(),
        replay,
      });
      nav("/watch", {
        state: {
          ...p,
          title: t.name,
          episode: episode?.name,
          title_id: t.title_id,
          next: episode
            ? t.episodes[
                t.episodes.findIndex(
                  (e) => e.episode_id === episode.episode_id,
                ) + 1
              ]
            : null,
        },
      });
    } catch (e) {
      setFault(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!t) return <Loading />;
  const mine = t.reviews?.find(
    (r) => r.profile_id === user.profile?.profile_id,
  );
  return (
    <section className="section page">
      <Link to="/" className="text-link">
        ← Back to the collection
      </Link>
      <div className="title-hero">
        <Poster item={t} large />
        <div>
          <p className="eyebrow">
            {t.title_type === "S"
              ? "A SERIES TO STAY WITH"
              : "FROM FILMS & STORIES"}
          </p>
          <h1>{t.name}</h1>
          <div className="metadata">
            <span>{t.release_year}</span>
            {t.age_rating != null && (
              <span className="badge">{t.age_rating}+</span>
            )}
            <span>
              {t.title_type === "S"
                ? `${t.season_count} seasons`
                : t.runtime_min
                  ? `${t.runtime_min} min`
                  : "Film"}
            </span>
            {t.imdb_rating && <span>IMDb {t.imdb_rating}/10</span>}
            {t.user_rating && <span>Viewers {t.user_rating}/10</span>}
          </div>
          <p className="lede">
            {t.description ||
              t.teaser ||
              "A new story waiting to be discovered."}
          </p>
          <div className="tags">
            {t.genres?.map((g) => (
              <span key={g}>{g}</span>
            ))}
          </div>
          <ErrorNote>{fault}</ErrorNote>
          <div className="actions">
            {t.preview ? (
              <Link
                className="button"
                to={user.kind === "account" ? "/profiles" : "/login"}
              >
                {user.kind === "account"
                  ? "Choose a profile"
                  : "Sign in to watch"}{" "}
                →
              </Link>
            ) : t.title_type === "M" ? (
              <>
                <Button busy={busy} onClick={() => play()}>
                  ▶ Play / resume
                </Button>
                <button
                  disabled={busy}
                  className="quiet"
                  onClick={() => play(null, true)}
                >
                  Start again
                </button>
              </>
            ) : (
              <a className="button" href="#episodes">
                Choose an episode ↓
              </a>
            )}
            {t.trailer_ref && (
              <button className="quiet" onClick={() => setTrailer(!trailer)}>
                {trailer ? "Close trailer" : "Watch trailer"}
              </button>
            )}
          </div>
          {!t.preview && (
            <p className="fine muted">
              Audio: {t.audio_languages?.join(", ") || "Not supplied"} ·
              Subtitles: {t.subtitle_languages?.join(", ") || "Not supplied"}
              <br />
              Demonstration playback uses clearly labelled placeholder videos.
            </p>
          )}
        </div>
      </div>
      {trailer && t.trailer_ref && (
        <iframe
          className="trailer"
          src={
            "https://www.youtube-nocookie.com/embed/" +
            encodeURIComponent(t.trailer_ref) +
            "?enablejsapi=1&origin=" +
            encodeURIComponent(location.origin)
          }
          title={t.name + " trailer"}
          allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      )}
      {t.episodes?.length > 0 && (
        <section id="episodes">
          <h2>One more episode</h2>
          <div className="episodes">
            {t.episodes.map((e) => (
              <article key={e.episode_id}>
                <span className="episode-no">
                  {e.season_no}.{String(e.episode_no).padStart(2, "0")}
                </span>
                <div>
                  <h3>{e.name}</h3>
                  <p className="muted">
                    {e.duration_min} min ·{" "}
                    {e.air_date || "Air date not supplied"}
                    {e.imdb_rating ? ` · IMDb ${e.imdb_rating}` : ""}
                  </p>
                </div>
                <Button busy={busy} onClick={() => play(e)}>
                  ▶ Play
                </Button>
                <RatingForm
                  endpoint={"/episodes/" + e.episode_id + "/rating"}
                  current={e.my_rating}
                  reload={reload}
                />
              </article>
            ))}
          </div>
        </section>
      )}
      {!t.preview && (
        <section className="reviews">
          <div>
            <p className="eyebrow">AFTER THE CREDITS</p>
            <h2>Your take</h2>
            <p className="muted">
              Complete at least 90% of the movie, or one episode of a series, to
              leave a review.
            </p>
            <RatingForm
              endpoint={"/catalog/" + id + "/review"}
              current={mine?.rating}
              text={mine?.review_text}
              review
              reload={reload}
            />
          </div>
          <div>
            <h2>From other viewers</h2>
            {t.reviews?.length ? (
              t.reviews.map((r) => (
                <article className="review" key={r.profile_id}>
                  <div>
                    <strong>{r.name}</strong>
                    <span>{r.rating} / 10</span>
                  </div>
                  <p>{r.review_text || "Rated without a written review."}</p>
                </article>
              ))
            ) : (
              <p className="muted">The conversation starts with you.</p>
            )}
          </div>
        </section>
      )}
    </section>
  );
}
function RatingForm({ endpoint, current, text, review = false, reload }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <form
      className={review ? "stack" : "rating-form"}
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        const f = new FormData(e.currentTarget);
        try {
          await send(
            endpoint,
            {
              rating: Number(f.get("rating")),
              review_text: review ? f.get("text") : null,
            },
            "PUT",
          );
          reload();
        } catch (e) {
          setError(e.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <label>
        {review ? "Your rating" : "Rate episode"}
        <select name="rating" defaultValue={current || 8}>
          {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
            <option key={n} value={n}>
              {n} / 10
            </option>
          ))}
        </select>
      </label>
      {review && (
        <label>
          Your review
          <textarea
            name="text"
            maxLength={2000}
            rows={3}
            defaultValue={text || ""}
          />
        </label>
      )}
      <Button busy={busy} className="quiet compact">
        {current ? "Update" : "Save"} {review ? "review" : "rating"}
      </Button>
      {current && (
        <button
          type="button"
          className="quiet compact"
          onClick={async () => {
            try {
              await send(endpoint, {}, "DELETE");
              reload();
            } catch (e) {
              setError(e.message);
            }
          }}
        >
          Remove
        </button>
      )}
      <ErrorNote>{error}</ErrorNote>
    </form>
  );
}
function Account() {
  const { user } = useSession();
  if (user.kind !== "account")
    return (
      <Empty>
        <Link to="/login">Sign in</Link> to manage your account.
      </Empty>
    );
  if (user.kids_locked) return <Unlock />;
  return <AccountDetails />;
}
function AccountDetails() {
  const { data: a, error, reload } = useLoad("/account"),
    [fault, setFault] = useState("");
  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!a) return <Loading />;
  return (
    <section className="section page">
      <p className="eyebrow">YOUR BINGEBOX</p>
      <h1>Your account</h1>
      <p className="lede">{a.email}</p>
      <ErrorNote>{fault}</ErrorNote>
      {a.suspended_at && (
        <p className="notice error">
          This account is suspended. Contact the demo administrator to reinstate
          it.
        </p>
      )}
      <div className="account-grid">
        <article className="panel">
          <span className="eyebrow">YOUR MEMBERSHIP</span>
          <h2>{a.plan_name || "Choose your first plan"}</h2>
          <p>
            {a.status || "No subscription"}
            {a.end_date ? ` · Period ends ${a.end_date}` : ""}
          </p>
          <p className="muted">
            {a.profile_count} / {a.max_profiles || "—"} profiles ·{" "}
            {a.live_streams} / {a.max_streams || "—"} active streams
          </p>
          <Link className="button" to="/plans">
            {a.plan_name ? "Change plan" : "View plans"} ↗
          </Link>
          {a.sub_id && (
            <RenewToggle
              enabled={a.auto_renew}
              reload={reload}
              onError={setFault}
            />
          )}
        </article>
        <article className="panel">
          <h2>Watching right now</h2>
          {a.sessions.length ? (
            a.sessions.map((s) => (
              <div className="device" key={s.session_id}>
                <div>
                  <strong>{s.name}</strong>
                  <p>
                    {s.device_type} · {s.device_name}
                  </p>
                </div>
                <button
                  className="quiet compact"
                  onClick={async () => {
                    try {
                      await send(
                        "/account/sessions/" + s.session_id,
                        {},
                        "DELETE",
                      );
                      reload();
                    } catch (e) {
                      setFault(e.message);
                    }
                  }}
                >
                  Stop stream
                </button>
              </div>
            ))
          ) : (
            <p className="muted">
              No active streams. Your next story is waiting.
            </p>
          )}
        </article>
      </div>
      <h2>Membership history</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Plan</th>
              <th>From</th>
              <th>Until</th>
              <th>Status</th>
              <th>Auto-renew</th>
            </tr>
          </thead>
          <tbody>
            {a.subscriptions.map((s) => (
              <tr key={s.sub_id}>
                <td>{s.name}</td>
                <td>{s.start_date}</td>
                <td>{s.end_date}</td>
                <td>{s.status}</td>
                <td>{s.auto_renew ? "On" : "Off"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function RenewToggle({ enabled, reload, onError }) {
  const [checked, setChecked] = useState(enabled),
    [busy, setBusy] = useState(false);
  return (
    <label className="check">
      <input
        type="checkbox"
        checked={checked}
        disabled={busy}
        onChange={async (e) => {
          const next = e.target.checked;
          setChecked(next);
          setBusy(true);
          try {
            await send("/account/auto-renew", { enabled: next }, "PATCH");
            reload();
          } catch (error) {
            setChecked(!next);
            onError(error.message);
          } finally {
            setBusy(false);
          }
        }}
      />{" "}
      Automatically renew every month
    </label>
  );
}
function Player() {
  const { state: p } = useLocation(),
    nav = useNavigate(),
    video = useRef(null),
    [error, setError] = useState(""),
    [finished, setFinished] = useState(false);
  const stopped = useRef(false),
    last = useRef(0);
  const position = () =>
    Math.min(
      p?.runtime_sec || 0,
      Math.max(0, Math.floor(video.current?.currentTime || 0)),
    );
  useEffect(() => {
    if (!p) return;
    const node = video.current;
    const close = () => {
      if (stopped.current) return;
      stopped.current = true;
      fetch("/api/playback/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: p.token,
          position: Math.min(p.runtime_sec, Math.floor(node?.currentTime || 0)),
        }),
        keepalive: true,
      }).catch(() => {});
    };
    window.addEventListener("pagehide", close);
    return () => {
      window.removeEventListener("pagehide", close);
      close();
    };
  }, [p]);
  if (!p)
    return (
      <Empty>
        No video selected. <Link to="/">Find a story to watch</Link>.
      </Empty>
    );
  async function save() {
    try {
      await send("/playback/progress", {
        token: p.token,
        position: position(),
      });
    } catch (e) {
      video.current?.pause();
      setError(e.message);
    }
  }
  async function stop() {
    try {
      await send("/playback/stop", { token: p.token, position: position() });
      stopped.current = true;
      nav("/title/" + p.title_id);
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <section className="section player-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            NOW PLAYING · {p.quality}
            {p.is_placeholder ? " · DEMO PLACEHOLDER" : ""}
          </p>
          <h1>{p.title}</h1>
          {p.episode && <p className="lede">{p.episode}</p>}
        </div>
        <button className="quiet" onClick={stop}>
          Save & close ×
        </button>
      </div>
      <ErrorNote>{error}</ErrorNote>
      <video
        ref={video}
        src={p.media_url}
        controls
        playsInline
        autoPlay
        onLoadedMetadata={() => {
          video.current.currentTime = p.progress_sec;
        }}
        onTimeUpdate={() => {
          const now = Date.now();
          if (now - last.current > 10000 && !stopped.current) {
            last.current = now;
            save();
          }
        }}
        onPause={() => {
          if (!stopped.current) save();
        }}
        onEnded={async () => {
          await save();
          setFinished(true);
          await send("/playback/stop", { token: p.token });
          stopped.current = true;
        }}
        onError={() =>
          setError(
            "Video could not load. Check your subscription and active devices, then try again.",
          )
        }
      />
      <div className="player-info">
        <p>
          {p.is_placeholder
            ? "This is a generated demo video, matched to the title’s runtime. No licensed film is included."
            : "Playback progress is saved automatically."}
        </p>
        <span>
          {Math.round(p.runtime_sec / 60)} min · {p.quality}
        </span>
      </div>
      {finished && (
        <div className="panel">
          <h2>That’s a wrap.</h2>
          <p>Your watch is complete. You can now leave a rating.</p>
          <Link className="button" to={"/title/" + p.title_id}>
            {p.next ? "Choose the next episode" : "Rate this story"} →
          </Link>
        </div>
      )}
    </section>
  );
}
createRoot(document.getElementById("root")).render(<App />);
