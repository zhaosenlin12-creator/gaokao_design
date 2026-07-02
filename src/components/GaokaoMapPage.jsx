import { useMemo, useState } from "react";

const stats = [
  { value: "32", label: "模拟省份" },
  { value: "128", label: "院校条目" },
  { value: "6", label: "兴趣维度" },
];

const recommendationRows = [
  { label: "省份推荐", value: "按地区和位次分层展示冲稳保" },
  { label: "分数策略", value: "结合近三年投档线和层次偏好" },
  { label: "专业方向", value: "围绕 RIASEC 兴趣测评给出匹配建议" },
];

const riasec = [
  ["R", "现实型", "动手、工程、设备"],
  ["I", "研究型", "分析、推理、探索"],
  ["A", "艺术型", "表达、设计、创造"],
  ["S", "社会型", "沟通、助人、协作"],
  ["E", "企业型", "组织、带动、决策"],
  ["C", "常规型", "秩序、执行、细致"],
];

const mapSchools = [
  { tag: "冲", name: "重点本科", desc: "冲刺与稳妥的交叉层" },
  { tag: "稳", name: "地方公办", desc: "兼顾分数和城市" },
  { tag: "保", name: "特色院校", desc: "专业适配优先" },
  { tag: "荐", name: "高潜志愿", desc: "结合兴趣和发展路径" },
];

export default function GaokaoMapPage() {
  const [introOpen, setIntroOpen] = useState(true);
  const data = useMemo(() => stats, []);

  return (
    <main className="demo-page">
      <section className="demo-hero">
        <div className="demo-hero-copy">
          <a className="back-link" href="/app-demo">全部演示</a>
          <h1>山河志愿 · 高考志愿填报模拟器</h1>
          <p>按省份与分数推荐冲稳保院校，含 RIASEC 兴趣测评、古地图风格的中国升学地图。</p>
          <a className="open-link" href="/app-demo/gaokao/index.html" target="_blank" rel="noreferrer">
            在新标签页打开
          </a>
        </div>
      </section>

      {introOpen ? (
        <section className="intro-modal" role="dialog" aria-modal="true" aria-label="欢迎来到高考志愿填报模拟器">
          <button className="close-intro" type="button" onClick={() => setIntroOpen(false)}>跳过引导</button>
          <h2>欢迎来到高考志愿填报模拟器</h2>
          <p>山河为卷，按分数选大学、按兴趣选专业。不如先——</p>
          <button className="primary-btn" type="button">开始测评 · 约 1 分钟 →</button>
          <button className="secondary-btn" type="button">填分数找院校</button>
          <button className="secondary-btn" type="button" onClick={() => setIntroOpen(false)}>不测，直接看</button>
          <label className="music-toggle">
            <input type="checkbox" defaultChecked />
            <span>🎵 播放古典配乐</span>
          </label>
        </section>
      ) : null}

      <section className="stats-grid">
        {data.map((item) => (
          <article className="stat-card" key={item.label}>
            <strong>{item.value}</strong>
            <span>{item.label}</span>
          </article>
        ))}
      </section>

      <section className="control-bar">
        <button className="ghost-pill" type="button">★ 志愿表 0</button>
        <button className="ghost-pill" type="button">今日签</button>
        <button className="ghost-pill" type="button">按省份聚焦地图</button>
        <button className="ghost-pill active" type="button">全国</button>
        <button className="ghost-pill" type="button">全部院校</button>
        <button className="ghost-pill" type="button">985 巡礼</button>
        <button className="ghost-pill" type="button">211·双一流</button>
        <button className="ghost-pill" type="button">计算机</button>
        <button className="ghost-pill" type="button">医学</button>
        <button className="ghost-pill" type="button">财经法学</button>
      </section>

      <section className="demo-grid">
        <article className="panel">
          <p className="section-kicker">省份推荐</p>
          {recommendationRows.map((row) => (
            <div className="row-item" key={row.label}>
              <strong>{row.label}</strong>
              <span>{row.value}</span>
            </div>
          ))}
        </article>

        <article className="panel">
          <p className="section-kicker">RIASEC 兴趣</p>
          <div className="riasec-grid">
            {riasec.map(([key, title, desc]) => (
              <div className="riasec-card" key={key}>
                <strong>{key}</strong>
                <span>{title}</span>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="map-panel">
        <div className="map-head">
          <p className="section-kicker">古地图</p>
          <h2>中国升学地图</h2>
        </div>
        <div className="map-grid">
          {mapSchools.map((school) => (
            <article className="map-card" key={school.name}>
              <span>{school.tag}</span>
              <strong>{school.name}</strong>
              <p>{school.desc}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
