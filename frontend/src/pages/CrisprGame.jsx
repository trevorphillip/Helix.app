import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useHelixStore } from '../store.jsx'

// ─── constants ────────────────────────────────────────────────────────────────

const HELIX_RADIUS      = 2.2
const RISE_PER_BP       = 0.34
const TURN_PER_BP       = (2 * Math.PI) / 10
const BP_WINDOW         = 60

const BASE_COLOR        = { A: 0x00ff88, T: 0xffaa00, G: 0xcc88ff, C: 0xff4488 }
const BASE_EMISSIVE     = { A: 0x00cc66, T: 0xff8800, G: 0xaa66ff, C: 0xdd2266 }
const BASE_EMISSIVE_INT = { A: 0.5,      T: 0.5,      G: 0.4,      C: 0.4      }
const COMPLEMENT        = { A: 'T', T: 'A', G: 'C', C: 'G' }

const RISK_BG    = { low: '#085041', med: '#633806', high: '#6B1D1D' }
const RISK_COLOR = { low: '#5DCAA5', med: '#FAC775', high: '#F09595' }

// ─── helpers ──────────────────────────────────────────────────────────────────

function helixPt(i, off = 0) {
  const a = i * TURN_PER_BP + off
  return new THREE.Vector3(HELIX_RADIUS * Math.cos(a), i * RISE_PER_BP, HELIX_RADIUS * Math.sin(a))
}

function disposeObj(obj) {
  obj.traverse(o => {
    o.geometry?.dispose()
    if (Array.isArray(o.material)) o.material.forEach(m => m.dispose())
    else o.material?.dispose()
  })
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3) }

// ─── helix builder ────────────────────────────────────────────────────────────

function buildGameHelix(seq) {
  const group = new THREE.Group()
  const n = seq.length
  if (!n) return group

  const bkMats = [
    new THREE.MeshPhysicalMaterial({ color: 0x004422, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.4, metalness: 0.2, roughness: 0.6, transmission: 0.3, thickness: 0.5, transparent: true, opacity: 0.95 }),
    new THREE.MeshPhysicalMaterial({ color: 0x003318, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.4, metalness: 0.2, roughness: 0.6, transmission: 0.3, thickness: 0.5, transparent: true, opacity: 0.95 }),
  ]
  for (let mi = 0; mi < 2; mi++) {
    const pts = Array.from({ length: n + 1 }, (_, i) => helixPt(i, mi === 0 ? 0 : Math.PI))
    group.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), n * 6, 0.12, 8, false), bkMats[mi]))
  }

  const yAxis = new THREE.Vector3(0, 1, 0)
  for (let i = 0; i < n; i++) {
    const base = (seq[i] || 'A').toUpperCase()
    const comp = COMPLEMENT[base] || 'T'
    const p1   = helixPt(i, 0)
    const p2   = helixPt(i, Math.PI)

    for (const [p, b] of [[p1, base], [p2, comp]]) {
      const col = BASE_COLOR[b] ?? 0x00ff88
      const s   = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 8, 8),
        new THREE.MeshPhysicalMaterial({ color: col, emissive: new THREE.Color(BASE_EMISSIVE[b] ?? 0x008844), emissiveIntensity: BASE_EMISSIVE_INT[b] ?? 0.4, metalness: 0.1, roughness: 0.2, transmission: 0.4, thickness: 1.0, transparent: true, opacity: 0.9 }),
      )
      s.position.copy(p)
      s.userData.bpIndex = i
      group.add(s)
      const glow = new THREE.Mesh(new THREE.SphereGeometry(0.32, 6, 6), new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.07 }))
      glow.position.copy(p)
      group.add(glow)
    }

    const mid = p1.clone().add(p2).multiplyScalar(0.5)
    const dir = p2.clone().sub(p1)
    const cyl = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, dir.length(), 6),
      new THREE.MeshPhysicalMaterial({ color: 0x004433, metalness: 0.4, roughness: 0.5, transparent: true, opacity: 0.25 }))
    cyl.position.copy(mid)
    cyl.quaternion.setFromUnitVectors(yAxis, dir.normalize())
    group.add(cyl)
  }

  return group
}

// ─── Cas9 builder ─────────────────────────────────────────────────────────────

function buildCas9() {
  const g = new THREE.Group()
  const lobeMat = () => new THREE.MeshPhysicalMaterial({ color: 0x112255, emissive: new THREE.Color(0x081830), emissiveIntensity: 0.4, metalness: 0.7, roughness: 0.15 })
  const wireMat = () => new THREE.LineBasicMaterial({ color: 0x2244aa, transparent: true, opacity: 0.4 })

  const l1 = new THREE.Mesh(new THREE.BoxGeometry(2.5, 1.8, 1.8, 2, 2, 2), lobeMat())
  l1.add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2.5, 1.8, 1.8)), wireMat()))
  g.add(l1)

  const l2 = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.6, 1.6, 2, 2, 2), lobeMat())
  l2.position.set(-2.2, 0, 0)
  l2.add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2.0, 1.6, 1.6)), wireMat()))
  g.add(l2)

  const hnh = new THREE.Mesh(new THREE.SphereGeometry(0.35, 12, 12), new THREE.MeshPhysicalMaterial({ color: 0xff2244, emissive: new THREE.Color(0xff0000), emissiveIntensity: 0.8, metalness: 0.9, roughness: 0.05 }))
  hnh.position.set(-1.7, -0.9, 0.8)
  g.add(hnh)
  const hnhG = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 8), new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.15 }))
  hnhG.scale.setScalar(2); hnhG.position.copy(hnh.position); g.add(hnhG)

  const ruvc = new THREE.Mesh(new THREE.SphereGeometry(0.35, 12, 12), new THREE.MeshPhysicalMaterial({ color: 0xffaa00, emissive: new THREE.Color(0xff8800), emissiveIntensity: 0.7, metalness: 0.9, roughness: 0.05 }))
  ruvc.position.set(-1.7, 0.9, 0.8)
  g.add(ruvc)
  const ruvcG = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 8), new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.12 }))
  ruvcG.scale.setScalar(2); ruvcG.position.copy(ruvc.position); g.add(ruvcG)

  return g
}

// ─── hit marker ───────────────────────────────────────────────────────────────

function addHitMarker(group) {
  const mat = new THREE.LineBasicMaterial({ color: 0xff4444 })
  const mk = (a, b) => new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), mat.clone())
  group.add(mk(new THREE.Vector3(-0.55, -0.55, 0), new THREE.Vector3(0.55, 0.55, 0)))
  group.add(mk(new THREE.Vector3(0.55, -0.55, 0), new THREE.Vector3(-0.55, 0.55, 0)))
  group.add(new THREE.Mesh(
    new THREE.TorusGeometry(0.45, 0.04, 6, 24),
    new THREE.MeshBasicMaterial({ color: 0xffaa00, transparent: true, opacity: 0.7 }),
  ))
}

// ─── ring color by score ──────────────────────────────────────────────────────

function ringColor(score) {
  if (score >= 0.8) return { color: 0x00ff88, emissive: 0x00cc66, emissiveIntensity: 0.6 }
  if (score >= 0.6) return { color: 0xffaa00, emissive: 0xff8800, emissiveIntensity: 0.5 }
  return               { color: 0xff4444, emissive: 0xdd2222, emissiveIntensity: 0.4 }
}

// ─── component ────────────────────────────────────────────────────────────────

export default function CrisprGame() {
  const { sequence, grnas } = useHelixStore()
  const navigate = useNavigate()

  const mountRef      = useRef(null)
  const rendererRef   = useRef(null)
  const sceneRef      = useRef(null)
  const cameraRef     = useRef(null)
  const controlsRef   = useRef(null)
  const rafRef        = useRef(null)
  const helixRef      = useRef(null)
  const ringGroupsRef = useRef([])   // [{ group, grna }]
  const hitMeshesRef  = useRef([])   // flat array for raycasting (hit zones)
  const cas9Ref       = useRef(null)
  const aimLineRef    = useRef(null)
  const flashPRef     = useRef([])
  const cutPRef       = useRef([])
  const ambPRef       = useRef([])
  const firingRef     = useRef(false)
  const hoveredRef    = useRef(null) // { group, grna }
  const hitSetRef     = useRef(new Set())
  const bpOffsetRef   = useRef(0)
  const shakeCamRef   = useRef({ active: false, until: 0 })
  const timersRef     = useRef([])

  const seq    = (sequence || '').replace(/[^ACGTacgt]/gi, '').toUpperCase()
  const seqLen = seq.length

  const [bpOffset,     setBpOffset]     = useState(0)
  const [totalCuts,    setTotalCuts]    = useState(0)
  const [totalXP,      setTotalXP]      = useState(0)
  const [critHits,     setCritHits]     = useState(0)
  const [gamePhase,    setGamePhase]    = useState('idle')
  const [tooltip,      setTooltip]      = useState(null)
  const [hovering,     setHovering]     = useState(false)
  const [resultPanel,  setResultPanel]  = useState(null)
  const [cutLog,       setCutLog]       = useState([])
  const [flashBorder,  setFlashBorder]  = useState(false)
  const [showInst,     setShowInst]     = useState(true)

  const slice        = seq.slice(bpOffset, bpOffset + BP_WINDOW)
  const canPrev      = bpOffset > 0
  const canNext      = bpOffset + BP_WINDOW < seqLen

  function syncBpOffset(v) { bpOffsetRef.current = v; setBpOffset(v) }

  function addTimer(fn, ms) {
    const id = setTimeout(fn, ms)
    timersRef.current.push(id)
    return id
  }

  useEffect(() => {
    const t = setTimeout(() => setShowInst(false), 5000)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    return () => { timersRef.current.forEach(clearTimeout) }
  }, [])

  // ── game complete ────────────────────────────────────────────────────────
  useEffect(() => {
    if (grnas.length > 0 && totalCuts >= grnas.length) {
      addTimer(() => setGamePhase('complete'), 600)
    }
  }, [totalCuts, grnas.length])

  // ── one-time setup ────────────────────────────────────────────────────────
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    const w = mount.clientWidth  || window.innerWidth
    const h = mount.clientHeight || (window.innerHeight - 48)

    // hoisted so cleanup can always reach them even if setup throws
    let renderer, controls, ro

    try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(w, h)
    renderer.shadowMap.enabled    = true
    renderer.shadowMap.type       = THREE.PCFSoftShadowMap
    renderer.toneMapping          = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure  = 1.4
    renderer.outputColorSpace     = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x020a06)
    scene.fog        = new THREE.FogExp2(0x020a06, 0.012)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 1000)
    camera.position.set(0, 4, 20)
    cameraRef.current = camera

    scene.add(new THREE.AmbientLight(0x0a1a0a, 0.5))
    const kl = new THREE.PointLight(0x00ff88, 4.0, 80, 2)
    kl.position.set(-8, 12, 8); kl.castShadow = true; scene.add(kl)
    const fl = new THREE.PointLight(0xffaa00, 2.0, 60, 2)
    fl.position.set(10, -6, 10); scene.add(fl)
    const rl = new THREE.PointLight(0x00aa44, 3.0, 80, 2)
    rl.position.set(-12, 0, -8); scene.add(rl)

    // floor
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60),
      new THREE.MeshPhysicalMaterial({ color: 0x001a0a, emissive: new THREE.Color(0x002211), emissiveIntensity: 0.3, metalness: 0.1, roughness: 0.8 }))
    floor.rotation.x = -Math.PI / 2; floor.position.y = -4; floor.receiveShadow = true; scene.add(floor)

    // background tori
    for (let i = 0; i < 5; i++) {
      const t = new THREE.Mesh(new THREE.TorusGeometry(Math.random() * 3 + 2, 0.08, 8, 40),
        new THREE.MeshBasicMaterial({ color: 0x003322, transparent: true, opacity: 0.12 }))
      t.position.set((Math.random() - 0.5) * 30, (Math.random() - 0.5) * 15, -(Math.random() * 10 + 15))
      t.userData.dir = Math.random() > 0.5 ? 1 : -1
      scene.add(t)
    }

    // ambient particles
    const amb = []
    const pCols = [0x004422, 0x002211, 0x113300]
    for (let i = 0; i < 150; i++) {
      const p = new THREE.Mesh(new THREE.SphereGeometry(Math.random() * 0.07 + 0.02, 5, 5),
        new THREE.MeshBasicMaterial({ color: pCols[i % 3], transparent: true, opacity: Math.random() * 0.3 + 0.2 }))
      const phi = Math.random() * Math.PI * 2, theta = Math.acos(2 * Math.random() - 1), r = 20 * Math.cbrt(Math.random())
      p.position.set(r * Math.sin(theta) * Math.cos(phi), r * Math.sin(theta) * Math.sin(phi), r * Math.cos(theta))
      p.userData = { speed: Math.random() * 0.3 + 0.1, offset: Math.random() * Math.PI * 2 }
      scene.add(p); amb.push(p)
    }
    ambPRef.current = amb

    controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 4, 0)
    controls.enableDamping = true; controls.dampingFactor = 0.05
    controls.minDistance = 8; controls.maxDistance = 35; controls.autoRotate = false
    controls.update()
    controlsRef.current = controls

    function animate() {
      rafRef.current = requestAnimationFrame(animate)
      controls.update()
      const now = Date.now(), time = now / 1000

      // ambient drift
      ambPRef.current.forEach(p => {
        const { speed, offset } = p.userData
        p.position.x += Math.sin(time * speed + offset) * 0.002
        p.position.y += Math.cos(time * speed + offset) * 0.002
        p.position.z += Math.sin(time * speed * 0.7 + offset) * 0.001
      })

      // ring pulse + spin
      ringGroupsRef.current.forEach(({ group, grna }) => {
        if (group.userData.hit) return
        if (group.userData.exploding) {
          const t = Math.min((now - group.userData.explodeStart) / 300, 1)
          group.children.forEach(c => {
            if (c.isMesh && c.material?.opacity !== undefined) {
              c.scale.setScalar(1 + t * 2)
              c.material.opacity = Math.max(0, 1 - t)
            }
          })
          if (t >= 1) { group.visible = false; group.userData.exploding = false }
          return
        }
        const isHov = hoveredRef.current?.grna === grna
        group.scale.setScalar(isHov ? 1.3 : 1 + 0.1 * Math.sin(time * 2 + grna.pos * 0.1))
        group.children.forEach(c => { if (c.isMesh && !c.userData.isHitZone) c.rotation.z += 0.02 })
      })

      // flash particles
      flashPRef.current = flashPRef.current.filter(p => {
        p.position.x += p.userData.vx; p.position.y += p.userData.vy; p.position.z += p.userData.vz
        p.material.opacity -= 0.04
        if (p.material.opacity <= 0) { scene.remove(p); p.geometry.dispose(); p.material.dispose(); return false }
        return true
      })

      // cut particles
      cutPRef.current = cutPRef.current.filter(p => {
        p.position.x += p.userData.vx; p.position.y += p.userData.vy; p.position.z += p.userData.vz
        p.material.opacity -= 0.02
        if (p.material.opacity <= 0) { scene.remove(p); p.geometry.dispose(); p.material.dispose(); return false }
        return true
      })

      // camera shake
      if (shakeCamRef.current.active) {
        if (now < shakeCamRef.current.until) {
          camera.position.x += (Math.random() - 0.5) * 0.1
          camera.position.y += (Math.random() - 0.5) * 0.1
        } else { shakeCamRef.current.active = false }
      }

      // Cas9 scale-in
      if (cas9Ref.current?.userData.scalingIn) {
        const t = Math.min((now - cas9Ref.current.userData.scaleStart) / 500, 1)
        cas9Ref.current.scale.setScalar(easeOut(t))
        if (t >= 1) cas9Ref.current.userData.scalingIn = false
      }

      renderer.render(scene, camera)
    }
    animate()

    ro = new ResizeObserver(() => {
      const nw = mount.clientWidth, nh = mount.clientHeight || window.innerHeight - 48
      camera.aspect = nw / nh; camera.updateProjectionMatrix(); renderer.setSize(nw, nh)
    })
    ro.observe(mount)

    } catch (err) {
      console.error('Scene setup error:', err)
    }

    return () => {
      cancelAnimationFrame(rafRef.current)
      ro?.disconnect()
      controls?.dispose()
      ambPRef.current.forEach(p => { p.geometry.dispose(); p.material.dispose() })
      if (renderer) {
        renderer.dispose()
        if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
      }
    }
  }, [])

  // ── rebuild helix ─────────────────────────────────────────────────────────
  useEffect(() => {
    const scene = sceneRef.current; if (!scene) return
    if (helixRef.current) { scene.remove(helixRef.current); disposeObj(helixRef.current) }
    const g = buildGameHelix(slice); scene.add(g); helixRef.current = g
    if (controlsRef.current) {
      controlsRef.current.target.set(0, (slice.length * RISE_PER_BP) / 2, 0)
    }
  }, [slice])

  // ── rebuild rings ─────────────────────────────────────────────────────────
  useEffect(() => {
    const scene = sceneRef.current; if (!scene) return

    ringGroupsRef.current.forEach(({ group }) => { scene.remove(group); disposeObj(group) })
    ringGroupsRef.current = []
    hitMeshesRef.current  = []

    const offset = bpOffsetRef.current
    const sliceLen = seq.slice(offset, offset + BP_WINDOW).length

    grnas.forEach(grna => {
      const localBp = grna.pos + 17 - offset
      if (localBp < 0 || localBp >= sliceLen) return

      const angle   = localBp * TURN_PER_BP
      const outward = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle))
      const pos     = helixPt(localBp, 0).addScaledVector(outward, 0.5)

      const group = new THREE.Group()
      group.position.copy(pos)
      group.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), outward)
      group.userData.grna = grna
      group.userData.hit  = hitSetRef.current.has(grna.pos)

      if (group.userData.hit) {
        addHitMarker(group)
      } else {
        const rc  = ringColor(grna.score)
        const mat = new THREE.MeshPhysicalMaterial({ color: rc.color, emissive: new THREE.Color(rc.emissive), emissiveIntensity: rc.emissiveIntensity, metalness: 0.3, roughness: 0.3, transparent: true, opacity: 0.9, side: THREE.DoubleSide })
        const ringMesh = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.1, 8, 32), mat)
        group.add(ringMesh)

        // invisible wider hit zone for reliable clicking
        const hz = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.3, 6, 16),
          new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, side: THREE.DoubleSide }))
        hz.userData.isHitZone  = true
        hz.userData.ringGroup  = group
        group.add(hz)
        hitMeshesRef.current.push(hz)
      }

      scene.add(group)
      ringGroupsRef.current.push({ group, grna })
    })
  }, [grnas, bpOffset])

  // ── particle helpers ──────────────────────────────────────────────────────
  function spawnParticles(pos, count, col1, col2, speed) {
    const scene = sceneRef.current; if (!scene) return []
    const arr = []
    for (let i = 0; i < count; i++) {
      const p = new THREE.Mesh(new THREE.SphereGeometry(0.07, 5, 5),
        new THREE.MeshBasicMaterial({ color: Math.random() > 0.5 ? col1 : col2, transparent: true, opacity: 1 }))
      p.position.copy(pos)
      p.userData.vx = (Math.random() - 0.5) * speed
      p.userData.vy = (Math.random() - 0.5) * speed
      p.userData.vz = (Math.random() - 0.5) * speed
      scene.add(p); arr.push(p)
    }
    return arr
  }

  // ── fire sequence ─────────────────────────────────────────────────────────
  function fireCas9(group, grna) {
    if (firingRef.current || group.userData.hit) return
    firingRef.current = true
    setGamePhase('firing')

    const worldPos = group.getWorldPosition(new THREE.Vector3())
    const _bpOffset = bpOffsetRef.current

    // step 1 — flash + ring explode
    setFlashBorder(true)
    addTimer(() => setFlashBorder(false), 300)
    group.userData.exploding   = true
    group.userData.explodeStart = Date.now()
    flashPRef.current.push(...spawnParticles(worldPos, 20, 0x00ff88, 0x00ffaa, 0.2))

    // step 2 — Cas9 materializes (300ms)
    addTimer(() => {
      const scene = sceneRef.current; if (!scene) return
      if (cas9Ref.current) { scene.remove(cas9Ref.current); disposeObj(cas9Ref.current) }
      const c9 = buildCas9()
      c9.position.set(worldPos.x + 3.5, worldPos.y, worldPos.z)
      c9.userData.scalingIn  = true
      c9.userData.scaleStart = Date.now()
      c9.scale.setScalar(0)
      scene.add(c9); cas9Ref.current = c9
    }, 300)

    // step 3 — cut fx (800ms)
    addTimer(() => {
      cutPRef.current.push(...spawnParticles(worldPos, 50, 0xff2244, 0xff8800, 0.15))
      shakeCamRef.current = { active: true, until: Date.now() + 600 }
      // flash bases
      const helix = helixRef.current; if (!helix) return
      const cutBp = grna.pos + 17 - _bpOffset
      helix.traverse(obj => {
        if (obj.userData.bpIndex === cutBp && obj.material?.color) {
          obj.material.color.setHex(0xff2244)
          if (obj.material.emissive) { obj.material.emissive.setHex(0xff0000); obj.material.emissiveIntensity = 1.0 }
        }
      })
      // red cut plane
      const plane = new THREE.Mesh(new THREE.CircleGeometry(HELIX_RADIUS + 1.2, 32),
        new THREE.MeshBasicMaterial({ color: 0xff2244, transparent: true, opacity: 0.3, side: THREE.DoubleSide }))
      plane.position.set(0, cutBp * RISE_PER_BP, 0); plane.rotation.x = Math.PI / 2
      helix.add(plane)
    }, 800)

    // step 4 — mark cut + result (1800ms)
    addTimer(() => {
      // mark base amber
      const helix = helixRef.current; if (helix) {
        const cutBp = grna.pos + 17 - _bpOffset
        helix.traverse(obj => {
          if (obj.userData.bpIndex === cutBp && obj.material?.color) {
            obj.material.color.setHex(0xffaa00)
            if (obj.material.emissive) { obj.material.emissive.setHex(0xff8800); obj.material.emissiveIntensity = 0.5 }
          }
        })
      }
      // convert ring to hit marker
      group.userData.hit = true
      hitSetRef.current.add(grna.pos)
      while (group.children.length) {
        const c = group.children[0]; group.remove(c); c.geometry?.dispose()
        if (Array.isArray(c.material)) c.material.forEach(m => m.dispose()); else c.material?.dispose()
      }
      addHitMarker(group)
      group.visible = true; group.scale.setScalar(1)

      const xp = Math.floor(grna.score * 100)
      setTotalCuts(prev => prev + 1)
      setTotalXP(prev => prev + xp)
      if (grna.score >= 0.8) setCritHits(prev => prev + 1)
      setCutLog(prev => [{ pos: grna.pos, score: grna.score, xp }, ...prev].slice(0, 5))
      setResultPanel({ grna, xp })
    }, 1800)

    // step 5 — cleanup (3800ms)
    addTimer(() => {
      setResultPanel(null)
      const scene = sceneRef.current
      if (scene && cas9Ref.current) { scene.remove(cas9Ref.current); disposeObj(cas9Ref.current); cas9Ref.current = null }
      firingRef.current = false
      setGamePhase('idle')
    }, 3800)
  }

  // ── mouse handlers ────────────────────────────────────────────────────────
  function handleMouseMove(e) {
    const renderer = rendererRef.current, camera = cameraRef.current, scene = sceneRef.current
    if (!renderer || !camera || !scene) return

    const rect = renderer.domElement.getBoundingClientRect()
    const mx   = ((e.clientX - rect.left) / rect.width)  * 2 - 1
    const my   = -((e.clientY - rect.top)  / rect.height) * 2 + 1

    if (aimLineRef.current) { scene.remove(aimLineRef.current); disposeObj(aimLineRef.current); aimLineRef.current = null }

    const ray = new THREE.Raycaster()
    ray.setFromCamera(new THREE.Vector2(mx, my), camera)
    const hits = ray.intersectObjects(hitMeshesRef.current, false)

    if (hits.length > 0) {
      const group = hits[0].object.userData.ringGroup
      if (group && !group.userData.hit) {
        hoveredRef.current = { group, grna: group.userData.grna }
        setHovering(true)
        setTooltip({ grna: group.userData.grna })

        const linePts = [camera.position.clone(), hits[0].point.clone()]
        const al = new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePts),
          new THREE.LineBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.3 }))
        scene.add(al); aimLineRef.current = al
        return
      }
    }

    hoveredRef.current = null
    setHovering(false)
    setTooltip(null)
  }

  function handleClick() {
    if (firingRef.current) return
    const h = hoveredRef.current
    if (!h || h.group.userData.hit) return
    fireCas9(h.group, h.grna)
  }

  // ── bp navigation ─────────────────────────────────────────────────────────
  function handlePrev() {
    const next = Math.max(0, bpOffset - BP_WINDOW)
    syncBpOffset(next)
    if (controlsRef.current) controlsRef.current.target.set(0, (Math.min(BP_WINDOW, seqLen - next) * RISE_PER_BP) / 2, 0)
  }
  function handleNext() {
    const next = Math.min(seqLen - BP_WINDOW, bpOffset + BP_WINDOW)
    syncBpOffset(next)
    if (controlsRef.current) controlsRef.current.target.set(0, (Math.min(BP_WINDOW, seqLen - next) * RISE_PER_BP) / 2, 0)
  }

  // ── styles ────────────────────────────────────────────────────────────────
  const panel = { background: 'rgba(2,10,6,0.88)', border: '1px solid rgba(0,255,136,0.2)', borderRadius: 8, backdropFilter: 'blur(12px)', padding: '10px 14px' }
  const mg    = { fontFamily: 'monospace', color: '#00ff88' }

  // ── empty state ───────────────────────────────────────────────────────────
  if (!seqLen || grnas.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 'calc(100vh - 48px)', background: '#020a06' }}>
        <div style={{ ...panel, textAlign: 'center', maxWidth: 340 }}>
          <div style={{ ...mg, fontSize: 16, fontWeight: 700, marginBottom: 8 }}>NO TARGETS LOADED</div>
          <div style={{ color: '#4caf7d', fontSize: 13, marginBottom: 16 }}>Run an analysis in Sandbox first to load targets</div>
          <button onClick={() => navigate('/')} style={{ background: '#00aa55', color: '#020a06', border: 'none', borderRadius: 6, padding: '8px 20px', fontWeight: 700, cursor: 'pointer', fontSize: 13, boxShadow: '0 0 12px rgba(0,255,136,0.3)' }}>
            Go to Sandbox →
          </button>
        </div>
      </div>
    )
  }

  const allCut = totalCuts >= grnas.length

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 48px)', background: '#020a06', overflow: 'hidden' }}>
      <style>{`
        @keyframes bpBlink  { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes slideUp  { from{transform:translateY(16px);opacity:0} to{transform:translateY(0);opacity:1} }
        @keyframes fadeInG  { from{opacity:0} to{opacity:1} }
        @keyframes instFade { 0%{opacity:1} 80%{opacity:1} 100%{opacity:0} }
      `}</style>

      {/* canvas */}
      <div ref={mountRef} style={{ width: '100%', height: '100%', cursor: hovering ? 'crosshair' : 'default' }}
        onMouseMove={handleMouseMove} onClick={handleClick} />

      {/* flash border */}
      {flashBorder && (
        <div style={{ position: 'absolute', inset: 0, border: '3px solid #00ff88', pointerEvents: 'none', boxShadow: 'inset 0 0 40px rgba(0,255,136,0.25)', animation: 'fadeInG 0.15s' }} />
      )}

      {/* TOP LEFT — stats */}
      <div style={{ position: 'absolute', top: 14, left: 14, ...panel, minWidth: 210 }}>
        <div style={{ ...mg, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', marginBottom: 8 }}>
          HELIX CRISPR INTERFACE v2.0
          <span style={{ animation: 'bpBlink 1s step-end infinite', marginLeft: 4 }}>█</span>
        </div>
        <div style={{ fontSize: 11, color: '#4caf7d', lineHeight: 1.7 }}>
          Sequence: <span style={mg}>{seq.substring(0, 12)}…</span><br />
          Targets: <span style={mg}>{grnas.length} PAM sites</span><br />
          Cuts made: <span style={{ fontFamily: 'monospace', color: totalCuts > 0 ? '#00ff88' : '#1a4a2a', fontWeight: 700 }}>{totalCuts} / {grnas.length}</span><br />
          Total XP: <span style={{ fontFamily: 'monospace', color: '#ffaa00', fontWeight: 700 }}>{totalXP}</span>
          {critHits > 0 && <><br /><span style={{ color: '#00ff88' }}>★ {critHits} critical hit{critHits > 1 ? 's' : ''}</span></>}
        </div>
      </div>

      {/* TOP CENTER — crosshair */}
      {hovering && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', pointerEvents: 'none' }}>
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <line x1="18" y1="4"  x2="18" y2="13" stroke="#00ff88" strokeWidth="1.5" strokeOpacity="0.75" />
            <line x1="18" y1="23" x2="18" y2="32" stroke="#00ff88" strokeWidth="1.5" strokeOpacity="0.75" />
            <line x1="4"  y1="18" x2="13" y2="18" stroke="#00ff88" strokeWidth="1.5" strokeOpacity="0.75" />
            <line x1="23" y1="18" x2="32" y2="18" stroke="#00ff88" strokeWidth="1.5" strokeOpacity="0.75" />
            <circle cx="18" cy="18" r="3.5" stroke="#00ff88" strokeWidth="1" fill="none" strokeOpacity="0.75" />
          </svg>
        </div>
      )}

      {/* TOP RIGHT — tooltip */}
      {tooltip && gamePhase !== 'firing' && (
        <div style={{ position: 'absolute', top: 14, right: 14, ...panel, minWidth: 230, animation: 'slideUp 0.2s' }}>
          <div style={{ ...mg, fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', marginBottom: 8 }}>TARGET ACQUIRED</div>
          <div style={{ fontSize: 10, color: '#1a4a2a', marginBottom: 3 }}>
            Guide: <span style={{ fontFamily: 'monospace', color: '#4caf7d', wordBreak: 'break-all' }}>{(tooltip.grna.guide || '').slice(0, 20)}</span>
          </div>
          <div style={{ fontSize: 11, color: '#4caf7d', marginBottom: 2 }}>
            Position: bp <span style={mg}>{tooltip.grna.pos}</span>
          </div>
          <div style={{ fontSize: 11, color: '#4caf7d', marginBottom: 8 }}>
            Efficiency:{' '}
            <span style={{ fontFamily: 'monospace', fontWeight: 700, color: tooltip.grna.score >= 0.8 ? '#00ff88' : tooltip.grna.score >= 0.6 ? '#ffaa00' : '#ff4444' }}>
              {(tooltip.grna.score * 100).toFixed(0)}%
            </span>
          </div>
          {tooltip.grna.risk && (
            <span style={{ background: RISK_BG[tooltip.grna.risk] ?? '#6B1D1D', color: RISK_COLOR[tooltip.grna.risk] ?? '#F09595', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>
              {tooltip.grna.risk} risk
            </span>
          )}
          <div style={{ marginTop: 8, fontSize: 10, color: '#1a4a2a' }}>+{Math.floor(tooltip.grna.score * 100)} XP on cut</div>
        </div>
      )}

      {/* CENTER — result panel */}
      {resultPanel && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', ...panel, textAlign: 'center', minWidth: 260, animation: 'fadeInG 0.3s', boxShadow: '0 0 50px rgba(0,255,136,0.15)' }}>
          <div style={{ fontSize: 24, fontFamily: 'monospace', fontWeight: 900, marginBottom: 8, color: resultPanel.grna.score >= 0.8 ? '#00ff88' : resultPanel.grna.score >= 0.6 ? '#ffaa00' : '#ff4444' }}>
            {resultPanel.grna.score >= 0.8 ? 'CRITICAL HIT' : resultPanel.grna.score >= 0.6 ? 'GOOD CUT' : 'LOW EFFICIENCY'}
          </div>
          <div style={{ fontSize: 14, color: '#4caf7d', marginBottom: 4 }}>
            Efficiency: {(resultPanel.grna.score * 100).toFixed(0)}%
          </div>
          <div style={{ fontSize: 20, fontFamily: 'monospace', color: '#ffaa00', fontWeight: 700, marginBottom: 10 }}>
            +{resultPanel.xp} XP
          </div>
          {resultPanel.grna.risk && (
            <span style={{ background: RISK_BG[resultPanel.grna.risk] ?? '#6B1D1D', color: RISK_COLOR[resultPanel.grna.risk] ?? '#F09595', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>
              {resultPanel.grna.risk} off-target risk
            </span>
          )}
        </div>
      )}

      {/* COMPLETE overlay */}
      {allCut && gamePhase === 'complete' && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(2,10,6,0.8)', backdropFilter: 'blur(10px)', animation: 'fadeInG 0.5s' }}>
          <div style={{ ...panel, textAlign: 'center', maxWidth: 360, boxShadow: '0 0 60px rgba(0,255,136,0.2)' }}>
            <div style={{ ...mg, fontSize: 28, fontWeight: 900, letterSpacing: '0.1em', marginBottom: 6 }}>SEQUENCE EDITED</div>
            <div style={{ color: '#4caf7d', fontSize: 13, marginBottom: 20 }}>All PAM sites targeted successfully</div>
            <div style={{ display: 'flex', gap: 24, justifyContent: 'center', marginBottom: 20 }}>
              <div>
                <div style={{ ...mg, fontSize: 32, fontWeight: 900 }}>{totalXP}</div>
                <div style={{ fontSize: 10, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: 1 }}>Total XP</div>
              </div>
              <div>
                <div style={{ fontFamily: 'monospace', color: '#ffaa00', fontSize: 32, fontWeight: 900 }}>{totalCuts}</div>
                <div style={{ fontSize: 10, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: 1 }}>Cuts Made</div>
              </div>
              <div>
                <div style={{ ...mg, fontSize: 32, fontWeight: 900 }}>{grnas.length > 0 ? (totalXP / grnas.length).toFixed(0) : 0}%</div>
                <div style={{ fontSize: 10, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: 1 }}>Avg Eff</div>
              </div>
            </div>
            <button onClick={() => navigate('/')} style={{ background: '#00aa55', color: '#020a06', border: 'none', borderRadius: 6, padding: '10px 28px', fontWeight: 700, cursor: 'pointer', fontSize: 14, boxShadow: '0 0 16px rgba(0,255,136,0.3)' }}>
              Return to Sandbox
            </button>
          </div>
        </div>
      )}

      {/* BOTTOM CENTER — instructions */}
      {showInst && (
        <div style={{ position: 'absolute', bottom: seqLen > BP_WINDOW ? 64 : 16, left: '50%', transform: 'translateX(-50%)', ...panel, fontSize: 12, color: '#4caf7d', whiteSpace: 'nowrap', animation: 'instFade 5s forwards' }}>
          HOVER to target PAM sites • CLICK to fire Cas9
        </div>
      )}

      {/* BOTTOM LEFT — bp navigation */}
      {seqLen > BP_WINDOW && (
        <div style={{ position: 'absolute', bottom: 14, left: 14, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button disabled={!canPrev} onClick={handlePrev}
            style={{ ...panel, padding: '6px 12px', fontSize: 11, cursor: canPrev ? 'pointer' : 'default', color: canPrev ? '#00ff88' : '#1a4a2a', border: `1px solid rgba(0,255,136,${canPrev ? '0.3' : '0.08'})` }}>
            ← Prev {BP_WINDOW}bp
          </button>
          <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#4caf7d', background: 'rgba(2,10,6,0.7)', padding: '5px 10px', borderRadius: 6, border: '1px solid rgba(0,255,136,0.1)' }}>
            bp {bpOffset + 1}–{Math.min(bpOffset + BP_WINDOW, seqLen)} / {seqLen}
          </span>
          <button disabled={!canNext} onClick={handleNext}
            style={{ ...panel, padding: '6px 12px', fontSize: 11, cursor: canNext ? 'pointer' : 'default', color: canNext ? '#00ff88' : '#1a4a2a', border: `1px solid rgba(0,255,136,${canNext ? '0.3' : '0.08'})` }}>
            Next {BP_WINDOW}bp →
          </button>
        </div>
      )}

      {/* BOTTOM RIGHT — cut log */}
      {cutLog.length > 0 && (
        <div style={{ position: 'absolute', bottom: 14, right: 14, ...panel, minWidth: 210 }}>
          <div style={{ fontSize: 10, color: '#1a4a2a', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>Cut Log</div>
          {cutLog.map((entry, i) => (
            <div key={`${entry.pos}-${i}`} style={{ fontSize: 11, fontFamily: 'monospace', color: i === 0 ? '#00ff88' : '#4caf7d', marginBottom: 2, animation: i === 0 ? 'slideUp 0.3s' : 'none' }}>
              bp {entry.pos} — {(entry.score * 100).toFixed(0)}% eff
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
