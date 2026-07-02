"""LLM client with primary/backup failover for gaokao backend.

Providers (read from D:/kaifa/gaokao/crawled/.env):
  MINIMAX_API_KEY + MINIMAX_BASE  (default https://api.minimaxi.com/v1)
  DEEPSEEK_API_KEY + DEEPSEEK_BASE  (default https://api.deepseek.com/v1)

Public API:
  LLMClient.complete(messages, *, max_tokens=800, temperature=0.4, json_mode=False, timeout=15.0) -> dict
  LLMClient.json(messages, *, max_tokens=800, temperature=0.2, timeout=15.0) -> dict  # forces json, returns parsed
  LLMClient.health() -> {provider: {ok:int, fail:int, down_until:ts|0, last_err:str}}
"""
import json, os, time, threading, urllib.request, urllib.error


class _FakeBody:
    def __init__(self, raw): self._raw = raw.encode('utf-8') if isinstance(raw, str) else raw
    def read(self, n=-1): return self._raw if n < 0 else self._raw[:n]
    def close(self): pass
from pathlib import Path

ENV_FILE = Path(r'D:/kaifa/gaokao/crawled/.env')

def _load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env

_ENV = _load_env()

PROVIDERS = [
    {
        'name': 'deepseek',
        'base': _ENV.get('DEEPSEEK_BASE', 'https://api.deepseek.com/v1'),
        'key':  _ENV.get('DEEPSEEK_API_KEY', ''),
        'model': _ENV.get('DEEPSEEK_MODEL', 'deepseek-chat'),
        'json_mode': 'native',  # 'prompt' | 'native'
    },
    {
        'name': 'minimax',
        'base': _ENV.get('MINIMAX_BASE', 'https://api.minimaxi.com/v1'),
        'key':  _ENV.get('MINIMAX_API_KEY', ''),
        'model': _ENV.get('MINIMAX_MODEL', 'MiniMax-Text-01'),
        'json_mode': 'prompt',
    },
]

class _ProviderState:
    __slots__ = ('ok', 'fail', 'down_until', 'last_err', 'last_use')
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.down_until = 0.0
        self.last_err = ''
        self.last_use = 0.0

class LLMClient:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.states = {p['name']: _ProviderState() for p in PROVIDERS}
        self._last_provider = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _available(self, name):
        s = self.states[name]
        return time.time() >= s.down_until

    def _pick(self):
        # Prefer the one not in cooldown, and the least-recently-used (so we exercise both).
        now = time.time()
        avail = [p for p in PROVIDERS if self._available(p['name'])]
        if not avail:
            # everyone down -> pick the one whose cooldown ends soonest
            return min(PROVIDERS, key=lambda p: self.states[p['name']].down_until)
        # Prefer primary (minimax) unless its last use was < 30s ago and deepseek is fresh
        primary = PROVIDERS[0]
        if self._available(primary['name']):
            return primary
        return avail[0]

    def _post(self, provider, body, timeout):
        # Run stdlib urlopen in a thread with an upper bound, since http.client
        # `timeout` only applies to connect, not the body read.
        import concurrent.futures as _cf
        url = provider['base'].rstrip('/') + '/chat/completions'
        data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + provider['key'], 'Connection': 'close'})
        def _call():
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode('utf-8', errors='replace')
                status = r.status
            return status, raw
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            try:
                status, raw = fut.result(timeout=timeout + 1)
            except _cf.TimeoutError:
                raise TimeoutError('http call exceeded ' + str(timeout) + 's')
        if status >= 400:
            raise urllib.error.HTTPError(url, status, 'HTTP ' + str(status), {}, _FakeBody(raw))
        return json.loads(raw)
    def _mark_ok(self, name):
        s = self.states[name]
        s.ok += 1
        s.down_until = 0.0
        s.last_err = ''
        s.last_use = time.time()

    def _mark_fail(self, name, err, hard=False):
        s = self.states[name]
        s.fail += 1
        s.last_err = str(err)[:200]
        s.last_use = time.time()
        if hard:
            cooldown = 300.0
        else:
            # soft: exponential backoff capped at 60s; reset to 0 on first success
            recent = s.fail
            cooldown = min(5.0 * (2 ** min(recent, 5)), 60.0)
        s.down_until = time.time() + cooldown

    def complete(self, messages, *, max_tokens=800, temperature=0.4, json_mode=False, timeout=25.0, retries=1):
        """Try primary, then backup. Returns parsed dict from the response, or {'_raw': content, '_provider': name, '_err': str} on failure."""
        # If caller provided a single string, wrap
        if isinstance(messages, str):
            messages = [{'role': 'user', 'content': messages}]
        tried = set()
        last_err = None
        for attempt in range(retries + 1):
            p = self._pick()
            if p['name'] in tried and len(PROVIDERS) > 1:
                # we already failed this provider this call; switch
                for q in PROVIDERS:
                    if q['name'] not in tried and self._available(q['name']):
                        p = q
                        break
            tried.add(p['name'])
            body = {'model': p['model'], 'messages': messages, 'max_tokens': int(max_tokens), 'temperature': float(temperature), 'stream': False}
            if json_mode:
                if p.get('json_mode', 'native') == 'native':
                    body['response_format'] = {'type': 'json_object'}
                    msgs = list(body['messages'])
                    # Some providers (e.g. deepseek) require the literal word 'json' in the prompt
                    for i, m in enumerate(msgs):
                        if m.get('role') == 'system':
                            if 'json' not in (m.get('content') or '').lower():
                                msgs[i] = dict(m); msgs[i]['content'] = '[json output only] ' + (m.get('content') or '')
                            break
                    else:
                        msgs.insert(0, {'role':'system','content':'[json output only] Output a single valid JSON object.'})
                    body['messages'] = msgs
                else:
                    # prompt-based: append strict-JSON hint to system
                    msgs = list(body['messages'])
                    for i, m in enumerate(msgs):
                        if m.get('role') == 'system':
                            msgs[i] = dict(m); msgs[i]['content'] = (m.get('content') or '') + '\n\n必须严格输出一个有效 JSON 对象，不要包含 markdown 或说明。'
                            break
                    else:
                        msgs.insert(0, {'role':'system','content':'必须严格输出一个有效 JSON 对象，不要包含 markdown 或说明。'})
                    body['messages'] = msgs
            try:
                t0 = time.time()
                r = self._post(p, body, timeout)
                dt = int((time.time() - t0) * 1000)
                self._mark_ok(p['name'])
                content = (r.get('choices') or [{}])[0].get('message', {}).get('content', '')
                usage = r.get('usage') or {}
                # Always include provider for observability
                r['_provider'] = p['name']
                r['_latency_ms'] = dt
                if json_mode and content:
                    try:
                        r['_parsed'] = json.loads(content)
                    except Exception as e:
                        # Some providers occasionally wrap JSON; try to extract
                        s = content.strip()
                        if s.startswith('```'):
                            s = s.strip('`')
                            if s.startswith('json'):
                                s = s[4:]
                            s = s.strip()
                        try:
                            r['_parsed'] = json.loads(s)
                        except Exception:
                            self._mark_fail(p['name'], 'json parse: ' + str(e), hard=False)
                            last_err = ('json', p['name'], str(e))
                            if attempt < retries:
                                continue
                            return {'_err': 'json parse failed', '_provider': p['name'], '_raw': content}
                return r
            except urllib.error.HTTPError as e:
                code = e.code
                body_txt = e.read()[:300].decode('utf-8', errors='replace')
                # 4xx auth/perm/rate = hard (5min); other 4xx = soft (30s); 5xx = hard
                hard = code in (401, 403, 429) or (code >= 500)
                self._mark_fail(p['name'], f'HTTP {code}: {body_txt[:120]}', hard=hard)
                last_err = ('http', p['name'], code, body_txt[:120])
                if attempt < retries and len(tried) < len(PROVIDERS):
                    continue
                # fall through
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self._mark_fail(p['name'], 'net: ' + str(e)[:120], hard=False)
                last_err = ('net', p['name'], str(e)[:120])
                if attempt < retries and len(tried) < len(PROVIDERS):
                    continue
            except Exception as e:
                self._mark_fail(p['name'], 'exc: ' + repr(e)[:120], hard=False)
                last_err = ('exc', p['name'], repr(e)[:120])
                if attempt < retries and len(tried) < len(PROVIDERS):
                    continue
        return {'_err': 'all providers failed', '_detail': last_err}

    def json(self, messages, *, max_tokens=800, temperature=0.2, timeout=15.0):
        r = self.complete(messages, max_tokens=max_tokens, temperature=temperature, json_mode=True, timeout=timeout)
        if '_parsed' in r:
            r['_json'] = r.pop('_parsed')
        return r

    def health(self):
        return {n: {'ok': s.ok, 'fail': s.fail, 'down_until': s.down_until, 'last_err': s.last_err} for n, s in self.states.items()}