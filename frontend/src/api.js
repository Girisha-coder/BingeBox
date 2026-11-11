export async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check the entered values and try again.",
    );
  return data;
}
export const send = (path, body = {}, method = "POST") =>
  api(path, { method, body });
export function deviceId() {
  let id = sessionStorage.getItem("bingebox-device-v1");
  if (!id) {
    id = "Web " + crypto.randomUUID();
    sessionStorage.setItem("bingebox-device-v1", id);
  }
  return id;
}
