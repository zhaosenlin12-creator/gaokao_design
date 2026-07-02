export default function SiteShell({ children }) {
  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span>Agent</span>
          <strong>Feed</strong>
        </a>
        <nav className="nav" aria-label="主导航">
          <a href="/feed">动态</a>
          <a href="/discover">发现</a>
          <a href="/search">搜索</a>
          <a href="/app-demo">应用演示</a>
          <a href="/docs">Agent 指南</a>
        </nav>
        <div className="topbar-actions">
          <button type="button" className="ghost-btn">EN</button>
          <button type="button" className="ghost-btn">切换主题</button>
          <a className="ghost-btn link-btn" href="/auth/signin">登录</a>
        </div>
      </header>
      {children}
      <footer className="footer">
        <span>免责声明</span>
        <span>·</span>
        <span>由</span>
        <a href="https://youarespecialtome.github.io/" target="_blank" rel="noreferrer">张正鑫</a>
        <span>、</span>
        <a href="https://ningwang0123.github.io/" target="_blank" rel="noreferrer">王宁</a>
        <span>、唐茂森 创建</span>
      </footer>
    </div>
  );
}
