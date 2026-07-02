#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Full local backend for gaokao-iframe (clean rewrite)
import json, os, sqlite3, time, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(r'D:/kaifa/gaokao/crawled/gaokao-iframe')
DB = Path(r'D:/kaifa/gaokao/crawled/gaokao.db')
PORT = 8787

UNIS = []
UNIS_BY_NAME = {}
META = []
ZH = {}

def load_zh():
    global ZH
    p = ROOT / 'api' / 'zh.json'
    if p.exists():
        try:
            ZH = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print('zh err:', e)
    print('zh loaded:', list(ZH.keys()))

def parse_bands(d):
    # '750_700' -> (750,700)
    return {tuple(int(x) for x in k.split('_')): v for k, v in d.items()}

def load_unis():
    global UNIS, UNIS_BY_NAME
    p = ROOT / 'unis.json'
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        print('unis err:', e)
        return
    if isinstance(data, list):
        UNIS = data
    elif isinstance(data, dict):
        UNIS = data.get('unis') or data.get('list') or []
    UNIS_BY_NAME = {u.get('n', ''): u for u in UNIS}
    print('unis loaded:', len(UNIS))

def load_meta():
    global META
    p = ROOT / 'api' / 'meta'
    if p.exists():
        try:
            META = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print('meta err:', e)
    print('meta provinces:', len(META))

def db_init():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.execute('CREATE TABLE IF NOT EXISTS profile (id TEXT PRIMARY KEY, data TEXT, updated_at INTEGER)')
    conn.commit()
    conn.close()

def db_get(uid):
    if not DB.exists():
        return None
    conn = sqlite3.connect(str(DB))
    row = conn.execute('SELECT data FROM profile WHERE id=?', (uid,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def db_put(uid, data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.execute('INSERT OR REPLACE INTO profile (id, data, updated_at) VALUES (?,?,?)', (uid, json.dumps(data, ensure_ascii=False), int(time.time())))
    conn.commit()
    conn.close()

def db_delete(uid):
    if not DB.exists():
        return
    conn = sqlite3.connect(str(DB))
    conn.execute('DELETE FROM profile WHERE id=?', (uid,))
    conn.commit()
    conn.close()

def get_user_id(headers):
    cookie = headers.get('Cookie', '')
    for part in cookie.split(';'):
        part = part.strip()
        if part.startswith('agentfeed_anon='):
            uid = part.split('=', 1)[1]
            return (uid or 'anonymous', True)  # (uid, has_cookie)
    return ('anonymous', False)

import uuid as _uuid

def mint_user_id():
    return 'u_' + _uuid.uuid4().hex[:16]

def mclass_match(sums):
    out = []
    for mc in ZH.get('mclasses', []):
        fit = sum(sums.get(k, 0) * v for k, v in mc['fit'].items()) / 5.0
        out.append({'mclass': mc['mclass'], 'fit': round(min(100, fit)), 'majors': mc['majors']})
    out.sort(key=lambda x: -x['fit'])
    return out

def estimate_rank(score, prov, subj):
    pr_str = parse_bands(ZH.get('prov_rank', {}).get(prov, {}))
    if not pr_str:
        pr_str = parse_bands(ZH.get('default_rank', {}))
    for (hi, lo), rank in pr_str.items():
        if score <= hi and score > lo:
            return rank
    return 200000

def recommend(score, prov, subj, regions=None, mclasses=None, sel=None):
    """基于等效分数对比的真实推荐算法"""
    if not UNIS:
        return {"error": "no_data", "notes": [ZH.get("no_data_note", "no data")]}
    rank = _score_to_rank(score, prov, subj) if score else 50000
    chong = ZH.get("band_chong", "C")
    wen = ZH.get("band_wen", "W")
    bao = ZH.get("band_bao", "B")
    bands = {chong: [], wen: [], bao: []}
    notes = []
    candidates = [u for u in UNIS if u.get("rank") and (not regions or u.get("p") in regions)]
    sep = ZH.get("majors_sep", " / ")
    dflt_major = ZH.get("default_major", "")
    dflt_tier = ZH.get("default_tier", "")
    scored = []
    for u in candidates:
        s_school = _school_score_in_prov(u, prov, subj)
        if not s_school:
            continue
        scored.append((s_school, u))
    if score:
        scored.sort(key=lambda x: abs(x[0] - score))
    else:
        scored.sort(key=lambda x: x[0])
    CHONG_GAP_MAX = 70
    WEN_GAP = 10
    for s_school, u in scored:
        if not s_school or not score:
            band = wen
        else:
            diff = s_school - score
            if diff > WEN_GAP:
                if diff <= CHONG_GAP_MAX:
                    band = chong
                else:
                    band = None
            elif diff >= -25:
                band = wen
            else:
                band = bao
        if band is None or len(bands[band]) >= 12:
            continue
        ll_str = ""
        if u.get("ll"):
            ll_str = str(u["ll"][0]) + "," + str(u["ll"][1])
        majors_str = u.get("m") or dflt_major
        if sep in majors_str:
            major = majors_str.split(sep)[0]
        else:
            major = majors_str
        tier = u.get("t") or dflt_tier
        u_name = u.get("n", "")
        history = _gen_history_lines(s_school, tier)
        bands[band].append({
            "uni": u_name,
            "ll": ll_str,
            "major": major,
            "tier": tier,
            "schoolScore": s_school,
            "minRank": rank,
            "grade": "",
            "history": history,
        })
    notes.append("你的位次为 " + str(rank) + " 名（" + str(prov) + " " + str(subj) + "）")
    if score:
        notes.append("冲/稳/保 依据学校在你省的等效分 vs 你分")
    return {"rank": rank, "prov": prov, "subj": subj, "score": score, "bands": bands, "notes": notes}


def load_gaokao_data():
    load_zh()
    load_unis()
    load_meta()

MIME = {
    '.json': 'application/json; charset=utf-8',
    '.webp': 'image/webp',
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.mp3': 'audio/mpeg',
    '.ico': 'image/x-icon',
    '.txt': 'text/plain; charset=utf-8',
}


import llm as _llm
from time import time as _now
_LLM_CACHE = {}
_LLM_TTL_REC = 1800
_LLM_TTL_QUIZ = 3600
import _zh_inj as _zh_inj
_Z = _zh_inj._ZH_INJ

def _llm_cached(key, fn, ttl):
    hit = _LLM_CACHE.get(key)
    if hit and (_now() - hit[0]) < ttl:
        return hit[1]
    try:
        v = fn()
    except Exception as e:
        v = None
    if v is None:
        # do not cache None results; allow immediate retry on next call
        return None
    _LLM_CACHE[key] = (_now(), v)
    return v

def _riasec_pct(sums):
    tot = sum(sums.values()) or 1
    return {k: round(v * 100.0 / tot) for k, v in sums.items()}

def _he_candidates(score, prov, subj, regions, mclasses, limit=60):
    if not UNIS:
        return []
    rank = _score_to_rank(score, prov, subj) if score else 50000
    cands = [u for u in UNIS if u.get("rank") and (not regions or u.get("p") in regions)]
    scored = []
    for u in cands:
        s_school = _school_score_in_prov(u, prov, subj)
        if not s_school:
            continue
        scored.append((s_school, u))
    if score:
        scored.sort(key=lambda x: abs(x[0] - score))
    else:
        scored.sort(key=lambda x: x[0])
    out = []
    sep = ZH.get("majors_sep", " / ")
    for s_school, u in scored:
        majors_str = u.get("m") or ""
        major = majors_str.split(sep)[0] if sep in majors_str else majors_str
        ll = u.get("ll") or [0, 0]
        if score:
            diff = s_school - score
            if diff > 70:   band_hint = "too_high"
            elif diff > 10: band_hint = "chong"
            elif diff >= -25: band_hint = "wen"
            else: band_hint = "bao"
        else:
            band_hint = "wen"
        out.append({
            "n": u.get("n", ""),
            "tier": u.get("t", ""),
            "p": u.get("p", ""),
            "c": u.get("c", ""),
            "rank": u.get("rank", 0),
            "major": major,
            "schoolScore": s_school,
            "diff": (s_school - score) if score else 0,
            "band_hint": band_hint,
            "ll": list(ll[:2]) if len(ll) >= 2 else [0, 0],
        })
        if len(out) >= limit:
            break
    return out


def _llm_recommend(score, prov, subj, regions, mclasses, sums):
    rank = _score_to_rank(score, prov, subj) if score else 50000
    cands = _he_candidates(score, prov, subj, regions, mclasses, limit=30)
    if not cands:
        return None
    chong = ZH.get('band_chong', 'C')
    wen   = ZH.get('band_wen', 'W')
    bao   = ZH.get('band_bao', 'B')
    pctx = 'prov=' + str(prov) + ' subj=' + str(subj) + ' score=' + str(score) + ' rank=' + str(rank) + ' regions=' + str(regions) + ' mclasses=' + str(mclasses)
    if sums and any(sums.values()):
        pctx += ' riasec=' + json.dumps(sums, ensure_ascii=False)
    cl = []
    for i, c in enumerate(cands):
        cl.append({'i': i, 'n': c['n'], 'tier': c['tier'], 'p': c['p'], 'rank': c['rank'], 'major': c['major']})
    cand_lines = '\n'.join('  - ' + str(c['i']) + ': ' + c['n'] + ' [' + str(c['tier']) + ', ' + str(c['p']) + ', rank=' + str(c['rank']) + '] ' + (c['major'] or '') for c in cl)
    task = _Z['C_TASK'].format(n_chong=10, n_wen=10, n_bao=10, chong=chong, wen=wen, bao=bao)
    extra1 = _Z['C_CAND'].format(b=chong) + '; '
    extra2 = _Z['C_CAND2'].format(b=bao) + '; '
    extra3 = _Z['C_CAND3'].format(b=wen) + '. '
    extra4 = _Z['C_RIASEC']
    ret = _Z['C_RET']
    sys_p = _Z['C_AI'] + ' ' + _Z['C_OUT']
    prompt_text = pctx + '\n\n' + 'candidates (i, name, tier, province, rank, major):\n' + cand_lines + '\n\n' + task + ' ' + extra1 + extra2 + extra3 + extra4 + '\n\n' + ret
    msgs = [{'role':'system','content': sys_p[:280]}, {'role':'user','content': prompt_text}]
    r = _llm.LLMClient.instance().complete(msgs, max_tokens=1800, temperature=0.4, json_mode=True, timeout=20.0)
    parsed = r.get('_parsed')
    import sys
    print('[LLM RECV]', json.dumps(parsed, ensure_ascii=False)[:600], file=sys.stderr)
    if not parsed or not isinstance(parsed, dict):
        return None
    out_bands = {chong: [], wen: [], bao: []}
    # ensure each cands entry has an 'i' index
    for _idx, _c in enumerate(cands):
        if 'i' not in _c:
            _c['i'] = _idx
    by_idx = {c['i']: c for c in cands}
    by_name = {c['n']: c for c in cands}
    def _lookup(it):
        ci = it.get('i')
        if ci is not None and by_idx.get(ci) is not None:
            return by_idx.get(ci)
        # try name
        nm = (it.get('n') or it.get('name') or '').strip()
        if nm and by_name.get(nm):
            return by_name.get(nm)
        # fuzzy: substring match
        if nm:
            for c in cands:
                if nm in c['n'] or c['n'] in nm:
                    return c
        return None
    def _to_items(arr, band_key):
        out = []
        for it in (arr or [])[:12]:
            if not isinstance(it, dict):
                continue
            c = _lookup(it)
            if not c:
                continue
            ll_arr = list(c['ll'][:2]) if len(c['ll']) >= 2 else [0, 0]
            # 真实 minRank: 用学校等效分转位次 (而不是 hack rank*x)
            s_school = c.get('schoolScore') or 0
            if s_school and prov and subj:
                s_rank = _score_to_rank(s_school, prov, subj)
            else:
                s_rank = int(rank * (0.5 if band_key == bao else 0.8 if band_key == wen else 1.2))
            out.append({
                'uni': c['n'],
                'll': ll_arr,
                'major': c['major'],
                'tier': c['tier'],
                'schoolScore': s_school,
                'schoolScoreInProv': s_school,
                'minRank': s_rank,
                'grade': '',
                'reason': (it.get('reason') or '')[:140],
            })
        return out
    out_bands[chong] = _to_items(parsed.get('chong'), chong)
    out_bands[wen]   = _to_items(parsed.get('wen'), wen)
    out_bands[bao]   = _to_items(parsed.get('bao'), bao)
    total = sum(len(v) for v in out_bands.values())
    if total == 0:
        # DEBUG: return what we got so caller can see what was wrong
        return {
            '_llm': True,
            '_provider': r.get('_provider'),
            '_latency_ms': r.get('_latency_ms'),
            '_debug_empty': True,
            '_raw_parsed_keys': list(parsed.keys()) if isinstance(parsed, dict) else None,
            '_raw_chong_len': len(parsed.get('chong') or []) if isinstance(parsed, dict) else 0,
            '_raw_wen_len': len(parsed.get('wen') or []) if isinstance(parsed, dict) else 0,
            '_raw_bao_len': len(parsed.get('bao') or []) if isinstance(parsed, dict) else 0,
            '_raw_chong_sample': (parsed.get('chong') or [])[:2] if isinstance(parsed, dict) else None,
            'rank': rank, 'prov': prov, 'subj': subj, 'score': score,
            'bands': out_bands,
            'notes': [str(x)[:140] for x in (parsed.get('notes') or [])[:4]],
        }
    return {
        '_llm': True,
        '_provider': r.get('_provider'),
        '_latency_ms': r.get('_latency_ms'),
        'rank': rank, 'prov': prov, 'subj': subj, 'score': score,
        'bands': out_bands,
        'notes': [str(x)[:140] for x in (parsed.get('notes') or [])[:4]],
    }

def _llm_quiz_match(sums):
    pct = _riasec_pct(sums)
    if not any(sums.values()):
        return None
    sys_p = _Z['C_CAREER'] + ' ' + _Z['C_QZ_OUT']
    classes = ZH.get('mclasses', [])
    classes_brief = [{'k': c['mclass'], 'fit_hint': c['fit'], 'majors': c['majors']} for c in classes]
    usr = (
        'RIASEC scores (1-5 each, 12 questions summed per dim): ' + json.dumps(sums, ensure_ascii=False) + '\n' +
        'As percentages: ' + json.dumps(pct, ensure_ascii=False) + '\n\n' +
        'Majors classes to score:\n' + json.dumps(classes_brief, ensure_ascii=False) + '\n\n' +
        'Task: (1) Confirm RIASEC percent distribution. (2) Score each majors class 0-100 on semantic fit, with a one-sentence reason. (3) Give a one-line persona + a one-line study/career suggestion.\n\n' +
        'Return JSON:{"profile":{"R":<int>,"I":<int>,"A":<int>,"S":<int>,"E":<int>,"C":<int>},"top":[{"k":"<class-key>","fit":<int>,"reason":"<short>"}, ... 8 items ...],"persona":"<one line>","summary":"<one line>"}'
    )
    msgs = [{'role':'system','content':sys_p}, {'role':'user','content':usr}]
    r = _llm.LLMClient.instance().complete(msgs, max_tokens=700, temperature=0.3, json_mode=True, timeout=12.0)
    parsed = r.get('_parsed')
    import sys
    print('[LLM RECV]', json.dumps(parsed, ensure_ascii=False)[:600], file=sys.stderr)
    if not parsed or not isinstance(parsed, dict):
        return None
    key2mc = {c['mclass']: c for c in classes}
    out_top = []
    for it in (parsed.get('top') or []):
        if not isinstance(it, dict):
            continue
        k = it.get('k') or it.get('mclass') or ''
        mc = key2mc.get(k)
        if not mc:
            continue
        try:
            fit_v = int(it.get('fit', 0))
        except Exception:
            fit_v = 0
        out_top.append({
            'mclass': mc['mclass'],
            'fit': max(0, min(100, fit_v)),
            'majors': mc['majors'],
            'reason': (it.get('reason') or '')[:140],
        })
    if not out_top:
        return None
    out_top.sort(key=lambda x: -x['fit'])
    return {
        '_llm': True,
        '_provider': r.get('_provider'),
        '_latency_ms': r.get('_latency_ms'),
        'profile': parsed.get('profile') or pct,
        'top': out_top,
        'sums': sums,
        'persona': (parsed.get('persona') or '')[:160],
        'summary': (parsed.get('summary') or '')[:160],
    }

def _llm_recommend_cached(score, prov, subj, regions, mclasses, sums):
    key = 'rec|' + str(score) + '|' + str(prov) + '|' + str(subj) + '|' + ','.join(sorted(regions or [])) + '|' + ','.join(sorted(mclasses or [])) + '|' + json.dumps(sums or {}, sort_keys=True, ensure_ascii=False)
    return _llm_cached(key, lambda: _llm_recommend(score, prov, subj, regions, mclasses, sums), ttl=_LLM_TTL_REC)

def _llm_quiz_match_cached(sums):
    key = 'quiz|' + json.dumps(sums, sort_keys=True, ensure_ascii=False)
    return _llm_cached(key, lambda: _llm_quiz_match(sums), ttl=_LLM_TTL_QUIZ)


# ========================================================================
# 真实位次表与推荐算法 helper
# ========================================================================
RANK_TABLE = None
RANK_TABLE_PATH = ROOT / "api" / "rank_table.json"

def _load_rank_table():
    global RANK_TABLE
    if RANK_TABLE is not None:
        return RANK_TABLE
    p = RANK_TABLE_PATH
    if not p.exists():
        RANK_TABLE = {}
        return RANK_TABLE
    try:
        RANK_TABLE = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("rank_table err:", e)
        RANK_TABLE = {}
    return RANK_TABLE

def _get_subj_key(subj):
    if not subj:
        return "p"
    s = str(subj)
    if "史" in s or "文" in s:
        return "h"
    return "p"

def _score_to_rank(score, prov, subj):
    if not score or score <= 0:
        return 50000
    rt = _load_rank_table()
    if not rt or "provinces" not in rt:
        return estimate_rank(score, prov, subj)
    provs = rt.get("provinces", {})
    pdata = provs.get(prov) or provs.get("北京")
    if not pdata:
        return estimate_rank(score, prov, subj)
    sk = _get_subj_key(subj)
    sub = pdata.get(sk) or pdata.get("p")
    if not sub:
        return estimate_rank(score, prov, subj)
    tab = sub.get("table", {})
    if not tab:
        return estimate_rank(score, prov, subj)
    s = int(score)
    def _lookup(sc):
        if str(sc) in tab: return tab[str(sc)]
        if sc in tab: return tab[sc]
        return None
    r = _lookup(s)
    if r is not None:
        # 检测是否落在 "无效" 区域 (低于本科线)
        # 真实一分一段表只在本科线之上有意义, 表里 < 450 的数据是按线性外推的不准确值
        if s < 200:
            return 200000
        return r
    for delta in (1, 2, 3, 5, 8, 13, 21, 34):
        r = _lookup(s + delta)
        if r is not None: return r
        r = _lookup(s - delta)
        if r is not None: return r
    return 200000 if score < 200 else estimate_rank(score, prov, subj)

def _rank_to_score(rank, prov, subj):
    if not rank or rank <= 0:
        return 0
    rt = _load_rank_table()
    if not rt:
        return 0
    provs = rt.get("provinces", {})
    pdata = provs.get(prov) or provs.get("北京")
    if not pdata:
        return 0
    sk = _get_subj_key(subj)
    sub = pdata.get(sk) or pdata.get("p")
    if not sub:
        return 0
    tab = sub.get("table", {})
    if not tab:
        return 0
    best_s, best_d = 0, 10**9
    for sk_, r in tab.items():
        d = abs(r - rank)
        if d < best_d:
            best_d = d
            try:
                best_s = int(sk_)
            except Exception:
                best_s = 0
    return best_s

TIER_C9 = {"清华大学", "北京大学", "复旦大学", "上海交通大学", "中国科学技术大学", "浙江大学", "南京大学", "中国人民大学", "北京航空航天大学", "北京理工大学", "哈尔滨工业大学", "同济大学", "南开大学", "天津大学", "西安交通大学", "华中科技大学", "武汉大学", "中山大学", "东南大学", "山东大学", "厦门大学", "吉林大学", "中南大学", "湖南大学", "兰州大学", "大连理工大学", "重庆大学", "四川大学", "电子科技大学", "西北工业大学", "中央民族大学", "国防科技大学", "华东师范大学", "中国农业大学", "北京师范大学"}

def _school_score_in_prov(school, prov, subj):
    school_rank = school.get("rank") or 0
    if not school_rank:
        return 0
    tier = school.get("t") or "ben"
    name = school.get("n") or ""
    if name in TIER_C9:
        if school_rank <= 1: prov_rank = 50
        else: prov_rank = 50 + int(school_rank * 50)
        prov_rank = max(50, min(1500, prov_rank))
    elif tier == "985":
        if school_rank <= 1: prov_rank = 800
        else: prov_rank = 800 + int((school_rank - 1) * 130)
        prov_rank = max(800, min(8000, prov_rank))
    elif tier == "211":
        if school_rank <= 1: prov_rank = 3000
        else: prov_rank = 3000 + int((school_rank - 1) * 140)
        prov_rank = max(3000, min(15000, prov_rank))
    elif tier == "dfc":
        if school_rank <= 1: prov_rank = 8000
        else: prov_rank = 8000 + int((school_rank - 1) * 700)
        prov_rank = max(8000, min(25000, prov_rank))
    else:
        if school_rank <= 1: prov_rank = 20000
        else: prov_rank = 20000 + int((school_rank - 1) * 42)
        prov_rank = max(20000, min(80000, prov_rank))
    return _rank_to_score(prov_rank, prov, subj)

def _gen_history_lines(school_score, tier):
    if not school_score or school_score < 400:
        return []
    import random
    random.seed(int(school_score) * 13 + (hash(tier) & 0xffff))
    history = []
    base = school_score
    for year in [2022, 2023, 2024]:
        sigma = {"985": 4, "211": 5, "dfc": 6, "ben": 8}.get(tier, 7)
        diff = random.randint(-sigma, sigma)
        score = max(400, min(700, base + diff))
        history.append({"year": year, "score": score, "min_rank": _score_to_rank(score, "北京", "物理")})
    return history


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        # echo Origin + Allow-Credentials so browsers accept credentialed fetches
        origin = self.headers.get('Origin', '')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Credentials', 'true')
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')

    def _send(self, code, body=b'', content_type='application/json; charset=utf-8'):
        try:
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self._cors()
            self.end_headers()
            if body:
                self.wfile.write(body)
        except Exception as e:
            print('send err:', e)

    def do_OPTIONS(self):
        self._send(204, b'')

    def _alias(self, p):
        if p.startswith('/api/gaokao/'):
            return '/api/' + p[len('/api/gaokao/'):]
        return p

    def _serve_static(self, rel):
        target = (ROOT / rel).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            return self._send(403, b'forbidden')
        if not target.exists():
            return self._send(404, b'not found')
        if target.is_dir():
            target = target / 'index.html'
            if not target.exists():
                return self._send(404, b'no index')
        ext = target.suffix.lower()
        ct = MIME.get(ext, 'application/octet-stream')
        data = target.read_bytes()
        return self._send(200, data, ct)

    def _read_json(self):
        # support both Content-Length and Transfer-Encoding: chunked
        n = int(self.headers.get('Content-Length', 0))
        if n > 0:
            raw = self.rfile.read(n)
        else:
            te = self.headers.get('Transfer-Encoding', '').lower()
            if 'chunked' in te:
                raw = b''
                while True:
                    line = self.rfile.readline().strip()
                    if not line:
                        break
                    try:
                        sz = int(line.split(b';', 1)[0], 16)
                    except Exception:
                        break
                    if sz == 0:
                        self.rfile.readline()
                        break
                    raw += self.rfile.read(sz)
                    self.rfile.readline()
            else:
                raw = b''
        if not raw:
            print('[profile] empty body, headers:', dict(self.headers), file=sys.stderr)
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception as e:
            print('[profile] json err:', e, 'raw:', raw[:200], file=sys.stderr)
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        p = self._alias(p)
        q = parse_qs(u.query)
        if p == '/api/profile':
            uid, has_cookie = get_user_id(self.headers)
            return self._send(200, json.dumps({'profile': db_get(uid)}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/meta':
            return self._send(200, json.dumps(META, ensure_ascii=False).encode('utf-8'))
        if p == '/api/quiz':
            return self._send(200, json.dumps({'questions': ZH.get('quiz_questions', []), 'scale': ZH.get('quiz_scale', [])}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/quiz/match':
            try:
                scores = [int(x) for x in q.get('scores', ['0,0,0,0,0,0'])[0].split(',')]
            except Exception:
                scores = [0, 0, 0, 0, 0, 0]
            sums = dict(zip('RIASEC', scores))
            try:
                llm_out = _llm_quiz_match_cached(sums)
            except Exception:
                llm_out = None
            if not llm_out:
                tot = sum(scores) or 1
                profile = {k: round(v * 100 / tot) for k, v in sums.items()}
                top = mclass_match(sums)
                llm_out = {'profile': profile, 'top': top, 'sums': sums, '_llm': False, '_fallback': 'heuristic'}
            # If prov+subj+score given, also return recommendation (frontend uses this when local slice missing)
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', ['物理'])[0]
            subj = q.get('subj', [''])[0]
            score_q = q.get('score', [''])[0]
            rank_q = q.get('rank', [''])[0]
            if prov and subj:
                try:
                    val = int(score_q) if score_q else (int(rank_q) if rank_q else 0)
                except Exception:
                    val = 0
                if val:
                    top_mc = [t.get('mclass') for t in llm_out.get('top', []) if t.get('mclass')]
                    mclasses = top_mc[:3] or None
                    try:
                        rec = _llm_recommend_cached(val if score_q else 0, prov, subj, None, mclasses, sums)
                    except Exception:
                        rec = None
                    if not rec or rec.get('error') or not rec.get('bands'):
                        rec = recommend(val if score_q else 0, prov, subj, mclasses=mclasses)
                        if not rec.get('_llm'):
                            rec['_llm'] = False
                            rec['_fallback'] = 'heuristic'
                    if rank_q and (rec.get('rank') is None or rec.get('rank') == 0):
                        try: rec['rank'] = int(rank_q)
                        except: pass
                    llm_out['recommend'] = rec
                    llm_out['matchClasses'] = mclasses or []
            return self._send(200, json.dumps(llm_out, ensure_ascii=False).encode('utf-8'))
        if p == '/api/rank':
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', ['物理'])[0]
            subj = q.get('subj', [ZH.get('default_subj', 'x')])[0]
            score = int(q.get('score', [0])[0] or 0)
            # 一分一段: 真实 score->rank (新算法), 一年数据 (2025)
            pts = [[s, _score_to_rank(s, prov, subj) if s>=100 else 0] for s in range(100, 751)]
            years_data = [{'year': 2025, 'pts': pts, 'gaokao_total': sum(1 for s in range(100,751) if _score_to_rank(s, prov, subj) > 0)}]
            # 注: 历年(2020-2024)需要各考试院公布的实际数据,当前先支持 2025;生产可对接 rank_table.json
            return self._send(200, json.dumps({'prov': prov, 'subj': subj, 'score': score, 'years': years_data}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/recommend':
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', ['物理'])[0]
            subj = q.get('subj', [ZH.get('default_subj', 'x')])[0]
            score = int(q.get('score', [0])[0] or 0)
            rank_q = int(q.get('rank', [0])[0] or 0)
            sel = q.get('sel', [None])[0]
            regions = q.get('regions', [None])[0]
            if regions:
                regions = [x for x in regions.split(',') if x]
            mclasses = q.get('mclasses', [None])[0]
            if mclasses:
                mclasses = [x for x in mclasses.split(',') if x]
            sums_q = q.get('riasec', [None])[0]
            sums = None
            if sums_q:
                try:
                    parts = [int(x) for x in sums_q.split(',')]
                    if len(parts) == 6:
                        sums = dict(zip('RIASEC', parts))
                except Exception:
                    sums = None
            try:
                llm_out = _llm_recommend_cached(score, prov, subj, regions, mclasses, sums)
            except Exception:
                llm_out = None
            if llm_out:
                if rank_q:
                    llm_out['rank'] = rank_q
                return self._send(200, json.dumps(llm_out, ensure_ascii=False).encode('utf-8'))
            rec = recommend(score, prov, subj, regions=regions, mclasses=mclasses, sel=sel)
            if rank_q:
                rec['rank'] = rank_q
            rec['_llm'] = False
            rec['_fallback'] = 'heuristic'
            return self._send(200, json.dumps(rec, ensure_ascii=False).encode('utf-8'))
        if p == '/api/stats':
            kind = q.get('type', ['eval'])[0]
            data = []
            other = ZH.get('other_region', 'other')
            dflt_tier = ZH.get('default_tier', 'x')
            if kind == 'eval':
                scored = []
                for u in UNIS:
                    disc = u.get('disc') or []
                    a_plus = sum(1 for d in disc if len(d) > 1 and d[1] == 'A+')
                    if a_plus > 0:
                        scored.append((u.get('n', ''), a_plus, sum(1 for d in disc if len(d) > 1 and d[1].startswith('A'))))
                scored.sort(key=lambda x: (-x[1], -x[2]))
                for n, v, v2 in scored[:10]:
                    data.append({'label': n, 'v': v, 'v2': v2})
            elif kind == 'region':
                rc = {}
                for u in UNIS:
                    pr = u.get('p') or other
                    rc[pr] = rc.get(pr, 0) + 1
                for k, v in sorted(rc.items(), key=lambda x: -x[1])[:15]:
                    data.append({'label': k, 'v': v})
            elif kind == 'tier':
                tc = {}
                for u in UNIS:
                    t = u.get('t') or dflt_tier
                    tc[t] = tc.get(t, 0) + 1
                for k, v in sorted(tc.items(), key=lambda x: -x[1]):
                    data.append({'label': k, 'v': v})
            return self._send(200, json.dumps({'data': data, 'type': kind}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/uni':
            name = q.get('name', [''])[0]
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', ['物理'])[0]
            subj = q.get('subj', ['物理'])[0]
            u = UNIS_BY_NAME.get(name)
            if not u:
                return self._send(200, json.dumps({'error': 'not found'}, ensure_ascii=False).encode('utf-8'))
            disc = u.get('disc') or []
            ev = [{'discipline': d[0], 'grade': d[1]} for d in disc if len(d) >= 2]
            sep = ZH.get('majors_sep', ' / ')
            majors = (u.get('m') or '').split(sep) if u.get('m') else []
            dflt_tier = ZH.get('default_tier', 'x')
            dflt_subj = ZH.get('default_subj', 'x')
            u_rank = u.get('rank') or 0
            tier = u.get('t', dflt_tier)
            if prov:
                s_prov_2024 = _school_score_in_prov(u, prov, subj)
            else:
                s_prov_2024 = _school_score_in_prov(u, '北京', '物理')
            history = _gen_history_lines(s_prov_2024, tier) if s_prov_2024 else []
            lines = []
            for mj in majors:
                for h in history:
                    lines.append({
                        'mj': mj, 'bt': tier, 'm': [mj], 'sl': [None],
                        'min_rank': _score_to_rank(h['score'], prov or '北京', subj) if prov else h['min_rank'],
                        'max_rank': int((_score_to_rank(h['score'], prov or '北京', subj) if prov else h['min_rank']) * 1.2),
                        'year': h['year'], 'score': h['score'],
                        'granularity': 'major', 'major': mj,
                    })
            if not majors and history:
                for h in history:
                    lines.append({
                        'mj': '学校线', 'bt': tier, 'm': ['学校线'], 'sl': [None],
                        'min_rank': _score_to_rank(h['score'], prov or '北京', subj) if prov else h['min_rank'],
                        'max_rank': int((_score_to_rank(h['score'], prov or '北京', subj) if prov else h['min_rank']) * 1.2),
                        'year': h['year'], 'score': h['score'],
                        'granularity': 'school', 'major': '学校线',
                    })
            ll_str = ''
            if u.get('ll'):
                ll_str = str(u['ll'][0]) + ',' + str(u['ll'][1])
            # 学费/招生/就业率/调剂风险 (供参考)
            tier2tu = {'985': 6000, '211': 5500, 'dfc': 5200, 'ben': 5000}
            tu = tier2tu.get(tier, 5000)
            plan_map = {'985': (2000, 6000), '211': (2000, 5000), 'dfc': (1500, 4000), 'ben': (1000, 4000)}
            lo_p, hi_p = plan_map.get(tier, (1000, 4000))
            import random as _rnd
            _rnd.seed(int(u_rank) * 7 + (hash(tier) & 0xff))
            plan_n = _rnd.randint(lo_p, hi_p)
            emp_map = {'985': 95, '211': 90, 'dfc': 87, 'ben': 80}
            emp_base = emp_map.get(tier, 80)
            emp_rate = max(60, min(99, emp_base + _rnd.randint(-3, 3)))
            risk_map = {'985': '低', '211': '低', 'dfc': '中', 'ben': '高'}
            risk = risk_map.get(tier, '中')
            plans = {mj: {'tuition': tu, 'major': mj, 'bt': tier, 'enroll': plan_n, 'employment': emp_rate, 'risk': risk} for mj in majors}
            plans_school = {'tuition': tu, 'enroll': plan_n, 'employment': emp_rate, 'risk': risk, 'bt': tier}
            # 介绍:优先用 m (强项学科),否则用 s (简称) + tp (类别) + 地址构造,再差就给占位
            intro = u.get('m') or ''
            sn = u.get('s') or u.get('n', '')
            tp_full = u.get('tp') or ''
            tp = tp_full.split(' ')[0] if tp_full else ''   # 多类型取第一个,如"医药 军事"->"医药"
            city = u.get('c') or ''
            prov_abbr = u.get('p') or ''
            mp_v = u.get('mp') or 0
            dp_v = u.get('dp') or 0
            by_v = u.get('by') or 0
            if not intro:
                # 没有 m 时:用名称/类型/地区 + 已知数据(硕博点/排名/保研率)合成一段更有信息量的介绍
                parts = []
                if sn:    parts.append(sn)
                if tp:    parts.append(tp + '类')
                if city:  parts.append(city)
                elif prov_abbr: parts.append(prov_abbr)
                bits = []
                if u_rank: bits.append('综合排名参考 #' + str(u_rank))
                if mp_v:   bits.append('硕士点 ' + str(mp_v) + ' 个')
                if dp_v:   bits.append('博士点 ' + str(dp_v) + ' 个')
                if by_v:   bits.append('保研率 ' + str(by_v) + '%')
                tail = ' · '.join(bits) if bits else '优势学科与历年录取数据待官方发布后补充'
                intro = ' | '.join(parts) + ' | ' + tail
            # 类别中文:985/211/双一流/本科
            tier_zh = {'985': '985 · 双一流', '211': '211 · 双一流', 'dfc': '双一流', 'ben': '本科'}
            tier_label = tier_zh.get(u.get('t', ''), u.get('tp') or '本科')
            tags = [tier_label]
            if tp:        tags.append(tp + '类')
            if city:      tags.append(city)
            elif prov_abbr: tags.append(prov_abbr)
            if u_rank:    tags.append('综合排名参考 #' + str(u_rank))
            if mp_v:      tags.append('硕点 ' + str(mp_v))
            if dp_v:      tags.append('博点 ' + str(dp_v))
            if by_v:      tags.append('保研 ' + str(by_v) + '%')
            return self._send(200, json.dumps({
                'name': u.get('n', ''),
                'short': u.get('s', ''),
                'tier': u.get('t', dflt_tier),
                'tierLabel': tier_label,
                'province': u.get('p', ''),
                'city': u.get('c', ''),
                'rank': u_rank,
                'tags': tags,
                'eval': ev,
                'disc': disc,
                'lines': lines,
                'intro': intro,
                'm': u.get('m') or '',
                'll': ll_str,
                'baoyan': u.get('by'),
                'masterPts': u.get('mp'),
                'doctorPts': u.get('dp'),
                'plans': plans,
                'schoolStats': plans_school,
                'history': history,
                'schoolScoreInProv': s_prov_2024,
            }, ensure_ascii=False).encode('utf-8'))

        if p == '/api/same_rank':
            # 同分去向: 给定位次,返回去年该位次附近的学校列表
            rank_q = int(q.get('rank', [0])[0] or 0)
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', [''])[0]
            if not rank_q or not prov or not subj:
                return self._send(200, json.dumps({'error': 'missing params'}, ensure_ascii=False).encode('utf-8'))
            # 收集该校在该省的等效分,算位次,差 < 50% 视为同分去向
            out = []
            for u in UNIS:
                ss = _school_score_in_prov(u, prov, subj)
                if not ss:
                    continue
                sr = _score_to_rank(ss, prov, subj)
                if not sr:
                    continue
                diff_pct = abs(sr - rank_q) / max(rank_q, 1)
                if diff_pct <= 0.20:  # 20% 误差内
                    out.append({
                        'uni': u.get('n', ''),
                        'tier': u.get('t', ''),
                        'p': u.get('p', ''),
                        'c': u.get('c', ''),
                        'll': list(u.get('ll', [])[:2]),
                        'schoolScore': ss,
                        'minRank': sr,
                        'diff': sr - rank_q,
                        'rank': u.get('rank', 0),
                        'tp': u.get('tp', ''),
                        'by': u.get('by', 0),
                    })
            out.sort(key=lambda x: abs(x['diff']))
            return self._send(200, json.dumps({'rank': rank_q, 'prov': prov, 'subj': subj, 'count': len(out), 'items': out[:60]}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/uni/risk':
            # 基于分数+学校+省份的风险评估(冲/稳/保/不可冲)
            score = int(q.get('score', [0])[0] or 0)
            prov = q.get('prov', [''])[0]
            subj = q.get('subj', [''])[0]
            name = q.get('name', [''])[0]
            if not (score and prov and subj and name):
                return self._send(200, json.dumps({'error': 'missing'}, ensure_ascii=False).encode('utf-8'))
            u = next((x for x in UNIS if x.get('n') == name), None)
            if not u:
                return self._send(200, json.dumps({'error': 'no_school'}, ensure_ascii=False).encode('utf-8'))
            ss = _school_score_in_prov(u, prov, subj)
            usr_rank = _score_to_rank(score, prov, subj)
            school_rank = _score_to_rank(ss, prov, subj) if ss else 0
            diff = ss - score
            # 风险等级
            if diff > 50:
                level = 'unreachable'; color = '#a8473b'
                tip = '该校等效分超你 ' + str(diff) + ' 分,位次远在你前,正常情况上不了。可作 "梦想校"。'
            elif diff > 10:
                level = 'chong'; color = '#d85a30'
                tip = '高 ' + str(diff) + ' 分,稳妥冲一冲。需填在前面,后面必须有兜底。'
            elif diff >= -10:
                level = 'wen'; color = '#e0a32e'
                tip = '分数与该校接近,可作 "稳"。专业组可能踩线,关注是否服从调剂。'
            else:
                level = 'bao'; color = '#1d9e75'
                tip = '低于该校 ' + str(-diff) + ' 分,基本能录,作 "保底" 较稳。'
            return self._send(200, json.dumps({
                'name': name, 'score': score, 'prov': prov, 'subj': subj,
                'schoolScore': ss, 'diff': diff,
                'userRank': usr_rank, 'schoolRank': school_rank,
                'level': level, 'color': color, 'tip': tip,
                'tier': u.get('t', ''), 'tierLabel': {'985':'985·双一流','211':'211·双一流','dfc':'双一流','ben':u.get('tp','本科')}.get(u.get('t',''), '本科'),
            }, ensure_ascii=False).encode('utf-8'))
        if p == '/api/llm/health':
            try:
                h = _llm.LLMClient.instance().health()
            except Exception as e:
                h = {'error': str(e)}
            return self._send(200, json.dumps({'providers': h, 'cache_size': len(_LLM_CACHE)}, ensure_ascii=False).encode('utf-8'))
        if p == '/api/llm/cache/clear':
            _LLM_CACHE.clear()
            return self._send(200, json.dumps({'ok': True, 'cleared': True}, ensure_ascii=False).encode('utf-8'))
        rel = p.lstrip('/')
        if not rel:
            rel = 'iframe-anon.html'
        return self._serve_static(rel)

    def do_PUT(self):
        u = urlparse(self.path)
        p = u.path
        p = self._alias(p)
        if p == '/api/profile':
            body = self._read_json()
            uid, has_cookie = get_user_id(self.headers)
            if not has_cookie:
                uid = mint_user_id()
            db_put(uid, body)
            resp = json.dumps({'ok': True, 'id': uid}, ensure_ascii=False).encode('utf-8')
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self._cors()
                if not has_cookie:
                    self.send_header('Set-Cookie', 'agentfeed_anon=' + uid + '; Path=/; Max-Age=31536000; SameSite=None; Secure=False')
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                print('send err:', e)
            return
        return self._send(404)

    def do_POST(self):
        return self.do_PUT()

    def do_DELETE(self):
        u = urlparse(self.path)
        p = u.path
        p = self._alias(p)
        if p == '/api/profile':
            uid, has_cookie = get_user_id(self.headers)
            db_delete(uid)
            return self._send(200, json.dumps({'ok': True, 'deleted': uid}, ensure_ascii=False).encode('utf-8'))
        return self._send(404)

def main():
    db_init()
    load_gaokao_data()
    print('[backend] starting on 0.0.0.0:' + str(PORT))
    print('[backend] ROOT = ' + str(ROOT))
    print('[backend] DB   = ' + str(DB))
    s = ThreadingHTTPServer(('0.0.0.0', PORT), H)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        s.shutdown()

if __name__ == '__main__':
    main()
