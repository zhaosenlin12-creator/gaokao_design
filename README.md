# 高考志愿填报模拟器 · gaokao_design

> 把全国 1500+ 所大学落在真实山河之上,按分数 / 位次 / 兴趣给冲稳保。

## 项目结构

```
.
├── index.html              # Vite 入口
├── package.json            # 依赖
├── vite.config.js          # Vite 配置
├── src/                    # React 19 + Vite 前端
│   ├── App.jsx             # 路由(landing / auth / app-demo)
│   ├── components/
│   │   ├── AuthPage.jsx
│   │   ├── GaokaoMapPage.jsx
│   │   └── SiteShell.jsx
│   ├── lib/auth.js
│   ├── main.jsx
│   ├── styles.css
│   └── test/
└── crawled/                # 爬取下来的原始前端 + 本地后端
    ├── backend.py          # Python HTTP API (:8787)
    ├── serve.py            # 静态文件服务 (:8765)
    ├── README.md
    └── gaokao-iframe/
        ├── iframe-anon.html    # 主页面(嵌 MapLibre GL + 1596 所大学数据)
        ├── unis.json           # 学校数据
        ├── geo/                # 中国边界 / 省份
        ├── assets/             # 校徽 / 装饰 / 背景音乐
        └── vendor/             # maplibre-gl.js
```

## 怎么跑(本地完整版)

需要 Python 3.10+。

### 1. 安装前端依赖
```bash
npm install
```

### 2. 启动后端 API(端口 8787)
```bash
python crawled/backend.py
```

### 3. 启动静态服务(端口 8765)
```bash
python crawled/serve.py
```

### 4. 打开页面
http://127.0.0.1:8765/iframe-anon.html

### 5. (可选)Vite 开发模式
```bash
npm run dev
```

## 数据来源

- 静态数据:`crawled/gaokao-iframe/unis.json`(1596 所学校)
- 地图瓦片:本地 `crawled/gaokao-iframe/tiles/`(可选,否则用 cartocdn 在线)
- 风格:古风 MapLibre GL 主题
