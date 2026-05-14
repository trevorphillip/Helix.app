import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useHelixStore } from '../store.jsx'

// ─── constants ────────────────────────────────────────────────────────────────

const HELIX_RADIUS         = 2.2
const RISE_PER_BP          = 0.34
const TURN_PER_BP          = (2 * Math.PI) / 10
const BP_COUNT             = 40

const BASE_COLOR           = { A: 0x00ff88, T: 0xffaa00, G: 0xcc88ff, C: 0xff4488 }
const BASE_EMISSIVE        = { A: 0x00cc66, T: 0xff8800, G: 0xaa66ff, C: 0xdd2266 }
const BASE_EMISSIVE_INT    = { A: 0.5,      T: 0.5,      G: 0.4,      C: 0.4      }
const GRNA_BASE_COLOR      = { A: 0x00e5a0, T: 0xffaa00, G: 0xaa88ff, C: 0xff6688 }
const COMPLEMENT           = { A: 'T', T: 'A', G: 'C', C: 'G' }

const PHASES = ['idle', 'scanning', 'binding', 'unwinding', 'hybridizing', 'cleaving', 'repair', 'complete']

const PHASE_DURATIONS = { scanning: 3, binding: 2, unwinding: 2, hybridizing: 2, cleaving: 1, repair: 3, complete: 99 }

const STATUS_TEXT = {
  idle:        'Ready — press Play to animate',
  scanning:    'Cas9 scanning DNA for PAM sequence (NGG)...',
  binding:     'PAM site found — Cas9 binds to DNA...',
  unwinding:   'DNA strands separate — R-loop forming...',
  hybridizing: 'gRNA hybridizing to target strand...',
  cleaving:    'DOUBLE STRAND BREAK — DNA cleaved!',
  repair:      'NHEJ repair — indel introduced at cut site...',
  complete:    'Edit complete!',
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
}

function helixPt(i, angleOffset = 0) {
  const a = i * TURN_PER_BP + angleOffset
  return new THREE.Vector3(HELIX_RADIUS * Math.cos(a), i * RISE_PER_BP, HELIX_RADIUS * Math.sin(a))
}

function disposeObject(obj) {
  obj.traverse(o => {
    o.geometry?.dispose()
    if (Array.isArray(o.material)) o.material.forEach(m => m.dispose())
    else o.material?.dispose()
  })
}

// ─── helix builder ────────────────────────────────────────────────────────────

function buildHelix(seq, bpOffset, grnas, orfs, renderMode, cutPlanesOut) {
  const group = new THREE.Group()
  const nBp   = seq.length
  if (nBp === 0) return group

  if (renderMode !== 'bases') {
    const backboneMats = [
      new THREE.MeshPhysicalMaterial({
        color: 0x004422, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.4,
        metalness: 0.2, roughness: 0.6, transmission: 0.3, thickness: 0.5,
        transparent: true, opacity: 0.95,
      }),
      new THREE.MeshPhysicalMaterial({
        color: 0x003318, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.4,
        metalness: 0.2, roughness: 0.6, transmission: 0.3, thickness: 0.5,
        transparent: true, opacity: 0.95,
      }),
    ]
    for (let mi = 0; mi < 2; mi++) {
      const off   = mi === 0 ? 0 : Math.PI
      const pts   = Array.from({ length: nBp + 1 }, (_, i) => helixPt(i, off))
      const curve = new THREE.CatmullRomCurve3(pts)
      const geo   = new THREE.TubeGeometry(curve, nBp * 8, 0.12, 8, false)
      group.add(new THREE.Mesh(geo, backboneMats[mi]))
    }
  }

  if (renderMode !== 'backbone') {
    const yAxis = new THREE.Vector3(0, 1, 0)
    for (let i = 0; i < nBp; i++) {
      const base = (seq[i] || 'A').toUpperCase()
      const comp = COMPLEMENT[base] || 'T'
      const p1   = helixPt(i, 0)
      const p2   = helixPt(i, Math.PI)
      const col1 = BASE_COLOR[base]        ?? 0x00ff88
      const col2 = BASE_COLOR[comp]        ?? 0x00ff88
      const em1  = BASE_EMISSIVE[base]     ?? 0x008844
      const em2  = BASE_EMISSIVE[comp]     ?? 0x008844
      const ei1  = BASE_EMISSIVE_INT[base] ?? 0.4
      const ei2  = BASE_EMISSIVE_INT[comp] ?? 0.4

      const s1 = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 8, 8),
        new THREE.MeshPhysicalMaterial({
          color: col1, emissive: new THREE.Color(em1), emissiveIntensity: ei1,
          metalness: 0.1, roughness: 0.2, transmission: 0.4, thickness: 1.0,
          transparent: true, opacity: 0.9,
        }),
      )
      s1.position.copy(p1)
      s1.userData.isForwardBase = true
      s1.userData.bpIndex       = i
      s1.userData.origColor     = col1
      s1.userData.origPos       = p1.clone()
      group.add(s1)

      const glow1 = new THREE.Mesh(
        new THREE.SphereGeometry(0.35, 8, 8),
        new THREE.MeshBasicMaterial({ color: col1, transparent: true, opacity: 0.08 }),
      )
      glow1.position.copy(p1)
      group.add(glow1)

      const s2 = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 8, 8),
        new THREE.MeshPhysicalMaterial({
          color: col2, emissive: new THREE.Color(em2), emissiveIntensity: ei2,
          metalness: 0.1, roughness: 0.2, transmission: 0.4, thickness: 1.0,
          transparent: true, opacity: 0.9,
        }),
      )
      s2.position.copy(p2)
      s2.userData.bpIndex   = i
      s2.userData.origColor = col2
      s2.userData.origPos   = p2.clone()
      group.add(s2)

      const mid = p1.clone().add(p2).multiplyScalar(0.5)
      const dir = p2.clone().sub(p1)
      const cyl = new THREE.Mesh(
        new THREE.CylinderGeometry(0.05, 0.05, dir.length(), 6),
        new THREE.MeshPhysicalMaterial({
          color: 0x004433, metalness: 0.4, roughness: 0.5, transparent: true, opacity: 0.25,
        }),
      )
      cyl.position.copy(mid)
      cyl.quaternion.setFromUnitVectors(yAxis, dir.normalize())
      cyl.userData.isConnector     = true
      cyl.userData.bpIndex         = i
      cyl.userData.origOpacity     = 0.25
      cyl.userData.origTransparent = true
      group.add(cyl)
    }
  }

  grnas.forEach((grna, gi) => {
    const relStart = grna.pos - bpOffset
    const relEnd   = relStart + 20
    const cS = Math.max(0, relStart)
    const cE = Math.min(nBp, relEnd)
    if (cE <= cS) return

    const pts = Array.from({ length: (cE - cS + 1) * 4 }, (_, k) => {
      const t = cS + k / 4
      const a = t * TURN_PER_BP
      return new THREE.Vector3(
        (HELIX_RADIUS + 0.6) * Math.cos(a),
        t * RISE_PER_BP,
        (HELIX_RADIUS + 0.6) * Math.sin(a),
      )
    })
    if (pts.length < 2) return
    group.add(new THREE.Mesh(
      new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length * 2, 0.2, 8, false),
      new THREE.MeshPhysicalMaterial({
        color: 0x00ffaa, emissive: new THREE.Color(0x00ff88), emissiveIntensity: 0.9,
        metalness: 0.0, roughness: 0.1, transparent: true, opacity: 0.7,
      }),
    ))

    const cutRel  = cS + Math.min(17, cE - cS - 1)
    const planeMat = new THREE.MeshBasicMaterial({ color: 0x00ffaa, transparent: true, opacity: 0.3, side: THREE.DoubleSide })
    const plane    = new THREE.Mesh(new THREE.CircleGeometry(HELIX_RADIUS + 1.2, 32), planeMat)
    plane.position.set(0, cutRel * RISE_PER_BP, 0)
    plane.rotation.x = Math.PI / 2
    group.add(plane)
    cutPlanesOut.push({ mesh: plane, phaseOffset: gi })
  })

  for (let i = 0; i < nBp; i++) {
    const win  = seq.slice(Math.max(0, i - 4), Math.min(nBp, i + 5))
    const gc   = win.length ? [...win].filter(b => b === 'G' || b === 'C').length / win.length : 0
    const barH = Math.max(gc * 1.4, 0.03)
    const bar  = new THREE.Mesh(
      new THREE.BoxGeometry(0.22, barH, 0.12),
      new THREE.MeshPhongMaterial({ color: gc >= 0.5 ? 0x00ff88 : 0x0a2a14 }),
    )
    bar.position.set(5.5, i * RISE_PER_BP + barH / 2, 0)
    group.add(bar)
  }

  orfs.forEach(orf => {
    const cS = Math.max(0, orf.start - bpOffset)
    const cE = Math.min(nBp, orf.end - bpOffset)
    if (cE <= cS) return
    const h = (cE - cS) * RISE_PER_BP
    const m = new THREE.Mesh(
      new THREE.BoxGeometry(0.44, Math.max(h, 0.05), 0.22),
      new THREE.MeshPhongMaterial({ color: orf.frame?.startsWith('+') ? 0x00ff88 : 0xffaa00, transparent: true, opacity: 0.65 }),
    )
    m.position.set(-5.5, cS * RISE_PER_BP + h / 2, 0)
    group.add(m)
  })

  return group
}

// ─── Cas9 builder ─────────────────────────────────────────────────────────────

function buildCas9() {
  const group = new THREE.Group()

  const lobe1 = new THREE.Mesh(
    new THREE.BoxGeometry(2.5, 1.8, 1.8, 4, 4, 4),
    new THREE.MeshPhysicalMaterial({
      color: 0x112255, emissive: new THREE.Color(0x081830), emissiveIntensity: 0.4,
      metalness: 0.7, roughness: 0.15, envMapIntensity: 1.2,
    }),
  )
  lobe1.name = 'lobe1'
  group.add(lobe1)
  lobe1.add(new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(2.5, 1.8, 1.8)),
    new THREE.LineBasicMaterial({ color: 0x2244aa, transparent: true, opacity: 0.4 }),
  ))

  const lobe2 = new THREE.Mesh(
    new THREE.BoxGeometry(2.0, 1.6, 1.6, 4, 4, 4),
    new THREE.MeshPhysicalMaterial({
      color: 0x112255, emissive: new THREE.Color(0x081830), emissiveIntensity: 0.4,
      metalness: 0.7, roughness: 0.15, envMapIntensity: 1.2,
    }),
  )
  lobe2.name = 'lobe2'
  lobe2.position.set(-2.2, 0, 0)
  group.add(lobe2)
  lobe2.add(new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(2.0, 1.6, 1.6)),
    new THREE.LineBasicMaterial({ color: 0x2244aa, transparent: true, opacity: 0.4 }),
  ))

  const hinge = new THREE.Mesh(
    new THREE.CylinderGeometry(0.3, 0.3, 0.8, 12),
    new THREE.MeshPhysicalMaterial({ color: 0x334477, metalness: 0.7, roughness: 0.3 }),
  )
  hinge.rotation.z = Math.PI / 2
  hinge.position.set(-1.1, 0, 0)
  group.add(hinge)

  const hnh = new THREE.Mesh(
    new THREE.SphereGeometry(0.35, 16, 16),
    new THREE.MeshPhysicalMaterial({
      color: 0xff2244, emissive: new THREE.Color(0xff0000), emissiveIntensity: 0.8,
      metalness: 0.9, roughness: 0.05,
    }),
  )
  hnh.name = 'hnh'
  hnh.position.set(-1.7, -0.9, 0.8)
  group.add(hnh)

  const hnhGlow = new THREE.Mesh(
    new THREE.SphereGeometry(0.35, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.15 }),
  )
  hnhGlow.name = 'hnhGlow'
  hnhGlow.scale.setScalar(2.0)
  hnhGlow.position.copy(hnh.position)
  group.add(hnhGlow)

  const ruvc = new THREE.Mesh(
    new THREE.SphereGeometry(0.35, 16, 16),
    new THREE.MeshPhysicalMaterial({
      color: 0xffaa00, emissive: new THREE.Color(0xff8800), emissiveIntensity: 0.7,
      metalness: 0.9, roughness: 0.05,
    }),
  )
  ruvc.name = 'ruvc'
  ruvc.position.set(-1.7, 0.9, 0.8)
  group.add(ruvc)

  const ruvcGlow = new THREE.Mesh(
    new THREE.SphereGeometry(0.35, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.12 }),
  )
  ruvcGlow.name = 'ruvcGlow'
  ruvcGlow.scale.setScalar(2.0)
  ruvcGlow.position.copy(ruvc.position)
  group.add(ruvcGlow)

  return group
}

// ─── gRNA builder ─────────────────────────────────────────────────────────────

function buildGrna(guide) {
  const group = new THREE.Group()
  const bases = (guide || '').slice(0, 20).toUpperCase()
  const pts   = []

  for (let k = 0; k < 20; k++) {
    const pos = new THREE.Vector3(-k * 0.3, 0, 0)
    pts.push(pos.clone())
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 10, 10),
      new THREE.MeshPhysicalMaterial({
        color: 0x00ffaa, emissive: new THREE.Color(0x00ff88), emissiveIntensity: 0.9,
        metalness: 0.0, roughness: 0.1, transparent: true, opacity: 0.9,
      }),
    )
    sphere.position.copy(pos)
    group.add(sphere)
  }

  if (pts.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(pts)
    group.add(new THREE.Mesh(
      new THREE.TubeGeometry(curve, 60, 0.04, 8, false),
      new THREE.MeshPhysicalMaterial({
        color: 0x00ffaa, emissive: new THREE.Color(0x00ff88), emissiveIntensity: 0.9,
        metalness: 0.0, roughness: 0.1, transparent: true, opacity: 0.7,
      }),
    ))
  }

  return group
}

// ─── component ────────────────────────────────────────────────────────────────

export default function DnaHelix3D({ sequence, grnas = [], orfs = [], selectedGrna = null, outcomeLabels = null }) {
  const mountRef         = useRef(null)
  const rendererRef      = useRef(null)
  const sceneRef         = useRef(null)
  const cameraRef        = useRef(null)
  const controlsRef      = useRef(null)
  const helixGroupRef    = useRef(null)
  const cutPlanesRef     = useRef([])
  const rafRef           = useRef(null)
  const idleTimerRef     = useRef(null)
  const cas9Ref          = useRef(null)
  const grnaRef          = useRef(null)
  const cas9LightRef     = useRef(null)
  const particlesRef     = useRef([])
  const causticLightsRef = useRef([])
  const bgShapesRef      = useRef([])
  const cutParticlesRef  = useRef([])

  // animation refs — always current, readable inside rAF loop
  const phaseRef       = useRef('idle')
  const playingRef     = useRef(false)
  const phaseStartTime = useRef(0)
  const clock          = useRef(new THREE.Clock(false))
  const bpOffsetRef    = useRef(0)
  const animGrnaRef    = useRef(null)

  const [bpOffset, setBpOffset]     = useState(0)
  const [renderMode, setRenderMode] = useState('full')
  const [animMode, setAnimMode]     = useState(false)
  const [animGrna, setAnimGrna]     = useState(null)
  const [phase, setPhase]           = useState('idle')
  const [playing, setPlaying]       = useState(false)

  const navigate              = useNavigate()
  const { update: storeUpdate } = useHelixStore()

  const seq    = (sequence || '').replace(/[^ACGTacgt]/gi, '').toUpperCase()
  const seqLen = seq.length
  const slice  = seq.slice(bpOffset, bpOffset + BP_COUNT)

  function syncBpOffset(v)  { bpOffsetRef.current = v;  setBpOffset(v) }
  function syncAnimGrna(g)  { animGrnaRef.current = g;  setAnimGrna(g) }
  function syncPhase(p)     { phaseRef.current    = p;  setPhase(p) }
  function syncPlaying(v)   { playingRef.current  = v;  setPlaying(v) }

  useEffect(() => {
    if (!selectedGrna) return
    syncBpOffset(Math.max(0, (selectedGrna.pos ?? 0) - 5))
  }, [selectedGrna])

  // ── one-time renderer / scene / controls setup ────────────────────────────
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const w = mount.clientWidth || 600
    const h = mount.clientHeight || 500

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(w, h)
    renderer.shadowMap.enabled  = true
    renderer.shadowMap.type     = THREE.PCFSoftShadowMap
    renderer.toneMapping        = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.4
    renderer.outputColorSpace   = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x020a06)
    scene.fog        = new THREE.FogExp2(0x020a06, 0.018)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200)
    camera.position.set(0, 6, 22)
    cameraRef.current = camera

    // ── lighting ──────────────────────────────────────────────────────────
    scene.add(new THREE.AmbientLight(0x0a1a0a, 0.5))

    const keyLight = new THREE.PointLight(0x00ff88, 4.0, 50, 2)
    keyLight.position.set(-8, 12, 8)
    keyLight.castShadow          = true
    keyLight.shadow.mapSize.width  = 1024
    keyLight.shadow.mapSize.height = 1024
    scene.add(keyLight)

    const fillLight = new THREE.PointLight(0xffaa00, 2.0, 40, 2)
    fillLight.position.set(10, -6, 10)
    scene.add(fillLight)

    const rimLight = new THREE.PointLight(0x00aa44, 3.0, 60, 2)
    rimLight.position.set(-12, 0, -8)
    scene.add(rimLight)

    const underLight = new THREE.PointLight(0x004422, 2.5, 30, 2)
    underLight.position.set(0, -12, 0)
    scene.add(underLight)

    const cas9Light = new THREE.PointLight(0x4488ff, 2.0, 20, 2)
    scene.add(cas9Light)
    cas9LightRef.current = cas9Light

    // ── bioluminescent floor ──────────────────────────────────────────────
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 40),
      new THREE.MeshPhysicalMaterial({
        color: 0x001a0a, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.3,
        metalness: 0.1, roughness: 0.8,
      }),
    )
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -8
    floor.receiveShadow = true
    scene.add(floor)

    // ── caustic lights ────────────────────────────────────────────────────
    const causticLights = []
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2
      const bx    = Math.cos(angle) * 12
      const bz    = Math.sin(angle) * 12
      const cl    = new THREE.PointLight(0x003322, 1.5, 15)
      cl.position.set(bx, -7.5, bz)
      cl.userData  = { baseX: bx, baseZ: bz, index: i }
      scene.add(cl)
      causticLights.push(cl)
    }
    causticLightsRef.current = causticLights

    // ── background organic shapes ─────────────────────────────────────────
    const bgShapes = []
    for (let i = 0; i < 6; i++) {
      const r    = Math.random() * 3 + 2
      const dir  = Math.random() > 0.5 ? 1 : -1
      const mesh = new THREE.Mesh(
        new THREE.TorusGeometry(r, 0.1, 8, 40),
        new THREE.MeshBasicMaterial({ color: 0x003322, transparent: true, opacity: 0.15 }),
      )
      mesh.position.set(
        (Math.random() - 0.5) * 30,
        (Math.random() - 0.5) * 16,
        -(Math.random() * 10 + 15),
      )
      mesh.userData = { dir }
      scene.add(mesh)
      bgShapes.push(mesh)
    }
    bgShapesRef.current = bgShapes

    // ── floating cellular particles ───────────────────────────────────────
    const particleColors = [0x004422, 0x002211, 0x113300]
    const particles = []
    for (let i = 0; i < 200; i++) {
      const r     = Math.random() * 0.09 + 0.03
      const color = particleColors[Math.floor(Math.random() * 3)]
      const p     = new THREE.Mesh(
        new THREE.SphereGeometry(r, 6, 6),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: Math.random() * 0.3 + 0.3 }),
      )
      const phi   = Math.random() * Math.PI * 2
      const theta = Math.acos(2 * Math.random() - 1)
      const rad   = 25 * Math.cbrt(Math.random())
      p.position.set(
        rad * Math.sin(theta) * Math.cos(phi),
        rad * Math.sin(theta) * Math.sin(phi),
        rad * Math.cos(theta),
      )
      p.userData = { speed: Math.random() * 0.3 + 0.1, offset: Math.random() * Math.PI * 2 }
      scene.add(p)
      particles.push(p)
    }
    particlesRef.current = particles

    // ── ambient background helices ────────────────────────────────────────
    const ambientHelices = []
    const ambientPositions = [
      [-8, 2, -18, 0.4], [9, -3, -20, -0.6], [-12, 5, -22, 1.1], [6, 1, -16, -0.3],
    ]
    for (const [xOff, yOff, zOff, rotY] of ambientPositions) {
      const hGroup = new THREE.Group()
      for (const off of [0, Math.PI]) {
        const pts   = Array.from({ length: 16 }, (_, i) => {
          const a = i * TURN_PER_BP + off
          return new THREE.Vector3(0.8 * Math.cos(a), i * RISE_PER_BP, 0.8 * Math.sin(a))
        })
        const curve = new THREE.CatmullRomCurve3(pts)
        hGroup.add(new THREE.Mesh(
          new THREE.TubeGeometry(curve, 60, 0.04, 6, false),
          new THREE.MeshBasicMaterial({ color: 0x003322, transparent: true, opacity: 0.1 }),
        ))
      }
      hGroup.position.set(xOff, yOff, zOff)
      hGroup.rotation.y = rotY
      scene.add(hGroup)
      ambientHelices.push(hGroup)
    }

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 6, 0)
    controls.autoRotate      = true
    controls.autoRotateSpeed = 0.4
    controls.enableDamping   = true
    controls.dampingFactor   = 0.05
    controls.update()
    controlsRef.current = controls

    const stopAuto = () => {
      controls.autoRotate = false
      clearTimeout(idleTimerRef.current)
      idleTimerRef.current = setTimeout(() => { controls.autoRotate = true }, 3000)
    }
    renderer.domElement.addEventListener('pointerdown', stopAuto)

    // ── animation tick (runs inside rAF — reads refs, never stale) ──────────
    function tickAnimation(now) {
      const ph       = phaseRef.current
      if (ph === 'idle' || ph === 'complete') return

      const elapsed  = clock.current.getElapsedTime() - phaseStartTime.current
      const duration = PHASE_DURATIONS[ph] ?? 2
      const progress = Math.min(elapsed / duration, 1)
      const ag       = animGrnaRef.current
      const startBp  = bpOffsetRef.current
      const cas9     = cas9Ref.current
      const grna     = grnaRef.current
      const helix    = helixGroupRef.current
      const grnaY    = ag ? (ag.pos - startBp + 10) * RISE_PER_BP : 0

      if (!cas9) return

      if (ph === 'scanning') {
        cas9.position.x = THREE.MathUtils.lerp(HELIX_RADIUS * 4, HELIX_RADIUS * 1.8, easeInOut(progress))
        cas9.position.y = THREE.MathUtils.lerp(0, grnaY, easeInOut(progress))
        cas9.rotation.y = Math.sin(elapsed * 2) * 0.1
        if (grna) grna.visible = progress > 0.3
      }

      if (ph === 'binding') {
        cas9.position.x = THREE.MathUtils.lerp(HELIX_RADIUS * 1.8, HELIX_RADIUS * 1.3, easeInOut(progress))
        const lobe1 = cas9.getObjectByName('lobe1')
        const lobe2 = cas9.getObjectByName('lobe2')
        if (lobe1) lobe1.rotation.z = THREE.MathUtils.lerp(0,  0.3, progress)
        if (lobe2) lobe2.rotation.z = THREE.MathUtils.lerp(0, -0.3, progress)
        if (ag && helix) {
          const relStart = ag.pos - startBp
          helix.traverse(obj => {
            if (obj.userData.bpIndex !== undefined) {
              const bp = obj.userData.bpIndex
              if (bp >= relStart && bp <= relStart + 20 && obj.material?.emissive) {
                obj.material.emissive.setHex(obj.userData.origColor ?? 0xffffff)
                obj.material.emissiveIntensity = THREE.MathUtils.lerp(0, 0.8, progress)
              }
            }
          })
        }
      }

      if (ph === 'unwinding') {
        if (ag && helix) {
          const relStart = ag.pos - startBp
          helix.traverse(obj => {
            const bp = obj.userData.bpIndex
            const inRange = bp >= relStart && bp <= relStart + 20
            if (obj.userData.isConnector && inRange && obj.material) {
              obj.material.transparent = true
              obj.material.opacity     = THREE.MathUtils.lerp(1, 0, progress)
              obj.material.needsUpdate = true
            }
            if (obj.userData.isForwardBase && inRange && obj.userData.origPos) {
              const orig = obj.userData.origPos
              obj.position.x = THREE.MathUtils.lerp(orig.x, orig.x + 0.3, progress)
            }
          })
        }
      }

      if (ph === 'hybridizing') {
        if (grna) {
          const spheresDone = Math.floor(progress * 20)
          grna.children.forEach((child, i) => {
            if (i < spheresDone && child.isMesh && child.material) {
              child.material.emissiveIntensity = 1.0
              child.scale.setScalar(1 + 0.3 * Math.sin(now / 200 + i))
            }
          })
        }
      }

      if (ph === 'cleaving') {
        if (ag && helix) {
          const cutBp = ag.pos - startBp + 17
          helix.traverse(obj => {
            if (obj.userData.bpIndex === cutBp && obj.material?.color) {
              obj.material.color.setHex(0xff2244)
              if (obj.material.emissive) {
                obj.material.emissive.setHex(0xff0000)
                obj.material.emissiveIntensity = 0.5 + 0.5 * Math.sin(elapsed * 20)
              }
            }
          })
        }
        if (progress < 0.4) {
          const shake = (0.4 - progress) / 0.4
          camera.position.x += (Math.random() - 0.5) * 0.08 * shake
          camera.position.y += (Math.random() - 0.5) * 0.08 * shake
        }
        const hnh  = cas9.getObjectByName('hnh')
        const ruvc = cas9.getObjectByName('ruvc')
        const hnhG = cas9.getObjectByName('hnhGlow')
        const ruvcG= cas9.getObjectByName('ruvcGlow')
        if (hnh)  { hnh.position.x  = THREE.MathUtils.lerp(-1.7, -4.2, progress); if (hnhG)  hnhG.position.x  = hnh.position.x }
        if (ruvc) { ruvc.position.x = THREE.MathUtils.lerp(-1.7, -4.2, progress); if (ruvcG) ruvcG.position.x = ruvc.position.x }

        // spawn cut particles once
        if (progress < 0.05 && cutParticlesRef.current.length === 0 && ag) {
          const cutY = (ag.pos - startBp + 17) * RISE_PER_BP
          for (let j = 0; j < 50; j++) {
            const cp = new THREE.Mesh(
              new THREE.SphereGeometry(0.06, 6, 6),
              new THREE.MeshBasicMaterial({
                color: Math.random() > 0.5 ? 0xff2244 : 0xff8800,
                transparent: true, opacity: 1,
              }),
            )
            cp.position.set(0, cutY, 0)
            cp.userData.vx = (Math.random() - 0.5) * 0.15
            cp.userData.vy = (Math.random() - 0.5) * 0.15
            cp.userData.vz = (Math.random() - 0.5) * 0.15
            scene.add(cp)
            cutParticlesRef.current.push(cp)
          }
        }
      }

      if (ph === 'repair') {
        cas9.position.x = THREE.MathUtils.lerp(HELIX_RADIUS * 1.3, HELIX_RADIUS * 4, easeInOut(progress))
        if (grna) {
          grna.children.forEach(child => {
            if (child.material) {
              child.material.opacity     = THREE.MathUtils.lerp(1, 0, progress)
              child.material.transparent = true
              child.material.needsUpdate = true
            }
          })
        }
        if (helix) {
          helix.traverse(obj => {
            if (obj.userData.isConnector && obj.material) {
              obj.material.opacity     = THREE.MathUtils.lerp(0, 1, progress)
              obj.material.transparent = false
              obj.material.needsUpdate = true
            }
          })
        }
      }

      // advance phase when complete
      if (progress >= 1) {
        const idx = PHASES.indexOf(ph)
        if (idx >= 0 && idx < PHASES.length - 1) {
          const next = PHASES[idx + 1]
          phaseRef.current       = next
          phaseStartTime.current = clock.current.getElapsedTime()
          setPhase(next)
          if (next === 'complete') {
            playingRef.current = false
            setPlaying(false)
          }
        }
      }
    }

    function animate() {
      rafRef.current = requestAnimationFrame(animate)
      controls.update()
      const now  = Date.now()
      const time = now / 1000

      cutPlanesRef.current.forEach(({ mesh, phaseOffset }) => {
        mesh.material.opacity = 0.3 + 0.2 * Math.sin(now / 500 + phaseOffset)
      })

      // floating particles
      particlesRef.current.forEach(p => {
        const { speed, offset } = p.userData
        p.position.x += Math.sin(time * speed + offset) * 0.002
        p.position.y += Math.cos(time * speed + offset) * 0.002
        p.position.z += Math.sin(time * speed * 0.7 + offset) * 0.001
      })

      // caustic lights
      causticLightsRef.current.forEach(cl => {
        const { baseX, baseZ, index: i } = cl.userData
        cl.position.x = baseX + Math.sin(time * 0.5 + i) * 2
        cl.position.z = baseZ + Math.cos(time * 0.5 + i) * 2
      })

      // background organic shapes
      bgShapesRef.current.forEach(s => { s.rotation.z += 0.001 * s.userData.dir })

      // cas9 follow light
      if (cas9LightRef.current) {
        cas9LightRef.current.visible = !!cas9Ref.current
        if (cas9Ref.current) cas9LightRef.current.position.copy(cas9Ref.current.position)
      }

      // cut particles
      cutParticlesRef.current = cutParticlesRef.current.filter(p => {
        p.position.x += p.userData.vx
        p.position.y += p.userData.vy
        p.position.z += p.userData.vz
        p.material.opacity -= 0.02
        if (p.material.opacity <= 0) {
          scene.remove(p)
          p.geometry.dispose()
          p.material.dispose()
          return false
        }
        return true
      })

      if (playingRef.current && cas9Ref.current) {
        tickAnimation(now)
      } else if (cas9Ref.current && !playingRef.current) {
        cas9Ref.current.rotation.y = now / 3000
      }

      renderer.render(scene, camera)
    }
    animate()

    const ro = new ResizeObserver(() => {
      const nw = mount.clientWidth
      const nh = mount.clientHeight || 500
      camera.aspect = nw / nh
      camera.updateProjectionMatrix()
      renderer.setSize(nw, nh)
    })
    ro.observe(mount)

    return () => {
      cancelAnimationFrame(rafRef.current)
      clearTimeout(idleTimerRef.current)
      ro.disconnect()
      controls.dispose()
      renderer.domElement.removeEventListener('pointerdown', stopAuto)
      if (cas9Ref.current) { disposeObject(cas9Ref.current); cas9Ref.current = null }
      particlesRef.current.forEach(p => { scene.remove(p); p.geometry.dispose(); p.material.dispose() })
      causticLightsRef.current.forEach(cl => scene.remove(cl))
      bgShapesRef.current.forEach(s => { disposeObject(s); scene.remove(s) })
      ambientHelices.forEach(h => { disposeObject(h); scene.remove(h) })
      cutParticlesRef.current.forEach(p => { scene.remove(p); p.geometry.dispose(); p.material.dispose() })
      if (cas9LightRef.current) { scene.remove(cas9LightRef.current); cas9LightRef.current = null }
      renderer.dispose()
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
    }
  }, [])

  // ── rebuild helix ─────────────────────────────────────────────────────────
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    if (helixGroupRef.current) {
      scene.remove(helixGroupRef.current)
      disposeObject(helixGroupRef.current)
    }
    cutPlanesRef.current = []
    const group = buildHelix(slice, bpOffset, grnas, orfs, renderMode, cutPlanesRef.current)
    scene.add(group)
    helixGroupRef.current = group
    if (controlsRef.current) {
      const cy = (slice.length * RISE_PER_BP) / 2
      controlsRef.current.target.set(0, cy, 0)
      controlsRef.current.update()
    }
  }, [slice, bpOffset, grnas, orfs, renderMode])

  // ── manage Cas9 + gRNA ────────────────────────────────────────────────────
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    if (cas9Ref.current) {
      scene.remove(cas9Ref.current)
      disposeObject(cas9Ref.current)
      cas9Ref.current = null
      grnaRef.current = null
    }
    if (!animMode || !animGrna) return

    const relIdx    = (animGrna.pos - bpOffset) + 10
    const y         = relIdx * RISE_PER_BP
    const cas9Group = buildCas9()
    const grnaGroup = buildGrna(animGrna.guide || '')
    grnaGroup.visible = false
    grnaGroup.position.set(1.2, 0, 0)
    cas9Group.add(grnaGroup)
    cas9Group.position.set(HELIX_RADIUS * 4, y, 0)
    scene.add(cas9Group)
    cas9Ref.current = cas9Group
    grnaRef.current = grnaGroup
  }, [animMode, animGrna, bpOffset])

  // ── material reset helper ─────────────────────────────────────────────────
  function resetHelixMaterials() {
    const helix = helixGroupRef.current
    if (!helix) return
    helix.traverse(obj => {
      if (obj.userData.origColor !== undefined && obj.material?.color) {
        obj.material.color.setHex(obj.userData.origColor)
        if (obj.material.emissive) obj.material.emissive.setHex(0x000000)
        obj.material.emissiveIntensity = 0
      }
      if (obj.userData.origOpacity !== undefined && obj.material) {
        obj.material.opacity     = obj.userData.origOpacity
        obj.material.transparent = obj.userData.origTransparent ?? false
        obj.material.needsUpdate = true
      }
      if (obj.userData.origPos) {
        obj.position.copy(obj.userData.origPos)
      }
    })
  }

  function clearCutParticles() {
    const scene = sceneRef.current
    if (scene) {
      cutParticlesRef.current.forEach(p => { scene.remove(p); p.geometry.dispose(); p.material.dispose() })
    }
    cutParticlesRef.current = []
  }

  // ── animation handlers ────────────────────────────────────────────────────
  function handlePlayAnim() {
    const cas9 = cas9Ref.current
    const grna = grnaRef.current
    const ag   = animGrnaRef.current
    if (!cas9 || !ag) return

    clearCutParticles()
    resetHelixMaterials()

    cas9.position.set(HELIX_RADIUS * 4, 0, 0)
    cas9.rotation.set(0, 0, 0)
    const lobe1 = cas9.getObjectByName('lobe1')
    const lobe2 = cas9.getObjectByName('lobe2')
    const hnh   = cas9.getObjectByName('hnh')
    const ruvc  = cas9.getObjectByName('ruvc')
    const hnhG  = cas9.getObjectByName('hnhGlow')
    const ruvcG = cas9.getObjectByName('ruvcGlow')
    if (lobe1) lobe1.rotation.z = 0
    if (lobe2) lobe2.rotation.z = 0
    if (hnh)  { hnh.position.set(-1.7, -0.9, 0.8);  if (hnhG)  hnhG.position.copy(hnh.position)  }
    if (ruvc) { ruvc.position.set(-1.7, 0.9, 0.8);  if (ruvcG) ruvcG.position.copy(ruvc.position) }

    if (grna) {
      grna.visible = false
      grna.children.forEach(child => {
        if (child.material) {
          child.material.opacity          = child.material.opacity < 1 ? 0.8 : 1
          child.material.emissiveIntensity = 0.7
          child.material.needsUpdate      = true
        }
        child.scale.setScalar(1)
      })
    }

    clock.current.start()
    phaseStartTime.current = clock.current.getElapsedTime()
    syncPhase('scanning')
    syncPlaying(true)
  }

  function handlePauseAnim() {
    if (playingRef.current) {
      clock.current.stop()
      syncPlaying(false)
    } else {
      clock.current.start()
      phaseStartTime.current = clock.current.getElapsedTime() - (PHASE_DURATIONS[phaseRef.current] ?? 2) * 0
      syncPlaying(true)
    }
  }

  function handleResetAnim() {
    clock.current.stop()
    syncPlaying(false)
    syncPhase('idle')
    clearCutParticles()
    resetHelixMaterials()

    const cas9 = cas9Ref.current
    const grna = grnaRef.current
    if (!cas9) return

    const ag      = animGrnaRef.current
    const startBp = bpOffsetRef.current
    const y       = ag ? (ag.pos - startBp + 10) * RISE_PER_BP : 0

    cas9.position.set(HELIX_RADIUS * 4, y, 0)
    cas9.rotation.set(0, 0, 0)
    const lobe1 = cas9.getObjectByName('lobe1')
    const lobe2 = cas9.getObjectByName('lobe2')
    const hnh   = cas9.getObjectByName('hnh')
    const ruvc  = cas9.getObjectByName('ruvc')
    const hnhG  = cas9.getObjectByName('hnhGlow')
    const ruvcG = cas9.getObjectByName('ruvcGlow')
    if (lobe1) lobe1.rotation.z = 0
    if (lobe2) lobe2.rotation.z = 0
    if (hnh)  { hnh.position.set(-1.7, -0.9, 0.8);  if (hnhG)  hnhG.position.copy(hnh.position)  }
    if (ruvc) { ruvc.position.set(-1.7, 0.9, 0.8);  if (ruvcG) ruvcG.position.copy(ruvc.position) }

    if (grna) {
      grna.visible = false
      grna.children.forEach(child => {
        if (child.material) { child.material.opacity = child.material.opacity < 1 ? 0.8 : 1; child.material.needsUpdate = true }
        child.scale.setScalar(1)
      })
    }
  }

  // ── other handlers ────────────────────────────────────────────────────────
  function handleReset() {
    const cam  = cameraRef.current
    const ctrl = controlsRef.current
    if (!cam || !ctrl) return
    cam.position.set(0, 6, 22)
    ctrl.target.set(0, (slice.length * RISE_PER_BP) / 2, 0)
    ctrl.update()
  }

  function handleScreenshot() {
    const renderer = rendererRef.current
    if (!renderer) return
    const a = document.createElement('a')
    a.href     = renderer.domElement.toDataURL('image/png')
    a.download = 'dna-helix.png'
    a.click()
  }

  function handleAnimModeToggle() {
    const next = !animMode
    setAnimMode(next)
    if (next && !animGrna && grnas.length > 0) {
      const first = grnas[0]
      syncAnimGrna(first)
      syncBpOffset(Math.max(0, (first.pos ?? 0) - 5))
    }
    if (!next) {
      syncAnimGrna(null)
      handleResetAnim()
    }
  }

  function handleAnimGrnaChange(e) {
    const idx  = parseInt(e.target.value, 10)
    const grna = grnas[idx]
    if (!grna) return
    syncAnimGrna(grna)
    syncBpOffset(Math.max(0, (grna.pos ?? 0) - 5))
  }

  function handleStartAnimation() {
    if (!animGrna) return
    storeUpdate({ selectedGuide: animGrna })
    navigate('/animation')
  }

  // ── derived ───────────────────────────────────────────────────────────────
  const canPrev      = bpOffset > 0
  const canNext      = bpOffset + BP_COUNT < seqLen
  const bpEnd        = Math.min(bpOffset + BP_COUNT, seqLen)
  const animGrnaIdx  = animGrna ? grnas.findIndex(g => g.pos === animGrna.pos) : -1
  const activePhaseI = PHASES.indexOf(phase)
  const bottomShift  = animMode ? 60 : 12

  const panelStyle = {
    background: 'rgba(2,10,6,0.88)',
    border: '1px solid rgba(0,255,136,0.2)',
    borderRadius: 8,
    backdropFilter: 'blur(12px)',
  }

  const overlayBtn = (active = false, disabled = false) => ({
    padding: '4px 10px', borderRadius: 4, fontSize: 11,
    cursor: disabled ? 'default' : 'pointer',
    background: active ? '#00aa55' : 'rgba(0,40,20,0.8)',
    border: `1px solid rgba(0,255,136,${active ? '0.4' : '0.2'})`,
    color: active ? '#020a06' : disabled ? '#1a4a2a' : '#00ff88',
    opacity: disabled ? 0.5 : 1, fontWeight: active ? 600 : 400,
    transition: 'background 0.15s',
    boxShadow: active ? '0 0 12px rgba(0,255,136,0.3)' : 'none',
  })

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ position: 'relative', width: '100%', height: 500, background: '#020a06', borderRadius: 6, overflow: 'hidden' }}>
      <style>{`@keyframes bpBlink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* Outcome labels — visible during repair/complete phases */}
      {outcomeLabels && (phase === 'repair' || phase === 'complete') && (
        <div style={{
          position:  'absolute',
          top:       54,
          right:     12,
          display:   'flex',
          flexDirection: 'column',
          gap:       5,
          animation: 'bpBlink 0.4s',
        }}>
          <div style={{ fontSize: 9, color: '#1a4a2a', fontFamily: 'monospace', letterSpacing: '1px', marginBottom: 2 }}>
            // TOP OUTCOMES
          </div>
          {outcomeLabels.map((l, i) => (
            <div key={i} style={{
              fontFamily:   'monospace',
              fontSize:     11,
              fontWeight:   700,
              color:        l.color,
              background:   'rgba(2,10,6,0.9)',
              border:       `1px solid ${l.color}44`,
              borderRadius: 4,
              padding:      '3px 8px',
              whiteSpace:   'nowrap',
              boxShadow:    `0 0 8px ${l.color}22`,
            }}>
              {l.label}
            </div>
          ))}
        </div>
      )}

      {/* Top-left: render mode + animation controls */}
      <div style={{ position: 'absolute', top: 10, left: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {['full', 'backbone', 'bases'].map(mode => (
            <button key={mode} onClick={() => setRenderMode(mode)} style={overlayBtn(renderMode === mode)}>{mode}</button>
          ))}
        </div>

        <button
          onClick={handleAnimModeToggle}
          style={{
            padding: '4px 10px', borderRadius: 4, fontSize: 11, cursor: 'pointer',
            fontWeight: animMode ? 600 : 400,
            background: animMode ? '#00aa55' : 'rgba(0,40,20,0.8)',
            border: `1px solid rgba(0,255,136,${animMode ? '0.4' : '0.2'})`,
            color: animMode ? '#020a06' : '#00ff88',
            boxShadow: animMode ? '0 0 12px rgba(0,255,136,0.3)' : 'none',
            transition: 'all 0.15s',
          }}
        >
          ⚡ Animation mode
        </button>

        {animMode && grnas.length > 0 && (
          <select
            value={animGrnaIdx >= 0 ? animGrnaIdx : 0}
            onChange={handleAnimGrnaChange}
            style={{
              background: 'rgba(0,20,10,0.9)',
              border: '1px solid rgba(0,255,136,0.2)',
              color: '#00ff88', fontSize: 11, borderRadius: 4,
              padding: '4px 6px', cursor: 'pointer', outline: 'none',
            }}
          >
            {grnas.slice(0, 20).map((g, i) => (
              <option key={i} value={i}>{`pos ${g.pos} | ${(g.guide || '').substring(0, 8)}... | ${(g.score ?? 0).toFixed(3)}`}</option>
            ))}
          </select>
        )}

        {animMode && animGrna && !playing && phase === 'idle' && (
          <button
            onClick={handleStartAnimation}
            style={{
              padding: '5px 10px', borderRadius: 6, fontSize: 11, cursor: 'pointer',
              fontWeight: 600, background: '#ffaa00', border: 'none', color: '#020a06',
              boxShadow: '0 0 12px rgba(255,170,0,0.3)',
            }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.85' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
          >
            ▶ Full animation →
          </button>
        )}
      </div>

      {/* Top-right: Cas9 legend (anim mode) or gRNA list (normal) */}
      {animMode ? (
        <div style={{ position: 'absolute', top: 10, right: 10, ...panelStyle, padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 5, minWidth: 150 }}>
          <div style={{ fontSize: 9, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 2 }}>Cas9 domains</div>
          {[
            { color: '#112255', label: 'Recognition lobe' },
            { color: '#ff2244', label: 'HNH (cuts −strand)' },
            { color: '#ffaa00', label: 'RuvC (cuts +strand)' },
            { color: '#00e5a0', label: 'gRNA (A)' },
            { color: '#ffaa00', label: 'gRNA (T)' },
            { color: '#aa88ff', label: 'gRNA (G)' },
            { color: '#ff6688', label: 'gRNA (C)' },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0, display: 'block', boxShadow: `0 0 4px ${color}` }} />
              <span style={{ fontSize: 10, color: '#4caf7d' }}>{label}</span>
            </div>
          ))}
          {animGrna && (
            <div style={{ marginTop: 4, paddingTop: 6, borderTop: '0.5px solid rgba(0,255,136,0.15)' }}>
              <div style={{ fontSize: 9, color: '#1a4a2a', marginBottom: 3 }}>Selected guide</div>
              <div style={{ fontFamily: 'monospace', fontSize: 10, color: '#00ff88', wordBreak: 'break-all' }}>
                {(animGrna.guide || '').slice(0, 20)}<span style={{ color: '#ffaa00' }}>{(animGrna.guide || '').slice(20)}</span>
              </div>
              <div style={{ fontSize: 10, color: '#1a4a2a', marginTop: 2 }}>bp {animGrna.pos}</div>
            </div>
          )}
        </div>
      ) : grnas.length > 0 ? (
        <div style={{ position: 'absolute', top: 10, right: 10, ...panelStyle, padding: '6px 10px', display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 180, overflowY: 'auto' }}>
          <div style={{ fontSize: 9, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 2 }}>gRNAs</div>
          {grnas.slice(0, 10).map((g, i) => (
            <div key={i} onClick={() => syncBpOffset(Math.max(0, g.pos - 5))} style={{ fontSize: 11, cursor: 'pointer', fontFamily: 'monospace', color: selectedGrna?.pos === g.pos ? '#ffaa00' : '#4caf7d' }}>
              {i + 1}. bp {g.pos}
            </div>
          ))}
        </div>
      ) : null}

      {/* Animation control bar */}
      {animMode && (
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          background: 'rgba(2,10,6,0.92)',
          borderTop: '1px solid rgba(0,255,136,0.15)',
          padding: '10px 16px',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={handlePlayAnim}
              disabled={!animGrna || phase === 'complete'}
              style={{
                padding: '5px 14px', borderRadius: 6, fontSize: 12,
                cursor: animGrna && phase !== 'complete' ? 'pointer' : 'not-allowed',
                background: !playing ? '#00aa55' : 'rgba(0,40,20,0.8)',
                color: !playing ? '#020a06' : '#00ff88',
                border: !playing ? 'none' : '1px solid rgba(0,255,136,0.3)',
                boxShadow: !playing ? '0 0 12px rgba(0,255,136,0.3)' : 'none',
                fontWeight: 600, opacity: !animGrna ? 0.5 : 1,
              }}
            >
              ▶ Play
            </button>
            <button
              onClick={handlePauseAnim}
              disabled={phase === 'idle' || phase === 'complete'}
              style={{
                padding: '5px 12px', borderRadius: 6, fontSize: 12,
                cursor: phase !== 'idle' && phase !== 'complete' ? 'pointer' : 'not-allowed',
                background: 'rgba(0,40,20,0.8)', color: '#00ff88',
                border: '1px solid rgba(0,255,136,0.3)',
                opacity: phase === 'idle' || phase === 'complete' ? 0.4 : 1,
              }}
            >
              {playing ? '⏸ Pause' : '▶ Resume'}
            </button>
            <button
              onClick={handleResetAnim}
              style={{
                padding: '5px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                background: 'rgba(0,40,20,0.8)', color: '#00ff88',
                border: '1px solid rgba(0,255,136,0.3)',
              }}
            >
              ⏮ Reset
            </button>
          </div>

          {/* Phase dots */}
          <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
            {PHASES.slice(1).map((ph, k) => {
              const idx     = k + 1
              const done    = activePhaseI > idx
              const current = activePhaseI === idx
              return (
                <div
                  key={ph}
                  title={ph}
                  style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: current ? '#00ff88' : done ? '#00aa55' : '#0a2a14',
                    boxShadow: current ? '0 0 8px #00ff88' : 'none',
                    transition: 'all 0.3s',
                  }}
                />
              )
            })}
          </div>

          {/* Status text */}
          <div style={{
            fontSize: 12,
            color: phase === 'cleaving' ? '#ff4488' : '#00ff88',
            fontFamily: 'monospace',
            flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {STATUS_TEXT[phase]}
            <span style={{ animation: 'bpBlink 1s step-end infinite', marginLeft: 2 }}>█</span>
          </div>
        </div>
      )}

      {/* bp navigator */}
      {seqLen > 0 && (
        <div style={{ position: 'absolute', bottom: bottomShift, left: '50%', transform: 'translateX(-50%)', display: 'flex', alignItems: 'center', gap: 6, ...panelStyle, padding: '4px 8px' }}>
          <button disabled={!canPrev} onClick={() => canPrev && syncBpOffset(Math.max(0, bpOffset - BP_COUNT))} style={overlayBtn(false, !canPrev)}>←</button>
          <span style={{ fontSize: 11, color: '#4caf7d', fontFamily: 'monospace', padding: '0 6px' }}>bp {bpOffset + 1}–{bpEnd} / {seqLen}</span>
          <button disabled={!canNext} onClick={() => canNext && syncBpOffset(Math.min(seqLen - BP_COUNT, bpOffset + BP_COUNT))} style={overlayBtn(false, !canNext)}>→</button>
        </div>
      )}

      {/* Reset + Screenshot */}
      <div style={{ position: 'absolute', bottom: bottomShift, right: 12, display: 'flex', gap: 6 }}>
        <button onClick={handleReset} style={overlayBtn()}>Reset</button>
        <button onClick={handleScreenshot} style={overlayBtn()}>Screenshot</button>
      </div>

      {/* Base legend */}
      {seqLen > 0 && (
        <div style={{ position: 'absolute', bottom: bottomShift, left: 10, ...panelStyle, padding: '5px 10px', display: 'flex', gap: 10 }}>
          {[['A','#00ff88'],['T','#ffaa00'],['G','#cc88ff'],['C','#ff4488']].map(([b, c]) => (
            <div key={b} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10 }}>
              <span style={{ width: 7, height: 7, borderRadius: 2, background: c, display: 'inline-block', boxShadow: `0 0 4px ${c}` }} />
              <span style={{ color: '#4caf7d', fontFamily: 'monospace' }}>{b}</span>
            </div>
          ))}
        </div>
      )}

      {!seqLen && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1a4a2a', fontSize: 13, pointerEvents: 'none' }}>
          Paste a sequence and run analysis to view the 3D helix
        </div>
      )}
    </div>
  )
}
