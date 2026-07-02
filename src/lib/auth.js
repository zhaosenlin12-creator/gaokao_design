const STORAGE_KEY = "gaokao-map-auth";
const ACCOUNT_KEY = "gaokao-map-accounts";

const seedAccounts = [
  { username: "alice", displayName: "Alice", email: "alice@agentsfeed.org", password: "demo1234" },
  { username: "bob", displayName: "Bob", email: "bob@agentsfeed.org", password: "demo1234" },
];

function safeParse(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function readAccounts() {
  if (typeof window === "undefined") return [...seedAccounts];
  const stored = safeParse(window.localStorage.getItem(ACCOUNT_KEY), null);
  if (Array.isArray(stored) && stored.length) return stored;
  window.localStorage.setItem(ACCOUNT_KEY, JSON.stringify(seedAccounts));
  return [...seedAccounts];
}

export function getAccounts() {
  return readAccounts();
}

export function getSession() {
  if (typeof window === "undefined") return null;
  return safeParse(window.localStorage.getItem(STORAGE_KEY), null);
}

export function registerAccount({ username, displayName, email, password }) {
  const accounts = readAccounts();
  const normalizedEmail = email.trim().toLowerCase();
  const normalizedUsername = username.trim().toLowerCase();
  const duplicate = accounts.some(
    (account) => account.email.toLowerCase() === normalizedEmail || account.username.toLowerCase() === normalizedUsername,
  );
  if (duplicate) {
    return { ok: false, error: "这个邮箱或用户名已经注册过了" };
  }

  const account = {
    id: crypto.randomUUID(),
    username: username.trim(),
    displayName: displayName.trim(),
    email: normalizedEmail,
    password,
  };
  const next = [...accounts, account];
  window.localStorage.setItem(ACCOUNT_KEY, JSON.stringify(next));
  return { ok: true, account };
}

export function signIn(identifier, password) {
  const accounts = readAccounts();
  const normalized = identifier.trim().toLowerCase();
  const account = accounts.find(
    (item) => item.email.toLowerCase() === normalized || item.username.toLowerCase() === normalized,
  );

  if (!account || account.password !== password) {
    return { ok: false, error: "账号或密码错误" };
  }

  const session = {
    username: account.username,
    displayName: account.displayName,
    email: account.email,
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }
  return { ok: true, session };
}

export function signOut() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}
