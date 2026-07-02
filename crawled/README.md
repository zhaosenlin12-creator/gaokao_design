# 爬取产物清单\n\n## 落盘位置\n\n- D:\kaifa\gaokao\crawled\ (本次新增，本会话外未动)\n\n## 文件清单\n\n- auth-signin-rendered.html  (20193 bytes)\n- auth-signin.html  (20480 bytes)\n- auth_state.json  (982 bytes)\n- diagnose_login.py  (1653 bytes)\n- download_assets.py  (1854 bytes)\n- fix_iframe.py  (1283 bytes)\n- gaokao-iframe\assets\favicon.png  (4921 bytes)\n- gaokao-iframe\assets\logos\上海交通大学.webp  (9168 bytes)\n- gaokao-iframe\assets\logos\中国人民大学.webp  (8728 bytes)\n- gaokao-iframe\assets\logos\中国科学技术大学.webp  (9280 bytes)\n- gaokao-iframe\assets\logos\中山大学.webp  (9072 bytes)\n- gaokao-iframe\assets\logos\北京大学.webp  (5218 bytes)\n- gaokao-iframe\assets\logos\华中科技大学.webp  (3940 bytes)\n- gaokao-iframe\assets\logos\南京大学.webp  (5168 bytes)\n- gaokao-iframe\assets\logos\南开大学.webp  (9290 bytes)\n- gaokao-iframe\assets\logos\哈尔滨工业大学.webp  (7742 bytes)\n- gaokao-iframe\assets\logos\四川大学.webp  (7592 bytes)\n- gaokao-iframe\assets\logos\复旦大学.webp  (8216 bytes)\n- gaokao-iframe\assets\logos\武汉大学.webp  (5832 bytes)\n- gaokao-iframe\assets\logos\浙江大学.webp  (4852 bytes)\n- gaokao-iframe\assets\logos\清华大学.webp  (10062 bytes)\n- gaokao-iframe\assets\logos\西安交通大学.webp  (11652 bytes)\n- gaokao-iframe\assets\relief-cn2.webp  (69044 bytes)\n- gaokao-iframe\assets\zuodong\m2-0.png  (10294 bytes)\n- gaokao-iframe\assets\zuodong\m2-1.png  (26725 bytes)\n- gaokao-iframe\assets\zuodong\m2-2.png  (18749 bytes)\n- gaokao-iframe\assets\zuodong\m3-1.png  (20446 bytes)\n- gaokao-iframe\assets\zuodong\m3-2.png  (35182 bytes)\n- gaokao-iframe\assets\zuodong\spot-hall2-0.png  (6840 bytes)\n- gaokao-iframe\assets\zuodong\spot-hall3-0.png  (7515 bytes)\n- gaokao-iframe\assets\zuodong\spot-pagoda-0.png  (8678 bytes)\n- gaokao-iframe\assets\zuodong\spot-town-0.png  (13633 bytes)\n- gaokao-iframe\gk-engine.js  (13167 bytes)\n- gaokao-iframe\iframe-anon.html  (421497 bytes)\n- gaokao-iframe\vendor\maplibre-gl.css  (70024 bytes)\n- gaokao-iframe\vendor\maplibre-gl.js  (1056837 bytes)\n- login.py  (1397 bytes)\n- login_browser.py  (2031 bytes)\n- outer-anon-stealth.html  (18817 bytes)\n- outer-anon.html  (18079 bytes)\n- probe_login.py  (1107 bytes)\n- probe_submit.py  (1377 bytes)\n- render_local.py  (1342 bytes)\n- screenshot-full.png  (897440 bytes)\n- screenshot-viewport.png  (895073 bytes)\n- try_demo.py  (1154 bytes)\n\n## 总计: 46 个文件, 3,783,626 bytes\n\n## 与本地 Vite 项目对比\n\n### 本地已存在的 (D:\kaifa\gaokao\publicpp-demo\gaokao\index.html)\n\n- public\app-demo\gaokao\index.html  (256 bytes)\n\n### 本地 Vite 源代码 (D:\kaifa\gaokao\src\)\n\n- src\App.jsx  (1795 bytes)\n- src\components\AuthPage.jsx  (2977 bytes)\n- src\components\GaokaoMapPage.jsx  (5116 bytes)\n- src\components\SiteShell.jsx  (1235 bytes)\n- src\lib\auth.js  (2555 bytes)\n- src\main.jsx  (239 bytes)\n- src\styles.css  (5177 bytes)\n- src\test\app.test.jsx  (1496 bytes)\n- src\test\setup.js  (534 bytes)\n\n### 关键差异 (按用途分)\n\n| 项 | 线上真实版 (本次爬) | 本地 Vite 镜像 (你之前搭的) |\n|---|---|---|\n| 框架 | 纯 HTML + vanilla JS + MapLibre GL | React 19 + Vite |\n| 内嵌页体积 | 418KB (DOM) + 30 个静态资源 (1.6MB) | 单一 index.html 静态 |\n| 数据来源 | 实时拉 /api/gaokao/profile、/unis.json、/geo/*.json、/tiles/terrarium/ready | 无后端代理 |\n| 登录 | NextAuth Credentials (返回 401) | 本地占位 |\n| 地图底图 | Carto Voyager + relief-cn2.webp 地形 | 同上（已下载到本地） |\n| 渲染验证 | 浏览器实测 6 canvas/50 button, 渲染正常 | 仅 npm run dev 验证 |\n\n## 没做的事 / 边界\n\n- 登录态: 你给的账号密码 401, 真实账号未知, 没硬爬。\n- 后端 API (/api/gaokao/profile 等) 不在爬虫范围 (要后端代理)。\n- Carto 地图瓦片: 运行时从 /b/c.basemaps.cartocdn.com 拉, 不下载。\n- 15 个大学 logo 引用已从 URL-encoded 改为磁盘中文名。\n

## 怎么用（最终方案：Playwright 路由代理）

serve.py 是入口。**一次性**启动：本地静态服务 + 真实浏览器拉起 + 把所有后端请求通过浏览器 fetch 转发到 https://agentsfeed.org（带着你的 session cookies 走 Cloudflare clearance）。

`powershell
cd D:\kaifa\gaokao\crawled
..\..\Scrapling\.venv\Scripts\python serve.py
`

启动后：
- 后台会打开一个 headless Chromium，**30 秒**内不要关
- 你的 in-app browser / 本地浏览器打开 http://127.0.0.1:8765/iframe-anon.html
- 看到登录态、数据齐全的高考地图页

需要更换 cookies 时，改 serve.py 顶部的 COOKIE_HDR 字符串后重启脚本。

## 服务日志格式

启动后 stdout 一行一个请求，例：
`
[proxy] 200   321595  /app-demo/gaokao/unis.json?v=1
[proxy] 200       16  /api/gaokao/profile
`

200 数字后面是响应字节数。502 或 ERR 说明上游有反爬阻断，需要换 cookies 或加延迟。
