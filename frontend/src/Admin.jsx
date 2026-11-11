import { useState } from "react";
import { Link } from "react-router-dom";
import { useSession, useLoad, ErrorNote, Loading, Empty, Button } from "./main";
import { send } from "./api";

// [key, label, type, options]. Forms only expose the API's permitted fields.
const schemas = {
  titles: [
    ["name", "Title", "text"],
    ["release_year", "Release year", "number"],
    ["title_type", "Type", "select", ["M", "S"]],
    ["description", "Synopsis", "textarea"],
    ["age_rating", "Age rating", "select", [0, 7, 13, 16, 18]],
    ["duration_min", "Movie runtime (minutes)", "number"],
    ["series_status", "Series status", "select", ["ongoing", "ended"]],
    ["original_language", "Original language", "text"],
    ["imdb_id", "IMDb ID (optional)", "text"],
    ["imdb_rating", "IMDb rating (optional)", "number"],
    ["imdb_votes", "IMDb votes (optional)", "number"],
    ["genres", "Genres (comma separated)", "list"],
    ["audio_languages", "Audio languages (comma separated)", "list"],
    ["subtitle_languages", "Subtitle languages (comma separated)", "list"],
  ],
  episodes: [
    ["series_id", "Series ID", "number"],
    ["season_no", "Season", "number"],
    ["episode_no", "Episode number", "number"],
    ["name", "Episode name", "text"],
    ["duration_min", "Runtime (minutes)", "number"],
    ["imdb_rating", "IMDb rating (optional)", "number"],
    ["air_date", "Air date (optional)", "date"],
  ],
  genres: [["name", "Genre name", "text"]],
  videos: [
    ["asset_kind", "Asset kind", "select", ["full", "trailer"]],
    ["title_id", "Title ID (trailer only)", "number"],
    ["movie_id", "Movie ID (full movie only)", "number"],
    ["episode_id", "Episode ID (full episode only)", "number"],
    ["provider", "Provider", "select", ["file", "youtube"]],
    ["source_ref", "Relative file path / YouTube video ID", "text"],
    ["quality", "Quality", "select", ["SD", "HD", "4K"]],
    ["duration_sec", "Duration (seconds)", "number"],
    ["is_placeholder", "Generated placeholder", "checkbox"],
  ],
  plans: [
    ["name", "Plan name", "text"],
    ["monthly_price", "Monthly price (INR)", "number"],
    ["max_profiles", "Profile limit", "number"],
    ["max_streams", "Stream limit", "number"],
    ["max_quality", "Maximum quality", "select", ["SD", "HD", "4K"]],
  ],
};
const ids = {
  titles: "title_id",
  episodes: "episode_id",
  genres: "genre_id",
  videos: "asset_id",
  plans: "plan_id",
};
const columns = {
  titles: [
    "title_id",
    "name",
    "title_type",
    "release_year",
    "age_rating",
    "runtime_min",
  ],
  episodes: [
    "episode_id",
    "series_id",
    "name",
    "season_no",
    "episode_no",
    "duration_min",
  ],
  genres: ["genre_id", "name"],
  videos: [
    "asset_id",
    "asset_kind",
    "movie_id",
    "episode_id",
    "title_id",
    "quality",
    "is_placeholder",
  ],
  plans: [
    "plan_id",
    "name",
    "monthly_price",
    "max_profiles",
    "max_streams",
    "max_quality",
  ],
};
const label = (s) => s.replaceAll("_", " ").replace(/\bid\b/g, "ID");
export default function Admin() {
  const { user } = useSession();
  const [tab, setTab] = useState("");
  if (user.kind !== "admin")
    return (
      <Empty>
        Staff access required.{" "}
        <Link to="/login">Sign in with your staff account</Link>.
      </Empty>
    );
  const tabs = [
      ...(user.role !== "billing"
        ? ["titles", "episodes", "genres", "videos"]
        : []),
      ...(user.role !== "catalogue" ? ["accounts", "reports"] : []),
      ...(user.role === "super" ? ["plans"] : []),
    ],
    active = tabs.includes(tab) ? tab : tabs[0];
  return (
    <section className="section page studio">
      <div className="section-heading">
        <div>
          <p className="eyebrow">BEHIND THE STORIES</p>
          <h1>BingeBox Studio</h1>
        </div>
        <div className="staff-badge">
          <strong>{user.full_name}</strong>
          <span>{user.role} access</span>
        </div>
      </div>
      <nav className="tabs" aria-label="Studio sections">
        {tabs.map((t) => (
          <button
            key={t}
            className={t === active ? "selected" : "quiet"}
            onClick={() => setTab(t)}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>
      {active === "accounts" ? (
        <Accounts />
      ) : active === "reports" ? (
        <Reports />
      ) : (
        <Manager key={active} resource={active} />
      )}
    </section>
  );
}
function Manager({ resource }) {
  const { data, error, reload } = useLoad("/admin/manage/" + resource),
    [edit, setEdit] = useState(null),
    [fault, setFault] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState("");
  async function remove(row) {
    if (
      !confirm(
        "Delete this " +
          resource.replace(/s$/, "") +
          "? Related catalogue links may also be removed.",
      )
    )
      return;
    try {
      await send(
        "/admin/manage/" + resource + "/" + row[ids[resource]],
        {},
        "DELETE",
      );
      reload();
      setSuccess("Record deleted.");
    } catch (e) {
      setFault(e.message);
    }
  }
  return (
    <>
      <div className="section-heading">
        <h2>Manage {resource}</h2>
        <label>
          Find a record
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search loaded records…"
          />
        </label>
      </div>
      <ErrorNote>{error || fault}</ErrorNote>
      {success && (
        <p className="notice" role="status">
          {success}
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns[resource].map((c) => (
                <th key={c}>{label(c)}</th>
              ))}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data
              ?.filter((r) =>
                JSON.stringify(r).toLowerCase().includes(search.toLowerCase()),
              )
              .map((row) => (
                <tr key={row[ids[resource]]}>
                  {columns[resource].map((c) => (
                    <td key={c}>
                      {typeof row[c] === "boolean"
                        ? row[c]
                          ? "Yes"
                          : "No"
                        : String(row[c] ?? "—")}
                    </td>
                  ))}
                  <td className="table-actions">
                    <button
                      className="quiet compact"
                      onClick={() => {
                        setEdit(row);
                        setFault("");
                        setSuccess("");
                        document
                          .getElementById("editor")
                          .scrollIntoView({ behavior: "smooth" });
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="danger quiet compact"
                      onClick={() => remove(row)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {!data && !error && <Loading />}
      <form
        id="editor"
        className="panel stack"
        key={edit?.[ids[resource]] || "new"}
        onSubmit={async (e) => {
          e.preventDefault();
          setFault("");
          setSuccess("");
          setBusy(true);
          const f = new FormData(e.currentTarget),
            payload = {};
          for (const [key, , type] of schemas[resource]) {
            const value = f.get(key);
            payload[key] =
              type === "checkbox"
                ? value === "on"
                : type === "list"
                  ? String(value || "")
                      .split(",")
                      .map((x) => x.trim())
                      .filter(Boolean)
                  : type === "number" || key === "age_rating"
                    ? value === "" || value === null
                      ? null
                      : Number(value)
                    : value === ""
                      ? null
                      : value;
          }
          if (resource === "titles") {
            if (payload.title_type === "S") delete payload.duration_min;
            else delete payload.series_status;
            if (!payload.original_language)
              payload.original_language = "Unknown";
          }
          try {
            await send(
              "/admin/manage/" +
                resource +
                (edit ? "/" + edit[ids[resource]] : ""),
              payload,
              edit ? "PATCH" : "POST",
            );
            setEdit(null);
            reload();
            setSuccess("Record saved.");
          } catch (e) {
            setFault(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>
          {edit
            ? "Edit record #" + edit[ids[resource]]
            : "Add " + resource.replace(/s$/, "")}
        </h2>
        {resource === "videos" && (
          <p className="muted">
            Trailers use an 11-character YouTube ID and a title ID. Full videos
            use exactly one movie or episode ID. For an original local video,
            place the MP4 in the project’s media directory first. Generated
            placeholders must use SD.
          </p>
        )}
        <div className="form-grid">
          {schemas[resource].map(([key, title, type, options]) => (
            <label
              key={key}
              className={
                type === "checkbox"
                  ? "check"
                  : type === "textarea"
                    ? "wide"
                    : ""
              }
            >
              {type === "checkbox" ? (
                <>
                  <input
                    type="checkbox"
                    name={key}
                    defaultChecked={edit?.[key] ?? false}
                  />
                  {title}
                </>
              ) : (
                <>
                  {title}
                  {type === "select" ? (
                    <select name={key} defaultValue={edit?.[key] ?? options[0]}>
                      {options.map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ) : type === "textarea" ? (
                    <textarea
                      name={key}
                      defaultValue={edit?.[key] || ""}
                      rows={3}
                    />
                  ) : (
                    <input
                      name={key}
                      type={type === "list" ? "text" : type}
                      step={
                        ["monthly_price", "imdb_rating"].includes(key)
                          ? "0.01"
                          : 1
                      }
                      defaultValue={
                        type === "list"
                          ? edit?.[key]?.join(", ") || ""
                          : (edit?.[key] ?? "")
                      }
                      required={[
                        "name",
                        "release_year",
                        "source_ref",
                        "monthly_price",
                        "max_profiles",
                        "max_streams",
                        "season_no",
                        "episode_no",
                        "series_id",
                        "duration_sec",
                      ].includes(key)}
                    />
                  )}
                </>
              )}
            </label>
          ))}
        </div>
        <div className="actions">
          <Button busy={busy}>Save record</Button>
          {edit && (
            <button
              className="quiet"
              type="button"
              onClick={() => setEdit(null)}
            >
              Cancel edit
            </button>
          )}
        </div>
      </form>
    </>
  );
}
function Accounts() {
  const { data, error, reload } = useLoad("/admin/accounts"),
    [fault, setFault] = useState(""),
    [result, setResult] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <>
      <ErrorNote>{error || fault}</ErrorNote>
      <form
        className="panel renewal-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setFault("");
          try {
            const r = await send("/admin/renewals", {
              date: new FormData(e.currentTarget).get("date"),
            });
            setResult(
              `${r.renewed_periods} periods renewed · ${r.expired} subscriptions expired`,
            );
            reload();
          } catch (e) {
            setFault(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <h2>Process renewals</h2>
          <p className="muted">
            Extends ended auto-renewing periods; expires others and closes their
            streams. Demo payments always succeed.
          </p>
        </div>
        <label>
          Process through
          <input
            type="date"
            name="date"
            defaultValue={new Date().toLocaleDateString("en-CA")}
            required
          />
        </label>
        <Button busy={busy}>Run renewals</Button>
        {result && (
          <p className="notice" role="status">
            {result}
          </p>
        )}
      </form>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Plan</th>
              <th>Period ends</th>
              <th>Status</th>
              <th>Profiles</th>
              <th>Streams</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((a) => (
              <tr key={a.account_id}>
                <td>{a.email}</td>
                <td>{a.plan_name || "—"}</td>
                <td>{a.end_date || "—"}</td>
                <td>{a.suspended_at ? "Suspended" : a.status || "New"}</td>
                <td>
                  {a.profile_count} / {a.max_profiles || "—"}
                </td>
                <td>
                  {a.live_streams} / {a.max_streams || "—"}
                </td>
                <td>
                  <button
                    className="quiet compact"
                    onClick={async () => {
                      try {
                        await send(
                          "/admin/accounts/" +
                            a.account_id +
                            "/" +
                            (a.suspended_at ? "reinstate" : "suspend"),
                        );
                        reload();
                      } catch (e) {
                        setFault(e.message);
                      }
                    }}
                  >
                    {a.suspended_at ? "Reinstate" : "Suspend"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
function Reports() {
  const [report, setReport] = useState("active-subscriptions");
  return (
    <>
      <div className="section-heading">
        <h2>A closer look</h2>
        <label>
          Report
          <select
            aria-label="Report"
            value={report}
            onChange={(e) => setReport(e.target.value)}
          >
            {[
              ["active-subscriptions", "Active subscriptions per plan"],
              ["lapsing", "Subscriptions lapsing within seven days"],
              ["binge", "Completed episodes per profile per day"],
              ["rating-comparison", "IMDb and viewer rating comparison"],
            ].map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Report key={report} name={report} />
    </>
  );
}
function Report({ name }) {
  const { data, error } = useLoad("/admin/reports/" + name);
  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!data) return <Loading />;
  if (!data.length) return <Empty>No matching activity for this report.</Empty>;
  const columns = Object.keys(data[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{label(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c}>
                  {typeof r[c] === "boolean"
                    ? r[c]
                      ? "Yes"
                      : "No"
                    : String(r[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
