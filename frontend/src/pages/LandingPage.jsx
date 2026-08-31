import { useState, useEffect, useRef, useCallback, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'

/* ─── utilities ─── */
const sleep = ms => new Promise(r => setTimeout(r, ms))
const rnd = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a
const pick = a => a[rnd(0, a.length - 1)]
const now = () => {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0')).join(':')
}

/* ─── data ─── */
const PLATFORMS = ['X', 'LinkedIn', 'Instagram', 'Threads', 'Reddit', 'Bluesky']
const ANGLES = ['contrarian take', 'teardown', 'under-the-hood', 'failure story', 'field report', 'hot take']
const SCHED_TIMES = ['tomorrow 09:30', 'Thu 12:00', 'Fri 18:15', 'tonight 21:00']

const EVENTS = [
  () => ['scout', `analyzed ${rnd(120, 900)} trending topics across ${pick(PLATFORMS)}`],
  () => ['draft', `post #${rnd(4000, 9999)} written \u00b7 ${rnd(38, 120)} words \u00b7 voice match ${rnd(91, 99)}%`],
  () => ['review', `\u201c${pick(ANGLES)}\u201d scored ${rnd(7, 9)}.${rnd(0, 9)}/10 \u00b7 approved`],
  () => ['queue', `thread scheduled ${pick(SCHED_TIMES)}`],
  () => ['pub', `shipped to ${pick(PLATFORMS)} \u00b7 live now`],
  () => ['learn', `+${rnd(4, 31)}% replies on post #${rnd(4000, 9999)} \u00b7 strategy updated`],
  () => ['scout', `monitor \u00b7 ${rnd(3, 12)} competitor feeds quiet \u00b7 window open`],
]

const TICKER_ITEMS = [
  'PUB 09:31 \u00b7 @nova_builds \u2014 \u201cWe rebuilt our onboarding in 6 hours. Here\u2019s the teardown.\u201d \u00b7 +18% replies',
  'PUB 09:12 \u00b7 @stack_daily \u2014 \u201cThe one-line deploy that saved our Friday.\u201d \u00b7 +9% saves',
  'PUB 08:58 \u00b7 @lumen_labs \u2014 \u201cNobody talks about the boring part of agents.\u201d \u00b7 +41% clicks',
  'PUB 08:40 \u00b7 @quiet_eng \u2014 \u201cOur incident review found 3 surprises. One was us.\u201d \u00b7 +22% shares',
  'PUB 08:17 \u00b7 @field_notes \u2014 \u201c30 days of shipping daily: the honest numbers.\u201d \u00b7 +31% follows',
  'PUB 07:52 \u00b7 @orbit_dev \u2014 \u201cWe deleted half our roadmap. Retention went up.\u201d \u00b7 +14% bookmarks',
]

const DRAFTS = [
  t => `We spent three weeks stress-testing ${t}.\n\nThe result surprised us:\n\n\u2014 the obvious approach lost 40% of the time\n\u2014 one small change flipped the outcome entirely\n\u2014 the data behind it is messier than anyone admits\n\nFull teardown below. Ask me anything.`,
  t => `Nobody talks about the boring part of ${t}.\n\nDemos get the clicks. Plumbing wins the users.\n\nThree things that actually moved the needle for us \u2014 and the one mistake that cost us a month.`,
  t => `Field report: ${t}, day 30.\n\nWhat we believed at the start: wrong.\nWhat actually happened: better \u2014 but not for the reason we expected.\n\nThe numbers, the mistakes, and the version we\u2019d ship again. Thread:`,
]

const CHIP_LIST = ['X', 'LinkedIn', 'Instagram', 'Threads']
const STAGES = [
  { idx: '01', name: 'Scout', desc: 'Continuously reads trending topics, competitor feeds, and your own top performers to find the window where a post lands hardest.', meta: 'sources \u00b7 40+ feeds\ncadence \u00b7 every 12 min' },
  { idx: '02', name: 'Draft', desc: 'Writes the post in your voice \u2014 trained on your best material, scored against your engagement history before a human ever sees it.', meta: 'voice match \u00b7 > 95%\nangles per topic \u00b7 3' },
  { idx: '03', name: 'Approve', desc: 'Runs its own review pass, flags anything risky, and routes to you only when it\u2019s genuinely unsure. Most drafts never need you.', meta: 'auto-approval \u00b7 87%\nescalation \u00b7 < 5 sec' },
  { idx: '04', name: 'Publish', desc: 'Ships to every connected platform at the minute it predicted would perform best, then feeds the result back into the next cycle.', meta: 'platforms \u00b7 6 live\ntiming \u00b7 per-post optimal' },
]

/* ─── hooks ─── */
function useClock() {
  const [time, setTime] = useState(now())
  useEffect(() => { const id = setInterval(() => setTime(now()), 1000); return () => clearInterval(id) }, [])
  return time
}

/* Global reveal observer — works on ALL .reveal elements in the document */
function useGlobalReveal() {
  useEffect(() => {
    const targets = document.querySelectorAll('.reveal')
    if (!targets.length) return
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target) } }),
      { threshold: 0.12 }
    )
    targets.forEach(t => obs.observe(t))
    return () => obs.disconnect()
  }, [])
}

function useCountUp() {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const counters = el.querySelectorAll('.count')
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (!e.isIntersecting) return
        const target = e.target
        obs.unobserve(target)
        const end = parseFloat(target.dataset.count)
        const dec = +(target.dataset.dec || 0)
        const dur = 1400
        const t0 = performance.now()
        function step(t) {
          const p = Math.min((t - t0) / dur, 1)
          const ease = 1 - Math.pow(1 - p, 3)
          target.textContent = dec ? (end * ease).toFixed(dec) : Math.round(end * ease).toLocaleString('en-US')
          if (p < 1) requestAnimationFrame(step)
        }
        requestAnimationFrame(step)
      }),
      { threshold: 0.6 }
    )
    counters.forEach(c => obs.observe(c))
    return () => obs.disconnect()
  }, [])
  return ref
}

/* ─── Toast ─── */
function ToastItem({ msg, err }) {
  const ref = useRef(null)
  useEffect(() => { requestAnimationFrame(() => { if (ref.current) ref.current.classList.add('show') }) }, [])
  return <div ref={ref} className={`toast${err ? ' err' : ''}`}>{msg}</div>
}

/* ─── Ticker ─── */
function Ticker() {
  const half = TICKER_ITEMS.map((t, i) => (
    <Fragment key={i}><span className="ti">{t}</span><span className="sep">/</span></Fragment>
  ))
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track">{half}{half}</div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function LandingPage({ toast }) {
  const navigate = useNavigate()
  const clock = useClock()
  useGlobalReveal()
  const countRef1 = useCountUp()
  const countRef2 = useCountUp()

  /* ── agent console feed ── */
  const [feed, setFeed] = useState(() => {
    const initial = []
    for (let i = 0; i < 7; i++) { const e = pick(EVENTS)(); initial.push({ tag: e[0], text: e[1], time: now() }) }
    return initial
  })
  useEffect(() => {
    const id = setInterval(() => {
      const e = pick(EVENTS)()
      setFeed(p => [...p.slice(-12), { tag: e[0], text: e[1], time: now() }])
    }, 2400)
    return () => clearInterval(id)
  }, [])

  /* ── email forms ── */
  const handleEmail = useCallback((e) => {
    e.preventDefault()
    const v = e.target.querySelector('input').value.trim()
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { toast("That email doesn\u2019t look right \u2014 try again.", false); return }
    toast(`You\u2019re in, ${v} \u2014 agent #${rnd(1100, 1900)} assigned. Watch your inbox.`)
    e.target.querySelector('input').value = ''
  }, [toast])

  /* ── demo: chips ── */
  const [chips, setChips] = useState({ X: true, LinkedIn: true, Instagram: false, Threads: false })
  const targetLabel = Object.entries(chips).filter(([, v]) => v).map(([k]) => k).join(' + ') || 'none'
  const toggleChip = useCallback((name) => {
    setChips(p => {
      const next = { ...p, [name]: !p[name] }
      if (!Object.values(next).some(Boolean)) { toast('Keep at least one feed on \u2014 the agent needs somewhere to ship.', false); return p }
      return next
    })
  }, [toast])

  /* ── demo: composer ── */
  const [topic, setTopic] = useState('')
  const [draftId, setDraftId] = useState('DRAFT \u2014 POST #\u2014\u2014')
  const [draftState, setDraftState] = useState('IDLE')
  const [statusLog, setStatusLog] = useState([])
  const [draftText, setDraftText] = useState('')
  const [drafting, setDrafting] = useState(false)
  const [showCaret, setShowCaret] = useState(false)
  const [footVisible, setFootVisible] = useState(false)
  const [footChars, setFootChars] = useState('')
  const [footQueue, setFootQueue] = useState('')
  const busyRef = useRef(false)

  const runAgent = useCallback(async () => {
    if (busyRef.current) return
    const t = topic.trim()
    if (!t) { toast('Give the agent a topic first \u2014 it can\u2019t read minds. Yet.', false); return }
    const targets = Object.entries(chips).filter(([, v]) => v).map(([k]) => k)
    busyRef.current = true
    setDrafting(true)
    setDraftState('WORKING')
    setStatusLog([{ text: `scouting ${rnd(140, 980)} conversations about \u201c${t}\u201d\u2026` }])
    setFootVisible(false)
    setDraftText('')
    setShowCaret(true)
    setDraftId(`DRAFT \u2014 POST #${rnd(4000, 9999)}`)
    await sleep(900)
    setStatusLog(p => [...p.slice(-2), { text: `3 angles found \u00b7 best fit: \u201c${pick(ANGLES)}\u201d \u00b7 writing for ${targets.join(' + ')}` }])
    await sleep(700)
    const draft = pick(DRAFTS)(t)
    for (const ch of draft) {
      setDraftText(p => p + ch)
      await sleep(ch === '\n' ? 55 : rnd(8, 26))
    }
    setShowCaret(false)
    const n = draft.length
    const sched = pick(SCHED_TIMES)
    setFootChars(`${n} chars \u00b7 ${n > 280 ? 'will thread for X' : 'fits X in one'}`)
    setFootQueue(`target <b>${targets.join(' + ')}</b> \u00b7 queued <b>${sched}</b>`)
    setFootVisible(true)
    setDraftState('QUEUED')
    toast(`Draft queued for ${sched} \u2014 the agent takes it from here.`)
    setDrafting(false)
    busyRef.current = false
  }, [topic, chips, toast])

  /* ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <>
      {/* ═══ HEADER ═══ */}
      <header>
        <div className="wrap nav">
          <a className="wordmark" href="#">AutoPost<b>.</b></a>
          <span className="status"><span className="dot" />AGENT ONLINE</span>
          <nav className="nav-links">
            <a href="#how">How it works</a>
            <a href="#demo">Live demo</a>
            <a href="#numbers">Numbers</a>
          </nav>
          <a className="btn" href="#cta">Get access</a>
        </div>
      </header>

      {/* ═══ HERO ═══ */}
      <div className="hero">
        <div className="wrap">
          <div className="hero-grid">
            <div>
              <p className="kicker">Autonomous publishing agent \u00b7 v2.1</p>
              <h1>Post like a machine.<br /><em>Sound like a human.</em></h1>
              <p className="hero-sub">
                AutoPost is an agent that scouts trends, drafts in your voice, and publishes across
                every platform \u2014 on a schedule it manages itself. You set the voice once.
                <strong>It ships every day after that.</strong>
              </p>
              <div className="hero-actions">
                <button className="btn" onClick={() => navigate('/dashboard')}>Get started</button>
                <a className="btn" href="#how" style={{ background: 'transparent', color: 'var(--ink)' }}>Learn more</a>
              </div>
            </div>

            <div className="console" aria-label="Live agent activity">
              <div className="console-head">
                <span className="dot" />AGENT CONSOLE \u2014 LIVE<span className="clock">{clock}</span>
              </div>
              <div className="feed">
                {feed.map((l, i) => (
                  <div key={i} className={`fl${l.tag === 'pub' ? ' hot' : ''}`}>
                    <span className="ft">[{l.time}]</span>
                    <span className="fg">{l.tag}</span>
                    <span>{l.text}</span>
                  </div>
                ))}
              </div>
              <div style={{ padding: '0 1rem .9rem' }}><span className="caret-block" /></div>
            </div>
          </div>

          <div className="stats" ref={countRef1}>
            <div className="stat"><div className="n"><span className="count" data-count="12438">0</span></div><div className="l">Posts this week</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="99.98" data-dec="2">0</span>%</div><div className="l">On-time publish rate</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="6">0</span></div><div className="l">Platforms live</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="0">0</span></div><div className="l">Humans required</div></div>
          </div>
        </div>
      </div>

      <Ticker />

      {/* ═══ HOW IT WORKS ═══ */}
      <section id="how">
        <div className="wrap">
          <div className="sec-head reveal"><span className="sec-num">01 / METHOD</span><h2>Four stages. <em>Zero hands.</em></h2></div>
          <svg className="pipe reveal" viewBox="0 0 1000 24" preserveAspectRatio="none" aria-hidden="true">
            <line x1="10" y1="12" x2="990" y2="12" stroke="#16150F" strokeOpacity=".22" strokeWidth="1" />
            <circle cx="10" cy="12" r="4" fill="#16150F" />
            <circle cx="336" cy="12" r="4" fill="#16150F" />
            <circle cx="664" cy="12" r="4" fill="#16150F" />
            <circle cx="990" cy="12" r="4" fill="#16150F" />
            <circle r="4.5" fill="#E8490F"><animateMotion dur="7s" repeatCount="indefinite" path="M10,12 L990,12" /></circle>
          </svg>
          {STAGES.map(s => (
            <div className="stage reveal" key={s.idx}>
              <div className="idx">{s.idx}</div>
              <div className="name">{s.name}</div>
              <div className="desc">{s.desc}</div>
              <div className="meta">{s.meta.split('\n').map((l, i) => <Fragment key={i}>{l}<br /></Fragment>)}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ DEMO ═══ */}
      <section id="demo" style={{ borderTop: '1px solid var(--hair)' }}>
        <div className="wrap">
          <div className="sec-head reveal"><span className="sec-num">02 / DEMO</span><h2>Watch it <em>draft.</em></h2></div>
          <div className="demo-grid">
            <div className="demo-copy reveal">
              <p>Give the agent a topic and pick your targets. It scouts, picks an angle, writes the draft, and queues it \u2014 one pass, right here on this page.</p>
              <div className="field">
                <label htmlFor="topicInput">Topic</label>
                <input type="text" id="topicInput" placeholder="e.g. AI agents, shipping fast, hiring" maxLength={60} value={topic} onChange={e => setTopic(e.target.value)} />
              </div>
              <div className="field">
                <label>Target feeds</label>
                <div className="chips">
                  {CHIP_LIST.map(c => (
                    <button key={c} className={`chip${chips[c] ? ' on' : ''}`} type="button" onClick={() => toggleChip(c)}>{c}</button>
                  ))}
                </div>
                <p className="target-label">target &rarr; <b>{targetLabel}</b></p>
              </div>
              <button className="btn run-btn" type="button" disabled={drafting} onClick={runAgent}>
                {drafting ? 'Running\u2026' : 'Run the agent'}
              </button>
            </div>
            <div className="draft-panel reveal">
              <div className="draft-head">
                <span>{draftId}</span>
                <span className={`st${draftState === 'WORKING' ? ' live' : ''}`}>{draftState}</span>
              </div>
              <div className="status-log">
                {statusLog.map((l, i) => <div key={i}><span className="arr">&rarr;</span>{l.text}</div>)}
              </div>
              <div className="draft-body">
                {draftText ? (
                  <span>{draftText}{showCaret && <span className="caret" />}</span>
                ) : (
                  <span className="placeholder">Give the agent a topic \u2014 it scouts, drafts, and queues in one pass.</span>
                )}
              </div>
              <div className={`draft-foot${footVisible ? '' : ' hidden'}`}>
                <span>{footChars}</span>
                <span dangerouslySetInnerHTML={{ __html: footQueue }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══ NUMBERS ═══ */}
      <section id="numbers" style={{ borderTop: '1px solid var(--hair)', paddingTop: 'clamp(48px,7vw,80px)', paddingBottom: 'clamp(48px,7vw,80px)' }}>
        <div className="wrap">
          <div className="sec-head reveal" style={{ marginBottom: '1.6rem' }}><span className="sec-num">03 / PROOF</span><h2>The agent keeps <em>score.</em></h2></div>
          <div className="stats reveal" style={{ marginTop: 0, borderTop: 'none' }} ref={countRef2}>
            <div className="stat"><div className="n"><span className="count" data-count="12438">0</span></div><div className="l">Posts shipped this week</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="41">0</span>%</div><div className="l">Avg. reply-rate lift</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="28" data-dec="0">0</span>s</div><div className="l">Median scout-to-queue</div></div>
            <div className="stat"><div className="n"><span className="count" data-count="87">0</span>%</div><div className="l">Drafts auto-approved</div></div>
          </div>
        </div>
      </section>

      {/* ═══ CTA ═══ */}
      <section className="cta" id="cta">
        <div className="wrap">
          <p className="kicker reveal" style={{ color: 'var(--acc-bright)' }}>Private beta \u00b7 190 seats left</p>
          <h2 className="reveal">Put your feed on <em>autopilot.</em></h2>
          <p className="reveal">Your agent goes live within 48 hours of invitation. It learns your voice from your twenty best posts \u2014 then it never misses a day.</p>
          <div className="cta-actions reveal">
            <button className="btn" onClick={() => navigate('/dashboard')} style={{ background: 'var(--acc)', borderColor: 'var(--acc)', padding: '.9rem 2rem', fontSize: '.78rem' }}>Get started</button>
          </div>
          <p className="form-note reveal" style={{ marginTop: '1.2rem' }}>One click to your agent dashboard. No card required.</p>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer>
        <div className="wrap foot">
          <span>AUTOPOST \u2014 AN AUTONOMOUS PUBLISHING AGENT</span>
          <span><a href="#how">METHOD</a> \u00b7 <a href="#demo">DEMO</a> \u00b7 <a href="#cta">ACCESS</a></span>
          <span>\u00a9 2025 \u00b7 BUILT FOR THE AGENTIC HACKATHON</span>
        </div>
      </footer>
    </>
  )
}