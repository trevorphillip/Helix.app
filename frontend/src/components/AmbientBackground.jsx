import { useEffect, useRef } from 'react'

const COLORS = ['#004422', '#002211', '#003318', '#001a0a', '#003322']

export default function AmbientBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const particles = Array.from({ length: 200 }, () => ({
      x:      Math.random() * window.innerWidth,
      y:      Math.random() * window.innerHeight,
      r:      Math.random() * 3 + 1,
      color:  COLORS[Math.floor(Math.random() * COLORS.length)],
      speed:  Math.random() * 0.3 + 0.05,
      phase:  Math.random() * Math.PI * 2,
      amp:    Math.random() * 40 + 10,
      baseX:  0,
      baseY:  0,
      pulsePhase: Math.random() * Math.PI * 2,
      pulseSpeed: Math.random() * 0.02 + 0.005,
    }))
    particles.forEach(p => { p.baseX = p.x; p.baseY = p.y })

    let raf
    let t = 0

    function draw() {
      raf = requestAnimationFrame(draw)
      t += 0.004
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      particles.forEach(p => {
        p.x = p.baseX + Math.sin(t * p.speed + p.phase) * p.amp
        p.y = p.baseY + Math.cos(t * p.speed * 0.7 + p.phase) * p.amp * 0.6

        p.pulsePhase += p.pulseSpeed
        const brightness = 0.4 + 0.3 * Math.sin(p.pulsePhase)

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = p.color
        ctx.globalAlpha = brightness
        ctx.fill()
      })
      ctx.globalAlpha = 1
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        zIndex: -1,
        pointerEvents: 'none',
      }}
    />
  )
}
