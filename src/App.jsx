import { useEffect, useState } from "react";

import AuthPage from "./components/AuthPage.jsx";
import GaokaoMapPage from "./components/GaokaoMapPage.jsx";
import SiteShell from "./components/SiteShell.jsx";
import { getSession } from "./lib/auth.js";

function usePathname() {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return pathname;
}

function LandingPage() {
  const session = getSession();

  return (
    <main className="landing-page">
      <section className="landing-hero">
        <p className="eyebrow">Agent Feed</p>
        <h1>Everything you need to know about the latest AI</h1>
        <p className="landing-copy">一个本地可跑的站点壳，保留演示、登录、注册与内容导览。</p>
        <div className="hero-actions">
          <a className="primary-btn" href="/auth/signin">登录</a>
          <a className="secondary-btn" href="/app-demo/gaokao-map">打开演示</a>
        </div>
        {session ? <div className="notice">当前已登录：{session.displayName}</div> : null}
      </section>
    </main>
  );
}

export default function App() {
  const pathname = usePathname();

  let content = <LandingPage />;
  if (pathname.startsWith("/auth/signup")) {
    content = <AuthPage mode="signup" />;
  } else if (pathname.startsWith("/auth/signin")) {
    content = <AuthPage mode="signin" />;
  } else if (pathname.startsWith("/app-demo/gaokao-map") || pathname.startsWith("/app-demo/gaokao/index.html")) {
    content = <GaokaoMapPage />;
  }

  return <SiteShell>{content}</SiteShell>;
}
