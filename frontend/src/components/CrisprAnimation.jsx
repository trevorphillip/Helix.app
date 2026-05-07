import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// ─── constants ────────────────────────────────────────────────────────────────

const T = {
  bg:      '#0f1117',
  surface: '#151821',
  border:  '#1e2130',
  border2: '#2a2e3e',
  teal:    '#1D9E75',
  amber:   '#EF9F27',
  text:    '#e8e6df',
  muted:   '#5F5E5A',
  mid:     '#888780',
  red:     '#F09595',
  purple:  '#9B8FEF',
}

const HELIX_RADIUS  = 1.8
const RISE_PER_BP   = 0.34
const TURN_PER_BP   = (2 * Math.PI) / 10
const DNA_BP        = 30

const PHASES = ['idle', 'scanning', 'binding', 'unwinding', 'hybridizing', 'cleaving', 'repair', 'complete']

const PHASE_DURATION = {
  idle:        0,
  scanning:    3,
  binding:     2,
  unwinding:   2,
  hybridizing: 2,
  cleaving:    1,
  repair:      3,
  complete:    0,
}

const PHASE_STATUS = {
  idle:        'Ready — press Play to begin',
  scanning:    'Cas9 scanning DNA for PAM sequence...',
  binding:     'PAM recognized — Cas9 binds to DNA...',
  unwinding:   'DNA strands separate — R-loop forms...',
  hybridizing: 'gRNA hybridizes to target strand...',
  cleaving:    'Double strand break — DNA cut!',
  repair:      'NHEJ repair — small indel introduced...',
  complete:    'Edit complete! NHEJ introduced a 1bp indel',
}

function helixPt(i, angleOffset = 0, radius = HELIX_RADIUS) {
  const a = i * TURN_PER_BP + angleOffset
  return new THREE.Vector3(radius * Math.cos(a), i * RISE_PER_BP, radius * Math.sin(a))
}

function makeTube(pts, radius, color, opacity = 1, emissive = false) {
  if (pts.length < 2) return null
  const curve = new THREE.CatmullRomCurve3(pts)
  const geo   = new THREE.TubeGeometry(curve, pts.length * 3, radius, 8, false)
  const mat   = new THREE.MeshPhongMaterial({
    color,
    transparent: opacity < 1,
    opacity,
    ...(emissive ? { emissive: new THREE.Color(color), emissiveIntensity: 0.4 } : {}),
  })
  return new THREE.Mesh(geo, mat)
}

function makeSphere(pos, radius, color, emissive = false) {
  const geo = new THREE.SphereGeometry(radius, 10, 10)
  const mat = new THREE.MeshPhongMaterial({
    color,
    ...(emissive ? { emissive: new THREE.Color(color), emissiveIntensity: 0.5 } : {}),
  })
  const m = new THREE.Mesh(geo, mat)
  m.position.copy(pos)
  return m
}

function makeBox(size, color, pos) {
  const geo = new THREE.BoxGeometry(...size)
  const mat = new THREE.MeshPhongMaterial({ color })
  const m   = new THREE.Mesh(geo, mat)
  m.position.copy(pos)
  return m
}

function disposeGroup(group) {
  group.traverse(obj => {
    if (obj.geometry) obj.geometry.dispose()
    if (obj.material) {
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
      else obj.material.dispose()
    }
  })
}

// ─── scene builder ────────────────────────────────────────────────────────────

function buildScene(scene) {
  const refs = {}

  // ── DNA double helix ──────────────────────────────────────────────────────
  const dnaGroup = new THREE.Group()
  dnaGroup.position.y = -(DNA_BP * RISE_PER_BP) / 2

  // backbones
  const bbMat = new THREE.MeshPhongMaterial({ color: 0x2a2e3e })
  for (const off of [0, Math.PI]) {
    const pts   = Array.from({ length: DNA_BP + 1 }, (_, i) => helixPt(i, off))
    const curve = new THREE.CatmullRomCurve3(pts)
    const geo   = new THREE.TubeGeometry(curve, DNA_BP * 6, 0.1, 8, false)
    dnaGroup.add(new THREE.Mesh(geo, bbMat.clone()))
  }

  // base pairs (cylinders + spheres)
  const basePairs = []
  const yAxis = new THREE.Vector3(0, 1, 0)
  for (let i = 0; i < DNA_BP; i++) {
    const p1 = helixPt(i, 0)
    const p2 = helixPt(i, Math.PI)
    // gRNA region (10-30) glows white
    const isTarget = i >= 10 && i < DNA_BP
    const col = isTarget ? 0xdddddd : 0x3a4060

    const s1 = makeSphere(p1, 0.15, col, isTarget)
    const s2 = makeSphere(p2, 0.15, col, isTarget)

    const mid = p1.clone().add(p2).multiplyScalar(0.5)
    const dir = p2.clone().sub(p1)
    const cyl = new THREE.Mesh(
      new THREE.CylinderGeometry(0.04, 0.04, dir.length(), 6),
      new THREE.MeshPhongMaterial({ color: 0x222840, transparent: true, opacity: 1 }),
    )
    cyl.position.copy(mid)
    cyl.quaternion.setFromUnitVectors(yAxis, dir.clone().normalize())

    basePairs.push({ s1, s2, cyl, p1: p1.clone(), p2: p2.clone(), i })
    dnaGroup.add(s1, s2, cyl)
  }
  scene.add(dnaGroup)
  refs.dnaGroup  = dnaGroup
  refs.basePairs = basePairs

  // displaced strand (R-loop) — hidden initially
  const rLoopGroup = new THREE.Group()
  rLoopGroup.visible = false
  const rPts = Array.from({ length: 20 }, (_, k) => {
    const i   = 10 + k
    const p   = helixPt(i, 0)
    p.x += 1.5 * Math.sin(k / 19 * Math.PI)
    p.z += 1.2 * Math.sin(k / 19 * Math.PI)
    return p.add(dnaGroup.position)
  })
  const rTube = makeTube(rPts, 0.08, 0x9B8FEF, 0.7)
  if (rTube) rLoopGroup.add(rTube)
  scene.add(rLoopGroup)
  refs.rLoopGroup = rLoopGroup

  // ── Cas9 protein ──────────────────────────────────────────────────────────
  const cas9 = new THREE.Group()
  cas9.position.set(20, 0, 0)

  const lobe1 = makeBox([3, 2, 2], 0x2a3a6a, new THREE.Vector3(-1.4, 0, 0))
  const lobe2 = makeBox([2.5, 2, 1.8], 0x1a2a5a, new THREE.Vector3(1.3, 0, 0))

  const hingeGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.8, 12)
  const hingeMat = new THREE.MeshPhongMaterial({ color: 0x334477 })
  const hinge    = new THREE.Mesh(hingeGeo, hingeMat)
  hinge.rotation.z = Math.PI / 2
  hinge.position.set(0, 0, 0)

  // nuclease domain spheres
  const ruvc = makeSphere(new THREE.Vector3(1.8, 0.8, 0.8), 0.35, 0xEF9F27, true)
  const hnh  = makeSphere(new THREE.Vector3(1.8, -0.8, 0.8), 0.35, 0xF09595, true)

  cas9.add(lobe1, lobe2, hinge, ruvc, hnh)
  scene.add(cas9)
  refs.cas9  = cas9
  refs.lobe1 = lobe1
  refs.lobe2 = lobe2
  refs.ruvc  = ruvc
  refs.hnh   = hnh

  // ── gRNA tube ─────────────────────────────────────────────────────────────
  const gRnaGroup = new THREE.Group()
  gRnaGroup.position.copy(cas9.position)

  const gPts = Array.from({ length: 20 }, (_, k) => new THREE.Vector3(-k * 0.3, Math.sin(k * 0.3) * 0.4, 0))
  const gTube = makeTube(gPts, 0.06, 0x1D9E75, 0.9, true)
  if (gTube) gRnaGroup.add(gTube)

  const gNucleotides = gPts.map(p => {
    const s = makeSphere(p.clone(), 0.1, 0x1D9E75, true)
    gRnaGroup.add(s)
    return s
  })
  scene.add(gRnaGroup)
  refs.gRnaGroup    = gRnaGroup
  refs.gNucleotides = gNucleotides

  // ── cut effect planes ─────────────────────────────────────────────────────
  const cutGroup = new THREE.Group()
  cutGroup.visible = false
  const cutMat = new THREE.MeshPhongMaterial({
    color: 0xff4444, emissive: new THREE.Color(0xff4444),
    emissiveIntensity: 0.8, transparent: true, opacity: 0.7,
    side: THREE.DoubleSide,
  })
  const cutPos = helixPt(20, 0).add(dnaGroup.position)
  for (let k = 0; k < 2; k++) {
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.06), cutMat.clone())
    plane.position.copy(cutPos)
    plane.position.y += k === 0 ? 0.1 : -0.1
    cutGroup.add(plane)
  }
  scene.add(cutGroup)
  refs.cutGroup = cutGroup

  // cut particles
  const particles = []
  for (let k = 0; k < 20; k++) {
    const s = makeSphere(cutPos.clone(), 0.08, 0xff4444, true)
    s.userData.vel = new THREE.Vector3(
      (Math.random() - 0.5) * 4,
      (Math.random() - 0.5) * 4,
      (Math.random() - 0.5) * 4,
    )
    s.userData.origin = cutPos.clone()
    s.visible = false
    scene.add(s)
    particles.push(s)
  }
  refs.particles = particles

  // ── NHEJ repair proteins ──────────────────────────────────────────────────
  const nhejGroup = new THREE.Group()
  nhejGroup.visible = false
  const ku1 = makeBox([0.8, 0.5, 0.5], 0xEF9F27, new THREE.Vector3(-1.2, 0, 0))
  const ku2 = makeBox([0.8, 0.5, 0.5], 0xEF9F27, new THREE.Vector3(1.2, 0, 0))
  nhejGroup.add(ku1, ku2)
  nhejGroup.position.copy(cutPos)
  nhejGroup.position.x += 6
  scene.add(nhejGroup)
  refs.nhejGroup = nhejGroup

  // indel base
  const indelBase = makeSphere(cutPos.clone(), 0.15, 0xEF9F27, true)
  indelBase.visible = false
  scene.add(indelBase)
  refs.indelBase = indelBase

  return refs
}

// ─── component ────────────────────────────────────────────────────────────────

export default function CrisprAnimation({ guide = 'GGCCGCCTCCGCGGCCGCCT', cutPosition = 42 }) {
  const mountRef   = useRef(null)
  const sceneRef   = useRef(null)
  const refsRef    = useRef(null)
  const clockRef   = useRef(new THREE.Clock(false))
  const stateRef   = useRef({
    phase:     'idle',
    phaseIdx:  0,
    elapsed:   0,
    playing:   false,
    speed:     1,
    shaking:   false,
    shakeDur:  0,
    particles: false,
  })

  const [phase, setPhase]   = useState('idle')
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed]   = useState(1)
  const [phaseIdx, setPhaseIdx] = useState(0)

  // ── scene init ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mountRef.current) return
    const el    = mountRef.current
    const w     = el.clientWidth
    const h     = el.clientHeight

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(w, h)
    renderer.shadowMap.enabled = true
    renderer.setClearColor(0x0f1117, 1)
    el.appendChild(renderer.domElement)

    const scene  = new THREE.Scene()
    scene.background = new THREE.Color(0x0f1117)

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000)
    camera.position.set(0, 5, 25)

    const ambient = new THREE.AmbientLight(0xffffff, 0.3)
    const dir     = new THREE.DirectionalLight(0xffffff, 0.8)
    dir.position.set(10, 20, 10)
    dir.castShadow = true
    const pt1 = new THREE.PointLight(0x1D9E75, 1.0)
    pt1.position.set(-10, 5, 0)
    const pt2 = new THREE.PointLight(0xEF9F27, 0.6)
    pt2.position.set(10, -5, 5)
    scene.add(ambient, dir, pt1, pt2)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.target.set(0, 2.5, 0)

    const refs = buildScene(scene)
    sceneRef.current = { renderer, scene, camera, controls }
    refsRef.current  = refs

    const camOrigin = camera.position.clone()

    // animation loop
    let animId
    function animate() {
      animId = requestAnimationFrame(animate)
      const st  = stateRef.current
      const raw = clockRef.current.getDelta()
      const dt  = st.playing ? raw * st.speed : 0

      if (st.playing) {
        st.elapsed += dt
        tickPhase(st, refsRef.current, dt)
      }

      // camera shake during cleaving
      if (st.shaking) {
        st.shakeDur -= raw
        if (st.shakeDur <= 0) {
          st.shaking = false
          camera.position.copy(camOrigin)
        } else {
          camera.position.x = camOrigin.x + (Math.random() - 0.5) * 0.15
          camera.position.y = camOrigin.y + (Math.random() - 0.5) * 0.15
        }
      }

      // pulse cut planes
      if (refsRef.current?.cutGroup?.visible) {
        const t = performance.now() / 400
        refsRef.current.cutGroup.children.forEach((p, k) => {
          if (p.material) p.material.opacity = 0.4 + 0.4 * Math.sin(t + k)
        })
      }

      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const ro = new ResizeObserver(() => {
      const ww = el.clientWidth
      const hh = el.clientHeight
      camera.aspect = ww / hh
      camera.updateProjectionMatrix()
      renderer.setSize(ww, hh)
    })
    ro.observe(el)

    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
      controls.dispose()
      if (refsRef.current) disposeGroup({ traverse: cb => Object.values(refsRef.current).forEach(v => v?.traverse?.(cb)) })
      renderer.dispose()
      el.removeChild(renderer.domElement)
      sceneRef.current  = null
      refsRef.current   = null
    }
  }, [])

  // ── phase tick ─────────────────────────────────────────────────────────────
  function tickPhase(st, refs, dt) {
    if (!refs) return
    const dur = PHASE_DURATION[st.phase] || 1
    const p   = dur > 0 ? Math.min(st.elapsed / dur, 1) : 1

    switch (st.phase) {
      case 'scanning':   tickScanning(refs, p, dt);    break
      case 'binding':    tickBinding(refs, p);          break
      case 'unwinding':  tickUnwinding(refs, p);        break
      case 'hybridizing':tickHybridizing(refs, p);      break
      case 'cleaving':   tickCleaving(refs, p, st, dt); break
      case 'repair':     tickRepair(refs, p);           break
      default: break
    }

    if (p >= 1 && st.phase !== 'idle' && st.phase !== 'complete') {
      advancePhase(st)
    }
  }

  function advancePhase(st) {
    const next = st.phaseIdx + 1
    if (next >= PHASES.length - 1) {
      st.phase    = 'complete'
      st.phaseIdx = PHASES.length - 1
      st.playing  = false
      setPlaying(false)
    } else {
      st.phaseIdx = next
      st.phase    = PHASES[next]
    }
    st.elapsed = 0
    setPhase(st.phase)
    setPhaseIdx(st.phaseIdx)
  }

  // ── per-phase animation functions ──────────────────────────────────────────

  function tickScanning(refs, p, dt) {
    // Cas9 moves from x=20 → x=4
    const x = 20 - p * 16
    refs.cas9.position.x = x
    refs.gRnaGroup.position.x = x
    // wobble
    refs.cas9.position.y = Math.sin(p * Math.PI * 6) * 0.3
    refs.gRnaGroup.position.y = refs.cas9.position.y
  }

  function tickBinding(refs, p) {
    // Cas9 arrives at x=4, lobes open slightly
    refs.cas9.position.x = THREE.MathUtils.lerp(4, 3, p)
    refs.cas9.position.y = THREE.MathUtils.lerp(refs.cas9.position.y, 0, p * 0.2)
    refs.gRnaGroup.position.copy(refs.cas9.position)
    // lobes rotate apart
    refs.lobe1.rotation.y = -p * 0.26
    refs.lobe2.rotation.y = p * 0.26
    // DNA unwinds near target — spread base spheres slightly
    refs.basePairs.forEach(({ s1, s2, i }) => {
      if (i >= 10 && i < DNA_BP) {
        const spread = p * 0.3
        const p1 = helixPt(i, -spread)
        const p2 = helixPt(i, Math.PI + spread)
        s1.position.copy(p1)
        s2.position.copy(p2)
      }
    })
  }

  function tickUnwinding(refs, p) {
    // base-pair connectors in target region fade out
    refs.basePairs.forEach(({ cyl, s1, s2, i }) => {
      if (i >= 10 && i < DNA_BP) {
        cyl.material.opacity  = 1 - p
        cyl.material.transparent = true
        // spread strands further
        const spread = 0.3 + p * 0.5
        s1.position.copy(helixPt(i, -spread))
        s2.position.copy(helixPt(i, Math.PI + spread))
      }
    })
    // R-loop appears
    refs.rLoopGroup.visible = true
    refs.rLoopGroup.children.forEach(c => {
      if (c.material) { c.material.transparent = true; c.material.opacity = p * 0.7 }
    })
  }

  function tickHybridizing(refs, p, dt) {
    // gRNA nucleotides glow intensifies
    refs.gNucleotides.forEach((s, k) => {
      const threshold = k / refs.gNucleotides.length
      if (p > threshold && s.material) {
        s.material.emissiveIntensity = Math.min(s.material.emissiveIntensity + 0.05, 1.2)
      }
    })
  }

  function tickCleaving(refs, p, st, dt) {
    // nuclease domains move toward cut site
    const cutPos = helixPt(20, 0)
    refs.ruvc.position.lerp(new THREE.Vector3(cutPos.x, cutPos.y - 0.3, cutPos.z).add(refs.cas9.position.clone().multiplyScalar(0)), p * 0.1)
    refs.hnh.position.lerp(new THREE.Vector3(cutPos.x, cutPos.y + 0.3, cutPos.z).add(refs.cas9.position.clone().multiplyScalar(0)), p * 0.1)

    if (p > 0.5) {
      refs.cutGroup.visible = true
      // flash DNA red
      refs.basePairs.forEach(({ s1, s2, i }) => {
        if (i >= 19 && i <= 21) {
          if (s1.material) s1.material.color.setHex(0xff4444)
          if (s2.material) s2.material.color.setHex(0xff4444)
        }
      })
    }

    if (p > 0.6 && !st.particles) {
      st.particles = true
      refs.particles.forEach(s => { s.visible = true; s.position.copy(s.userData.origin) })
    }
    if (st.particles) {
      refs.particles.forEach(s => {
        if (s.visible) s.position.addScaledVector(s.userData.vel, dt * 0.15)
      })
    }

    if (p > 0.7 && !st.shaking) {
      st.shaking  = true
      st.shakeDur = 0.4
    }

    // DNA gap at cut
    if (p > 0.8) {
      refs.basePairs.forEach(({ s1, s2, i }) => {
        if (i >= 19 && i <= 22) {
          s1.position.y += dt * 0.5
          s2.position.y -= dt * 0.5
        }
      })
    }
  }

  function tickRepair(refs, p) {
    // Cas9 retreats
    refs.cas9.position.x = THREE.MathUtils.lerp(3, 14, p)
    refs.gRnaGroup.position.x = refs.cas9.position.x
    refs.lobe1.rotation.y = THREE.MathUtils.lerp(-0.26, 0, p)
    refs.lobe2.rotation.y = THREE.MathUtils.lerp(0.26, 0, p)

    // hide cut effect
    if (p > 0.2) refs.cutGroup.visible = false
    if (p > 0.2) refs.particles.forEach(s => { s.visible = false })

    // NHEJ proteins approach cut site
    refs.nhejGroup.visible = true
    refs.nhejGroup.position.x = THREE.MathUtils.lerp(
      refs.nhejGroup.userData.startX ?? (refs.nhejGroup.userData.startX = refs.nhejGroup.position.x),
      helixPt(20, 0).x,
      p,
    )

    if (p > 0.8) {
      refs.indelBase.visible = true
      refs.indelBase.material.emissiveIntensity = 0.3 + 0.3 * Math.sin(p * Math.PI * 8)
    }
  }

  // ── controls ───────────────────────────────────────────────────────────────

  const handlePlay = useCallback(() => {
    const st = stateRef.current
    if (st.phase === 'complete') return
    if (st.phase === 'idle') {
      st.phase    = 'scanning'
      st.phaseIdx = 1
      st.elapsed  = 0
      setPhase('scanning')
      setPhaseIdx(1)
    }
    st.playing = true
    setPlaying(true)
    clockRef.current.start()
  }, [])

  const handlePause = useCallback(() => {
    stateRef.current.playing = false
    setPlaying(false)
    clockRef.current.stop()
  }, [])

  const handleReset = useCallback(() => {
    const st    = stateRef.current
    st.phase    = 'idle'
    st.phaseIdx = 0
    st.elapsed  = 0
    st.playing  = false
    st.particles = false
    st.shaking  = false
    setPhase('idle')
    setPhaseIdx(0)
    setPlaying(false)
    clockRef.current.stop()

    const refs = refsRef.current
    if (!refs) return

    // reset Cas9
    refs.cas9.position.set(20, 0, 0)
    refs.gRnaGroup.position.set(20, 0, 0)
    refs.lobe1.rotation.y = 0
    refs.lobe2.rotation.y = 0

    // reset DNA
    refs.basePairs.forEach(({ s1, s2, cyl, p1, p2, i }) => {
      s1.position.copy(p1)
      s2.position.copy(p2)
      const mid = p1.clone().add(p2).multiplyScalar(0.5)
      cyl.position.copy(mid)
      if (cyl.material) { cyl.material.opacity = 1 }
      const isTarget = i >= 10 && i < DNA_BP
      if (s1.material) s1.material.color.setHex(isTarget ? 0xdddddd : 0x3a4060)
      if (s2.material) s2.material.color.setHex(isTarget ? 0xdddddd : 0x3a4060)
    })

    refs.rLoopGroup.visible = false
    refs.cutGroup.visible   = false
    refs.nhejGroup.visible  = false
    refs.indelBase.visible  = false
    refs.particles.forEach(s => { s.visible = false; s.position.copy(s.userData.origin) })
    refs.gNucleotides.forEach(s => { if (s.material) s.material.emissiveIntensity = 0.5 })
    refs.ruvc.position.set(1.8, 0.8, 0.8)
    refs.hnh.position.set(1.8, -0.8, 0.8)
  }, [])

  const handleSpeed = useCallback((s) => {
    stateRef.current.speed = s
    setSpeed(s)
  }, [])

  // ─── render ────────────────────────────────────────────────────────────────

  const activePhaseIdx = PHASES.indexOf(phase)

  const LEGEND = [
    { color: '#2a3a6a', label: 'Cas9 protein' },
    { color: T.teal,    label: 'gRNA' },
    { color: '#dddddd', label: 'Target DNA' },
    { color: T.purple,  label: 'R-loop' },
    { color: '#ff4444', label: 'Cut site' },
    { color: T.amber,   label: 'Repair proteins' },
  ]

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 560, background: T.bg, borderRadius: 8, overflow: 'hidden' }}>

      {/* 3D canvas */}
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* top-right info panel */}
      <div style={{
        position: 'absolute', top: 12, right: 12,
        background: 'rgba(21,24,33,0.88)',
        border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: '12px 16px',
        minWidth: 220, maxWidth: 260,
      }}>
        <div style={{ fontSize: 11, color: T.muted, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.7px' }}>Status</div>
        <div style={{ fontSize: 12, color: T.text, lineHeight: 1.5, marginBottom: 10 }}>{PHASE_STATUS[phase]}</div>
        <div style={{ fontSize: 11, color: T.muted, marginBottom: 3 }}>Guide sequence</div>
        <div style={{ fontSize: 11, fontFamily: 'monospace', color: T.teal, wordBreak: 'break-all', marginBottom: 8 }}>
          {guide.slice(0, 20)}<span style={{ color: T.amber }}>{guide.slice(20)}</span>
        </div>
        <div style={{ fontSize: 11, color: T.muted }}>Cut position: <span style={{ color: T.text }}>{cutPosition}</span></div>
      </div>

      {/* top-left legend */}
      <div style={{
        position: 'absolute', top: 12, left: 12,
        background: 'rgba(21,24,33,0.88)',
        border: `0.5px solid ${T.border}`,
        borderRadius: 8, padding: '10px 14px',
        display: 'flex', flexDirection: 'column', gap: 5,
      }}>
        {LEGEND.map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0, display: 'block' }} />
            <span style={{ fontSize: 11, color: T.mid }}>{label}</span>
          </div>
        ))}
      </div>

      {/* bottom control bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: T.surface,
        borderTop: `1px solid ${T.border}`,
        padding: '10px 16px',
        display: 'flex', alignItems: 'center', gap: 14,
        flexWrap: 'wrap',
      }}>
        {/* playback buttons */}
        <div style={{ display: 'flex', gap: 6 }}>
          {[
            { label: '▶ Play',   handler: handlePlay,  active: !playing },
            { label: '⏸ Pause', handler: handlePause, active: playing  },
            { label: '⏮ Reset', handler: handleReset, active: false    },
          ].map(({ label, handler, active }) => (
            <button
              key={label}
              onClick={handler}
              style={{
                padding: '5px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer',
                background: active ? T.teal : 'transparent',
                color: active ? '#04342C' : T.mid,
                border: `0.5px solid ${active ? T.teal : T.border2}`,
                fontWeight: active ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* phase dots */}
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {PHASES.slice(1).map((ph, k) => {
            const idx = k + 1
            return (
              <div
                key={ph}
                title={ph}
                style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: idx < activePhaseIdx ? T.teal
                    : idx === activePhaseIdx ? T.amber
                    : T.border2,
                  transition: 'background 0.3s',
                }}
              />
            )
          })}
        </div>

        {/* phase label */}
        <div style={{ fontSize: 12, color: T.mid, minWidth: 90 }}>
          {phase !== 'idle' ? `${phase.charAt(0).toUpperCase()}${phase.slice(1)}` : 'Ready'}
        </div>

        {/* speed */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginLeft: 'auto' }}>
          <span style={{ fontSize: 11, color: T.muted }}>Speed</span>
          {[0.5, 1, 2].map(s => (
            <button
              key={s}
              onClick={() => handleSpeed(s)}
              style={{
                padding: '3px 8px', borderRadius: 4, fontSize: 11, cursor: 'pointer',
                background: speed === s ? T.amber : 'transparent',
                color: speed === s ? '#1a0c00' : T.mid,
                border: `0.5px solid ${speed === s ? T.amber : T.border2}`,
                fontWeight: speed === s ? 700 : 400,
                transition: 'all 0.15s',
              }}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
