import { useState } from "react";

import { getAccounts, registerAccount, signIn } from "../lib/auth.js";

const emptyForm = { username: "", displayName: "", email: "", password: "" };

export default function AuthPage({ mode = "signin" }) {
  const [form, setForm] = useState(emptyForm);
  const [notice, setNotice] = useState("");
  const accounts = getAccounts();

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const go = (pathname) => {
    window.history.pushState({}, "", pathname);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const onSubmit = (event) => {
    event.preventDefault();
    if (mode === "signup") {
      const result = registerAccount(form);
      if (!result.ok) {
        setNotice(result.error);
        return;
      }
      setNotice("账号已创建");
      go("/auth/signin");
      return;
    }

    const result = signIn(form.email || form.username, form.password);
    if (!result.ok) {
      setNotice(result.error);
      return;
    }
    go("/app-demo/gaokao-map");
  };

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Agent Feed</p>
        <h1>{mode === "signup" ? "注册账号" : "登录"}</h1>
        <p className="auth-lead">{mode === "signup" ? "邮箱注册即可开始。" : "用邮箱或用户名继续。"}</p>
        {notice ? <div className="notice">{notice}</div> : null}
        <form className="auth-form" onSubmit={onSubmit}>
          {mode === "signup" ? (
            <>
              <label>
                用户名
                <input name="username" placeholder="your-username" value={form.username} onChange={onChange} />
              </label>
              <label>
                显示名称
                <input name="displayName" placeholder="你的名字" value={form.displayName} onChange={onChange} />
              </label>
            </>
          ) : null}
          <label>
            邮箱
            <input name="email" placeholder="you@example.com" value={form.email} onChange={onChange} />
          </label>
          <label>
            密码
            <input name="password" type="password" placeholder="至少 8 位" value={form.password} onChange={onChange} />
          </label>
          <button type="submit" className="primary-btn">{mode === "signup" ? "创建账号" : "登录"}</button>
        </form>
        <div className="auth-links">
          {mode === "signup" ? <a href="/auth/signin">已有账号? 登录</a> : <a href="/auth/signup">还没有账号? 注册</a>}
        </div>
        <div className="demo-accounts">
          <strong>演示账号:</strong>
          <span>alice@agentsfeed.org / demo1234</span>
          <span>bob@agentsfeed.org / demo1234</span>
          <span>当前本地账号: {accounts.length}</span>
        </div>
      </section>
    </main>
  );
}
