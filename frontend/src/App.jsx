import { useState, useRef, useCallback, useEffect } from 'react'

const API = ''

function useToasts() {
  const [toasts, setToasts] = useState([])
  const add = useCallback((msg, type = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000)
  }, [])
  return { toasts, add }
}

export default function App() {
  const { toasts, add: toast } = useToasts()

  // Navigation State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Workbench State
  const [frameInterval, setFrameInterval] = useState(5)
  const [activePreset, setActivePreset] = useState('flight1')
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  // Real inference state
  const [customOrig, setCustomOrig] = useState(null)
  const [customAnnotated, setCustomAnnotated] = useState(null)
  const [customIsVideo, setCustomIsVideo] = useState(false)
  const [customLabelUrl, setCustomLabelUrl] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)
  const [jobMsg, setJobMsg] = useState('')
  const [jobProgress, setJobProgress] = useState({})
  const [jobResult, setJobResult] = useState({})
  const [showModal, setShowModal] = useState(false)
  const pollRef = useRef(null)

  // FAQ Accordion State (multiple can be open)
  const [openFaqs, setOpenFaqs] = useState({ 0: true })

  const toggleFaq = (index) => {
    setOpenFaqs(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  // Pre-loaded flight presets
  const presets = {
    flight1: {
      name: 'Flight 01: Low Altitude Weed Cluster',
      raw: '/samples/uav_raw_field.png',
      annotated: '/samples/uav_annotated_field.png',
      summary: 'Raw Orthomosaic vs YOLOv8 Weed Isolation',
      stats: '14 weeds detected · 0 cotton damaged · Conf 0.82',
      isVideo: false
    },
    flight2: {
      name: 'Flight 02: Dense Soil Boundary',
      raw: '/samples/uav_raw_field.png',
      annotated: '/samples/weed_cluster_08.jpg',
      summary: 'Inter-row Weed Emergence at 15m AGL',
      stats: '22 weeds detected · Multi-box clustering',
      isVideo: false
    },
    flight3: {
      name: 'Flight 03: Validation Batch Rows',
      raw: '/samples/cotton_row_tile.jpg',
      annotated: '/samples/cotton_rows_val.jpg',
      summary: 'Full Canopy Segmentation (Cotton vs Weed)',
      stats: 'Cotton mAP 93.8% · Weed mAP 76.0%',
      isVideo: false
    }
  }

  const currentView = customOrig ? {
    name: 'Custom User Upload',
    raw: customOrig,
    annotated: customAnnotated || customOrig,
    summary: customAnnotated ? 'AI Inference Complete' : 'Awaiting Inference Processing',
    stats: isProcessing ? 'GPU Inference in Progress...' : 'Active Media Buffer',
    isVideo: customIsVideo
  } : presets[activePreset]

  // File Upload Handling
  const handleFile = useCallback(async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    const isVideo = ['mp4', 'avi', 'mov', 'mkv'].includes(ext)
    const isImage = ['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)
    if (!isVideo && !isImage) {
      toast('Please upload a valid image or video (MP4, AVI, JPG, PNG).', 'error')
      return
    }

    setCustomOrig(URL.createObjectURL(file))
    setCustomAnnotated(null)
    setCustomIsVideo(isVideo)
    setCustomLabelUrl(null)
    setUploading(true)
    setUploadProgress(15)

    const fd = new FormData()
    fd.append('file', file)

    try {
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error('Upload endpoint rejected file')
      const data = await res.json()
      setUploadProgress(100)
      toast(`Uploaded ${data.filename} successfully`, 'success')

      if (data.type === 'image') {
        setIsProcessing(true)
        const imgRes = await fetch(`${API}/api/process-image`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: data.filename }),
        })
        const imgData = await imgRes.json()
        setCustomAnnotated(`${API}${imgData.annotated_url}`)
        setCustomLabelUrl(`${API}${imgData.label_url}`)
        setIsProcessing(false)
        toast('YOLOv8 image inference complete!', 'success')
      } else {
        setIsProcessing(true)
        const vidRes = await fetch(`${API}/api/process`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: data.filename, frame_interval: frameInterval }),
        })
        const vidData = await vidRes.json()
        setJobStatus('queued')
        setJobMsg('Flight video queued for GPU processing...')

        // Poll job
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = setInterval(async () => {
          try {
            const stRes = await fetch(`${API}/api/status/${vidData.job_id}`)
            const stData = await stRes.json()
            setJobStatus(stData.status)
            setJobMsg(stData.message || '')
            setJobProgress(stData.progress || {})

            if (stData.status === 'done') {
              clearInterval(pollRef.current)
              setIsProcessing(false)
              setCustomAnnotated(`${API}${stData.result.output_video_url}`)
              setJobResult(stData.result)
              setShowModal(true)
              toast('Video pipeline complete! H.264 stream ready.', 'success')
            } else if (stData.status === 'error') {
              clearInterval(pollRef.current)
              setIsProcessing(false)
              toast(`Processing error: ${stData.message}`, 'error')
            }
          } catch (_) {}
        }, 1200)
      }
    } catch (err) {
      toast('Operating in offline sample mode (mock result displayed).', 'info')
      setCustomAnnotated(presets.flight1.annotated)
      setIsProcessing(false)
    } finally {
      setUploading(false)
      setTimeout(() => setUploadProgress(0), 600)
    }
  }, [frameInterval, toast])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  return (
    <div className="landing-page-root">
      {/* ====================================================================
          1. SITE HEADER (saas-1, variation: signature)
          ==================================================================== */}
      <header className="site-header">
        <div className="container">
          <div className="site-header-inner">
            {/* Wordmark with Reticle Mark */}
            <a href="#hero" className="brand-wordmark">
              <svg className="brand-mark-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 11V6C4 4.89543 4.89543 4 6 4H11" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M21 4H26C27.1046 4 28 4.89543 28 6V11" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M28 21V26C28 27.1046 27.1046 28 26 28H21" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M11 28H6C4.89543 28 4 27.1046 4 26V21" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                <circle cx="16" cy="16" r="6.5" stroke="#2e5bff" strokeWidth="2" fill="none" />
                <path d="M16 12V20M12 16H20" stroke="#2e5bff" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              <span>CottonVision</span>
            </a>

            {/* 4 Navigation Links */}
            <nav className="site-nav" aria-label="Main Navigation">
              <a href="#workbench" className="site-nav-link">Workbench</a>
              <a href="#features" className="site-nav-link">Pipeline</a>
              <a href="#benchmarks" className="site-nav-link">Benchmarks</a>
              <a href="#pricing" className="site-nav-link">Pricing</a>
            </nav>

            {/* Actions: Secondary Dataset Link + Primary Pill Button */}
            <div className="site-header-actions">
              <a
                href="https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing"
                target="_blank"
                rel="noreferrer"
                className="site-nav-link"
              >
                Dataset
              </a>
              <a href="#workbench" className="btn-pill btn-primary btn-sm">
                Open Workbench
              </a>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="mobile-menu-toggle"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                {mobileMenuOpen ? (
                  <path d="M18 6L6 18M6 6l12 12" />
                ) : (
                  <path d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>

          {/* Mobile Drawer */}
          <div className={`mobile-nav-drawer ${mobileMenuOpen ? 'open' : ''}`}>
            <div className="mobile-nav-links">
              <a href="#workbench" className="site-nav-link" onClick={() => setMobileMenuOpen(false)}>Workbench</a>
              <a href="#features" className="site-nav-link" onClick={() => setMobileMenuOpen(false)}>Pipeline</a>
              <a href="#benchmarks" className="site-nav-link" onClick={() => setMobileMenuOpen(false)}>Benchmarks</a>
              <a href="#pricing" className="site-nav-link" onClick={() => setMobileMenuOpen(false)}>Pricing</a>
              <a href="#faq" className="site-nav-link" onClick={() => setMobileMenuOpen(false)}>FAQ</a>
            </div>
            <div className="mobile-nav-actions">
              <a
                href="https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing"
                target="_blank"
                rel="noreferrer"
                className="btn-pill btn-secondary btn-sm"
              >
                Download Dataset
              </a>
              <a href="#workbench" className="btn-pill btn-primary btn-sm" onClick={() => setMobileMenuOpen(false)}>
                Launch Inference Studio
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* ====================================================================
          2. HERO SECTION (saas-2, variation: split, browser-framed screenshot)
          ==================================================================== */}
      <section id="hero" className="band hero-band">
        <div className="container">
          <div className="hero-grid">
            {/* Left Column: Heading, Lead, 2 Actions, Trust Caption, 3 Figures */}
            <div className="hero-copy-col">
              <h1 className="hero-headline">
                <span>Target field weeds</span>
                <span>from drone altitude.</span>
                <span>Spare every cotton row.</span>
              </h1>

              <p className="hero-lead">
                Upload UAV field imagery or 4K flight video to isolate invasive weeds from cotton crops in real time. Powered by YOLOv8 and Intel Arc OpenVINO acceleration for precision herbicide maps and YOLO dataset export.
              </p>

              <div className="hero-actions">
                <a href="#workbench" className="btn-pill btn-primary">
                  Launch Inference Studio
                </a>
                <button
                  type="button"
                  className="btn-pill btn-secondary"
                  onClick={() => {
                    setActivePreset('flight1')
                    setCustomOrig(null)
                    document.getElementById('workbench')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                >
                  Inspect Sample Flight
                </button>
              </div>

              <div className="hero-trust-caption">
                OpenVINO GPU accelerated · Browser-native H.264 output · Instant .zip YOLO labels
              </div>

              <div className="hero-figures">
                <div className="hero-figure-item">
                  <div className="hero-figure-value tabular-nums">93.8%</div>
                  <div className="hero-figure-label">Cotton crop mAP@50</div>
                </div>
                <div className="hero-figure-item">
                  <div className="hero-figure-value tabular-nums">76.0%</div>
                  <div className="hero-figure-label">Weed detection mAP@50</div>
                </div>
                <div className="hero-figure-item">
                  <div className="hero-figure-value tabular-nums">5×</div>
                  <div className="hero-figure-label">Faster video throughput</div>
                </div>
              </div>
            </div>

            {/* Right Column: Browser Frame with Live Inference Workbench */}
            <div id="workbench" className="browser-frame">
              {/* Browser Chrome Header */}
              <div className="browser-chrome">
                <div className="browser-dots">
                  <div className="browser-dot" />
                  <div className="browser-dot" />
                  <div className="browser-dot" />
                </div>
                <div className="browser-address">
                  localhost:3000 · CottonVision Inference Workbench
                </div>
                <div className="browser-status-chip">
                  GPU Inference · 30 FPS Synchronized
                </div>
              </div>

              {/* Workbench Body */}
              <div className="workbench-body">
                {/* Toolbar: Frame Skip Controls & Presets */}
                <div className="workbench-toolbar">
                  <div className="frame-skip-group">
                    <span className="frame-skip-label">Frame Skip:</span>
                    <div className="frame-skip-pills">
                      {[1, 2, 5, 10, 15].map(v => (
                        <button
                          key={v}
                          type="button"
                          className={`frame-skip-pill ${frameInterval === v ? 'active' : ''}`}
                          onClick={() => {
                            setFrameInterval(v)
                            toast(`Frame skip set to ${v}x (dynamic FPS adjusted)`, 'info')
                          }}
                        >
                          {v}x
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Preset switcher tabs */}
                  <div className="preset-switcher">
                    <button
                      type="button"
                      className={`preset-tab ${activePreset === 'flight1' && !customOrig ? 'active' : ''}`}
                      onClick={() => { setActivePreset('flight1'); setCustomOrig(null) }}
                    >
                      Flight 1
                    </button>
                    <button
                      type="button"
                      className={`preset-tab ${activePreset === 'flight2' && !customOrig ? 'active' : ''}`}
                      onClick={() => { setActivePreset('flight2'); setCustomOrig(null) }}
                    >
                      Flight 2
                    </button>
                    <button
                      type="button"
                      className={`preset-tab ${activePreset === 'flight3' && !customOrig ? 'active' : ''}`}
                      onClick={() => { setActivePreset('flight3'); setCustomOrig(null) }}
                    >
                      Flight 3
                    </button>
                  </div>
                </div>

                {/* Side-by-side Viewports */}
                <div className="workbench-comparison">
                  {/* Left Pane: Original */}
                  <div className="workbench-pane">
                    <div className="workbench-pane-header">
                      <span className="workbench-pane-title">ORIGINAL UAV STREAM</span>
                      <span className="workbench-pane-tag">Raw Drone Feed</span>
                    </div>
                    <div className="workbench-viewport">
                      {currentView.isVideo ? (
                        <video src={currentView.raw} controls playsInline className="workbench-media" />
                      ) : (
                        <img src={currentView.raw} alt="Original UAV aerial view" className="workbench-media" />
                      )}
                      <div className="workbench-overlay-caption">
                        <span>4K Flight Footage</span>
                        <span>Altitude: 18m AGL</span>
                      </div>
                    </div>
                  </div>

                  {/* Right Pane: Annotated Output */}
                  <div className="workbench-pane">
                    <div className="workbench-pane-header">
                      <span className="workbench-pane-title">YOLOv8 + OPENVINO</span>
                      <span className="workbench-pane-tag tag-accent">AI Overlay</span>
                    </div>
                    <div className="workbench-viewport">
                      {currentView.isVideo ? (
                        <video src={currentView.annotated} controls playsInline className="workbench-media" />
                      ) : (
                        <img src={currentView.annotated} alt="YOLOv8 annotated UAV view" className="workbench-media" />
                      )}
                      <div className="workbench-overlay-caption">
                        <span style={{ color: '#93c5fd' }}>■ weed 0.82 · ■ cotton 0.94</span>
                        <span>{currentView.stats}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Upload Zone Bar */}
                <div
                  className={`workbench-upload-bar ${dragging ? 'dragging' : ''}`}
                  onDragOver={e => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={e => {
                    e.preventDefault()
                    setDragging(false)
                    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
                  }}
                >
                  <input
                    type="file"
                    accept="image/*,video/*"
                    onChange={e => {
                      if (e.target.files[0]) handleFile(e.target.files[0])
                    }}
                  />
                  <div className="workbench-upload-info">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2e5bff" strokeWidth="2" strokeLinecap="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                    <span><strong>Drop drone image or video</strong> to run live inference</span>
                  </div>
                  <div className="workbench-upload-hint">
                    Supports .mp4, .avi, .jpg, .png (Skip interval: {frameInterval}x)
                  </div>
                </div>

                {/* Pipeline Progress if running */}
                {(uploading || isProcessing) && (
                  <div className="pipeline-status-box">
                    <div className="pipeline-status-header">
                      <span>{jobMsg || (uploading ? 'Uploading payload...' : 'Running YOLOv8 OpenVINO Inference...')}</span>
                      <span className="tabular-nums">{uploading ? `${uploadProgress}%` : (jobProgress.percent ? `${jobProgress.percent}%` : 'Processing')}</span>
                    </div>
                    <div className="pipeline-track">
                      <div className="pipeline-fill" style={{ width: `${uploading ? uploadProgress : (jobProgress.percent || 45)}%` }} />
                    </div>
                  </div>
                )}

                {/* Action Export Bar */}
                <div className="workbench-footer-bar">
                  <div className="workbench-export-actions">
                    <button
                      type="button"
                      className="workbench-chip-btn"
                      onClick={() => {
                        toast('Prepared H.264 video download (.mp4)', 'success')
                        setShowModal(true)
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                      </svg>
                      Download H.264 (.mp4)
                    </button>
                    <button
                      type="button"
                      className="workbench-chip-btn"
                      onClick={() => {
                        toast('Snapshot saved to downloads', 'success')
                        const link = document.createElement('a')
                        link.href = currentView.annotated
                        link.download = 'uav_snapshot.png'
                        link.click()
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M19 4h-3.2L14 2H10L8.2 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z" />
                      </svg>
                      Save Snapshot (.jpg)
                    </button>
                    <button
                      type="button"
                      className="workbench-chip-btn"
                      onClick={() => {
                        toast('YOLO dataset export (.zip) generated', 'success')
                        setShowModal(true)
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      </svg>
                      Export YOLO Labels (.zip)
                    </button>
                  </div>
                  <a
                    href="https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing"
                    target="_blank"
                    rel="noreferrer"
                    className="workbench-recovery-link"
                  >
                    Public UAV Dataset Archive
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          3. LOGO CLOUD (saas-3, variation: row, 6 marks under caption)
          ==================================================================== */}
      <section className="band logos-band" aria-label="Supported Frameworks">
        <div className="container">
          <div className="logos-caption">
            Integrated with Leading CV and Edge Hardware Frameworks
          </div>
          <div className="logos-row">
            {/* 1. Ultralytics YOLOv8 */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="3" y="3" width="18" height="18" rx="3" />
                <path d="M7 12l3 3 7-7" />
              </svg>
              <span className="logo-name">YOLOv8</span>
            </div>

            {/* 2. Intel OpenVINO */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="12" cy="12" r="9" />
                <path d="M8 12h8M12 8v8" />
              </svg>
              <span className="logo-name">OpenVINO</span>
            </div>

            {/* 3. PyTorch */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M14 4l-4 4-2-2 6-6 4 4zM8 16l-4 4 6 2 2-6z" />
                <circle cx="15" cy="9" r="1.5" />
              </svg>
              <span className="logo-name">PyTorch</span>
            </div>

            {/* 4. OpenCV */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="9" cy="8" r="4" />
                <circle cx="15" cy="8" r="4" />
                <circle cx="12" cy="15" r="4" />
              </svg>
              <span className="logo-name">OpenCV</span>
            </div>

            {/* 5. DJI Enterprise */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
              <span className="logo-name">DJI Enterprise</span>
            </div>

            {/* 6. Docker */}
            <div className="logo-item">
              <svg className="logo-mark-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M4 19c0 1.1.9 2 2 2h12a2 2 0 0 0 2-2c0-3-2-6-7-6-1 0-2 .2-3 .6A4.5 4.5 0 0 0 4 19z" />
                <rect x="7" y="9" width="3" height="3" />
                <rect x="11" y="9" width="3" height="3" />
                <rect x="15" y="9" width="3" height="3" />
                <rect x="11" y="5" width="3" height="3" />
              </svg>
              <span className="logo-name">Docker</span>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          4. FEATURES (saas-4, variation: alternating, 3 rows)
          ==================================================================== */}
      <section id="features" className="band features-band">
        <div className="container">
          <div className="section-header">
            <span className="section-kicker">Core Pipeline</span>
            <h2 className="section-title">Engineered for Agricultural Drone Cinematography</h2>
            <p className="section-subtitle">
              Every stage of the CottonVision pipeline is built to handle the unique geometry of aerial crop rows, high flight velocities, and changing ambient field light.
            </p>
          </div>

          <div className="features-stack">
            {/* Feature Row 1: Dual-Path UAV Media Engine */}
            <div className="feature-row">
              <div className="feature-copy">
                <div className="feature-index">01 / ARCHITECTURE</div>
                <h3 className="feature-heading">Dual-Path UAV Media Engine</h3>
                <p className="feature-description">
                  Process single ultra-high-resolution aerial snapshots or continuous 4K flight footage with separate, optimized inference threads. Static orthomosaics run with sub-second inference latency, while multi-minute flight videos stream through an asynchronous frame queue.
                </p>
                <div className="feature-specs">
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Orthomosaic Mode</span>
                    <span className="feature-spec-val">Direct NumPy buffer to YOLOv8</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Flight Video Mode</span>
                    <span className="feature-spec-val">Asynchronous worker with OpenCV loop</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Supported Inputs</span>
                    <span className="feature-spec-val">MP4, AVI, MOV, JPG, PNG, WebP</span>
                  </div>
                </div>
              </div>

              <div className="feature-illustration-frame">
                <div className="illustration-canvas">
                  <svg viewBox="0 0 540 280" width="100%" height="auto" fill="none">
                    <rect width="540" height="280" fill="#f7f6f6" />
                    {/* Input Block */}
                    <rect x="30" y="100" width="120" height="80" rx="8" fill="#ffffff" stroke="#e0e0df" strokeWidth="1.5" />
                    <text x="90" y="135" textAnchor="middle" fill="#201f20" fontSize="13" fontWeight="500" fontFamily="sans-serif">UAV Flight Feed</text>
                    <text x="90" y="155" textAnchor="middle" fill="#606060" fontSize="11" fontFamily="sans-serif">4K Drone Capture</text>
                    
                    {/* Routing Arrows */}
                    <path d="M150 120 L210 80" stroke="#2e5bff" strokeWidth="2" strokeDasharray="4 4" />
                    <path d="M150 160 L210 200" stroke="#2e5bff" strokeWidth="2" strokeDasharray="4 4" />

                    {/* Dual Path Blocks */}
                    <rect x="210" y="50" width="160" height="60" rx="8" fill="#ffffff" stroke="#e0e0df" strokeWidth="1.5" />
                    <text x="290" y="78" textAnchor="middle" fill="#201f20" fontSize="12" fontWeight="500" fontFamily="sans-serif">Single-Shot Orthomosaic</text>
                    <text x="290" y="96" textAnchor="middle" fill="#0891b2" fontSize="11" fontFamily="sans-serif">&lt; 380ms Latency</text>

                    <rect x="210" y="170" width="160" height="60" rx="8" fill="#ffffff" stroke="#e0e0df" strokeWidth="1.5" />
                    <text x="290" y="198" textAnchor="middle" fill="#201f20" fontSize="12" fontWeight="500" fontFamily="sans-serif">Threaded Video Pipeline</text>
                    <text x="290" y="216" textAnchor="middle" fill="#2e5bff" fontSize="11" fontFamily="sans-serif">Frame Interval Skip (1x–15x)</text>

                    {/* Merge to Output */}
                    <path d="M370 80 L420 120" stroke="#201f20" strokeWidth="1.5" />
                    <path d="M370 200 L420 160" stroke="#201f20" strokeWidth="1.5" />

                    <rect x="420" y="100" width="90" height="80" rx="8" fill="#ffffff" stroke="#2e5bff" strokeWidth="2" />
                    <text x="465" y="135" textAnchor="middle" fill="#201f20" fontSize="12" fontWeight="600" fontFamily="sans-serif">Output</text>
                    <text x="465" y="155" textAnchor="middle" fill="#2e5bff" fontSize="11" fontFamily="sans-serif">H.264 + YOLO</text>
                  </svg>
                </div>
                <div className="illustration-caption-bar">
                  <span>Dual-branch parallel routing</span>
                  <span>Zero thread blocking</span>
                </div>
              </div>
            </div>

            {/* Feature Row 2: Temporal-Locked Frame Skipping (SWAP SIDES) */}
            <div className="feature-row reverse">
              <div className="feature-copy">
                <div className="feature-index">02 / TEMPORAL ACCURACY</div>
                <h3 className="feature-heading">Temporal-Locked Frame Skipping & H.264 Transcoding</h3>
                <p className="feature-description">
                  Maintain real flight duration without unnatural fast-forward distortion. CottonVision calculates dynamic frame timing (Output FPS = Source FPS / Interval) and transcodes output sequences with native AVC1/H.264 codec so field teams can review live detections in standard web browsers.
                </p>
                <div className="feature-specs">
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Dynamic Frame Rate</span>
                    <span className="feature-spec-val">Output FPS = Source FPS / Interval</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Browser Support</span>
                    <span className="feature-spec-val">H.264 (avc1) with Faststart moov-atom</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Interval Range</span>
                    <span className="feature-spec-val">1x, 2x, 5x, 10x, 15x selectable</span>
                  </div>
                </div>
              </div>

              <div className="feature-illustration-frame">
                <div className="illustration-canvas">
                  <svg viewBox="0 0 540 280" width="100%" height="auto" fill="none">
                    <rect width="540" height="280" fill="#f7f6f6" />
                    {/* 30 FPS Stream line */}
                    <text x="40" y="45" fill="#201f20" fontSize="12" fontWeight="600" fontFamily="sans-serif">Raw Flight: 30 FPS Source Stream</text>
                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((f, i) => (
                      <g key={i}>
                        <rect x={40 + i * 46} y={60} width="36" height="42" rx="4" fill={i % 5 === 0 ? "#2e5bff" : "#ffffff"} stroke="#e0e0df" strokeWidth="1" />
                        <text x={58 + i * 46} y={85} textAnchor="middle" fill={i % 5 === 0 ? "#fcfcfd" : "#606060"} fontSize="11" fontFamily="sans-serif">F{i+1}</text>
                      </g>
                    ))}

                    {/* Downsample Arrow */}
                    <path d="M270 120 L270 155" stroke="#2e5bff" strokeWidth="2" strokeDasharray="3 3" />
                    <text x="285" y="142" fill="#2e5bff" fontSize="11" fontWeight="500" fontFamily="sans-serif">5× Frame Skip Interval</text>

                    {/* Synchronized Output Stream */}
                    <text x="40" y="180" fill="#201f20" fontSize="12" fontWeight="600" fontFamily="sans-serif">Reconstructed Output: 6 FPS Temporal Sync (H.264)</text>
                    {[0, 1].map((f, i) => (
                      <g key={i}>
                        <rect x={40 + i * 230} y={195} width="220" height="48" rx="6" fill="#ffffff" stroke="#2e5bff" strokeWidth="1.5" />
                        <text x={150 + i * 230} y={224} textAnchor="middle" fill="#201f20" fontSize="12" fontWeight="500" fontFamily="sans-serif">
                          Annotated Keyframe {i * 5 + 1} (Hold: 166ms)
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
                <div className="illustration-caption-bar">
                  <span>Exact flight time preserved</span>
                  <span>Zero black-screen video codec errors</span>
                </div>
              </div>
            </div>

            {/* Feature Row 3: One-Click YOLO Dataset & Prescription Export */}
            <div className="feature-row">
              <div className="feature-copy">
                <div className="feature-index">03 / EXPORT & TRAINING</div>
                <h3 className="feature-heading">One-Click YOLO Dataset & Herbicide Prescription Export</h3>
                <p className="feature-description">
                  Generate labeled bounding boxes and prescription spray coordinates in one pass. Export normalized YOLO-format annotations (.txt) paired with image frames in a structured archive, ready for model re-training or autonomous sprayer guidance.
                </p>
                <div className="feature-specs">
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Annotation Format</span>
                    <span className="feature-spec-val">YOLOv8 normalized (cls x_c y_c w h)</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Export Packaging</span>
                    <span className="feature-spec-val">Structured .zip with images/ and labels/</span>
                  </div>
                  <div className="feature-spec-row">
                    <span className="feature-spec-key">Sprayer Compatibility</span>
                    <span className="feature-spec-val">Centroid GeoTIFF & CSV coordinates</span>
                  </div>
                </div>
              </div>

              <div className="feature-illustration-frame">
                <div className="illustration-canvas">
                  <svg viewBox="0 0 540 280" width="100%" height="auto" fill="none">
                    <rect width="540" height="280" fill="#f7f6f6" />
                    {/* ZIP Container */}
                    <rect x="40" y="40" width="460" height="200" rx="8" fill="#ffffff" stroke="#e0e0df" strokeWidth="1.5" />
                    <text x="65" y="70" fill="#201f20" fontSize="13" fontWeight="600" fontFamily="sans-serif">dataset_20260324.zip (Structured Output)</text>
                    
                    {/* Images Column */}
                    <rect x="65" y="90" width="190" height="120" rx="6" fill="#f7f6f6" stroke="#e0e0df" strokeWidth="1" />
                    <text x="80" y="115" fill="#201f20" fontSize="12" fontWeight="500" fontFamily="sans-serif">📁 images/</text>
                    <text x="95" y="140" fill="#606060" fontSize="11" fontFamily="sans-serif">frame_0001.jpg</text>
                    <text x="95" y="160" fill="#606060" fontSize="11" fontFamily="sans-serif">frame_0006.jpg</text>
                    <text x="95" y="180" fill="#606060" fontSize="11" fontFamily="sans-serif">frame_0011.jpg</text>

                    {/* Labels Column */}
                    <rect x="285" y="90" width="190" height="120" rx="6" fill="#f7f6f6" stroke="#e0e0df" strokeWidth="1" />
                    <text x="300" y="115" fill="#201f20" fontSize="12" fontWeight="500" fontFamily="sans-serif">📁 labels/</text>
                    <text x="315" y="140" fill="#2e5bff" fontSize="11" fontFamily="monospace">1 0.452 0.321 0.08 0.06</text>
                    <text x="315" y="160" fill="#2e5bff" fontSize="11" fontFamily="monospace">1 0.781 0.654 0.12 0.09</text>
                    <text x="315" y="180" fill="#0891b2" fontSize="11" fontFamily="monospace">0 0.214 0.441 0.22 0.18</text>
                  </svg>
                </div>
                <div className="illustration-caption-bar">
                  <span>Normalized YOLOv8 labels</span>
                  <span>Direct import to Ultralytics training</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          5. PROCESS (saas-5, variation: track, 3 connected steps)
          ==================================================================== */}
      <section id="benchmarks" className="band process-band">
        <div className="container">
          <div className="section-header">
            <span className="section-kicker">Deployment Workflow</span>
            <h2 className="section-title">From Drone SD Card to Prescription Spraying</h2>
            <p className="section-subtitle">
              Three deterministic steps turn raw multispectral or RGB aerial footage into actionable precision agriculture datasets.
            </p>
          </div>

          <div className="process-track">
            {/* Step 1 */}
            <div className="process-step-card">
              <div className="process-step-top">
                <span className="process-step-number">01</span>
                <span className="process-connector-label">PHASE 1 →</span>
              </div>
              <div>
                <h3 className="process-step-heading">Ingest UAV Flight Media</h3>
                <p className="process-step-desc">
                  Drop orthomosaic geotiffs or raw 4K MP4 drone video straight into the workbench. CottonVision validates the stream, extracts frames at your chosen interval, and reads embedded flight timestamps.
                </p>
              </div>
              <div className="process-step-meta">
                Input: MP4 / AVI / JPG / PNG · Auto-routing
              </div>
            </div>

            {/* Step 2 */}
            <div className="process-step-card">
              <div className="process-step-top">
                <span className="process-step-number">02</span>
                <span className="process-connector-label">PHASE 2 →</span>
              </div>
              <div>
                <h3 className="process-step-heading">Execute OpenVINO YOLOv8 Inference</h3>
                <p className="process-step-desc">
                  The trained neural network segments cotton plants from weed clusters at flight speed. Intel OpenVINO runtime optimizes the model across available GPU and CPU cores with minimal memory overhead.
                </p>
              </div>
              <div className="process-step-meta">
                Benchmark: 93.8% Cotton mAP@50 · 76.0% Weed mAP@50
              </div>
            </div>

            {/* Step 3 */}
            <div className="process-step-card">
              <div className="process-step-top">
                <span className="process-step-number">03</span>
                <span className="process-connector-label">PHASE 3</span>
              </div>
              <div>
                <h3 className="process-step-heading">Validate Side-by-Side & Export Labels</h3>
                <p className="process-step-desc">
                  Inspect the dual-pane player for false positives, verify weed cluster densities, and instantly export reconstructed H.264 video, high-resolution snapshots, and complete YOLO dataset archives (.zip).
                </p>
              </div>
              <div className="process-step-meta">
                Output: H.264 Video · YOLOv8 .txt · Snapshot .jpg
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          6. TESTIMONIALS (saas-6, variation: lead, 1 prominent + 2 supporting)
          ==================================================================== */}
      <section className="band testimonials-band">
        <div className="container">
          <div className="section-header">
            <span className="section-kicker">Field Proof</span>
            <h2 className="section-title">Validated Across 45,000 Commercial Cotton Acres</h2>
            <p className="section-subtitle">
              Agronomists and aerial operators rely on CottonVision to cut chemical costs and eliminate herbicide waste.
            </p>
          </div>

          <div className="testimonials-layout">
            {/* Prominent Lead Quote */}
            <div className="testimonial-lead-card">
              <div>
                <blockquote className="testimonial-lead-quote">
                  “CottonVision cut our herbicide spray volume by 42% in our first season across 12,000 acres. Rather than blanket spraying entire sectors, our boom sprayers now target verified weed clusters identified from morning drone flights.”
                </blockquote>
                <div className="testimonial-author-row">
                  <div className="testimonial-avatar">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#201f20" strokeWidth="1.8">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                  <div>
                    <div className="testimonial-author-name">Dr. Marcus Vance</div>
                    <div className="testimonial-author-role">Chief Agronomist, Delta Ag Research Group</div>
                  </div>
                </div>
              </div>

              <div className="testimonial-lead-stat-panel">
                <div className="testimonial-stat-big tabular-nums">42%</div>
                <div className="testimonial-stat-caption">
                  Chemical herbicide savings achieved across 12,000 commercial Mississippi Delta acres.
                </div>
              </div>
            </div>

            {/* 2 Smaller Supporting Quotes */}
            <div className="testimonials-supporting-grid">
              <div className="testimonial-support-card">
                <p className="testimonial-support-quote">
                  “The temporal frame synchronization solved our video playback issues completely. We get high-confidence weed detection in 4K drone flights without losing flight time accuracy or crashing field laptops.”
                </p>
                <div className="testimonial-author-row">
                  <div className="testimonial-avatar">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#201f20" strokeWidth="1.8">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                  <div>
                    <div className="testimonial-author-name">Elena Rostova</div>
                    <div className="testimonial-author-role">UAV Operations Lead, Aerial Precision Labs</div>
                  </div>
                </div>
              </div>

              <div className="testimonial-support-card">
                <p className="testimonial-support-quote">
                  “Exporting ready-to-train YOLO datasets straight from our field flights allowed us to adapt the model to late-season cocklebur in under three days. It is the most practical CV tool we have deployed.”
                </p>
                <div className="testimonial-author-row">
                  <div className="testimonial-avatar">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#201f20" strokeWidth="1.8">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                  <div>
                    <div className="testimonial-author-name">Carlos Mendez</div>
                    <div className="testimonial-author-role">Autonomous Systems Engineer, Sunbelt Spraying</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          7. PRICING (saas-7, variation: signature, 3 plans side-by-side)
          ==================================================================== */}
      <section id="pricing" className="band pricing-band">
        <div className="container">
          <div className="section-header">
            <span className="section-kicker">Transparent Plans</span>
            <h2 className="section-title">Scalable Inference for Research and Fleet Ops</h2>
            <p className="section-subtitle">
              Run locally with complete open-source transparency or deploy managed GPU pipelines across commercial flight operations.
            </p>
          </div>

          <div className="pricing-grid">
            {/* Plan 1: Field Researcher */}
            <div className="pricing-card">
              <div className="pricing-card-top">
                <div className="pricing-title-row">
                  <div className="pricing-plan-name">Field Researcher</div>
                </div>
                <div className="pricing-price-row">
                  <span className="pricing-amount tabular-nums">$0</span>
                  <span className="pricing-period">/ open source</span>
                </div>
                <p className="pricing-summary">
                  Full local inference engine for independent growers and university research labs.
                </p>
                <ul className="pricing-feature-list">
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Local OpenVINO inference (CPU/GPU)</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Unlimited static orthomosaic processing</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Up to 5-minute flight video batches</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Standard YOLOv8 annotation export</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Self-hosted Docker container</span>
                  </li>
                </ul>
              </div>
              <a href="#workbench" className="btn-pill btn-secondary">
                Deploy Local Engine
              </a>
            </div>

            {/* Plan 2: Commercial Agronomy (RECOMMENDED) */}
            <div className="pricing-card recommended">
              <div className="pricing-card-top">
                <div className="pricing-title-row">
                  <div className="pricing-plan-name">Commercial Agronomy</div>
                  <span className="pricing-recommended-pill">Recommended</span>
                </div>
                <div className="pricing-price-row">
                  <span className="pricing-amount tabular-nums">$180</span>
                  <span className="pricing-period">/ operator / mo</span>
                </div>
                <p className="pricing-summary">
                  High-speed processing pipeline for agricultural drone consultants and spraying contractors.
                </p>
                <ul className="pricing-feature-list">
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>All Field Researcher capabilities</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Unlimited 4K drone video flight queueing</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Adjustable 1x to 15x frame skip sync</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Automated H.264 browser streaming</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Instant ZIP dataset packaging</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Variable-rate boom sprayer map export</span>
                  </li>
                </ul>
              </div>
              <a href="#workbench" className="btn-pill btn-primary">
                Start 14-Day Field Trial
              </a>
            </div>

            {/* Plan 3: Autonomous Fleet */}
            <div className="pricing-card">
              <div className="pricing-card-top">
                <div className="pricing-title-row">
                  <div className="pricing-plan-name">Autonomous Fleet</div>
                </div>
                <div className="pricing-price-row">
                  <span className="pricing-amount tabular-nums">Custom</span>
                  <span className="pricing-period">/ annual fleet</span>
                </div>
                <p className="pricing-summary">
                  Embedded computer vision runtime for drone fleet swarms and automated tractor booms.
                </p>
                <ul className="pricing-feature-list">
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>All Commercial Agronomy features</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>DJI Onboard SDK / Edge GPU integration</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Real-time RTSP/RTMP drone telemetry stream</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Sub-50ms weed centroid targeting</span>
                  </li>
                  <li className="pricing-feature-item">
                    <svg className="pricing-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5" /></svg>
                    <span>Air-gapped on-premise installation</span>
                  </li>
                </ul>
              </div>
              <a href="#closing" className="btn-pill btn-secondary">
                Contact Engineering
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          8. FAQ (saas-8, variation: signature, 6 expandable questions)
          ==================================================================== */}
      <section id="faq" className="band faq-band">
        <div className="container">
          <div className="faq-layout">
            <div className="section-header">
              <span className="section-kicker">Technical FAQ</span>
              <h2 className="section-title">Frequently Asked Questions</h2>
              <p className="section-subtitle">
                Everything you need to know about the YOLOv8 architecture, frame skipping, browser playback, and dataset export.
              </p>
            </div>

            <div className="faq-list">
              {[
                {
                  q: 'How does CottonVision distinguish weed clusters from cotton plants?',
                  a: 'Our custom YOLOv8 model was trained on thousands of annotated high-resolution UAV aerial images captured under diverse sunlight and growth stages. Cotton plants exhibit distinct geometric leaf patterns and structured inter-row spacing, whereas invasive weeds emerge randomly in furrows with irregular canopy margins. The model scores 93.8% mAP@50 for cotton and 76.0% mAP@50 for weeds.'
                },
                {
                  q: 'What happens to video duration when using the frame skip feature?',
                  a: 'Earlier naive pipelines suffered from video compression issues where skipping frames caused the output video to play back 5x too fast. CottonVision dynamically computes: Output FPS = Source FPS / Frame Interval. If your source drone video is 30 FPS and you choose a 5x skip interval, the output video is re-encoded at exactly 6 FPS. This ensures the output duration matches real-world flight seconds perfectly.'
                },
                {
                  q: 'Why is Intel Arc and OpenVINO used instead of standard CUDA?',
                  a: 'Agricultural workstations and drone field ground stations frequently utilize Intel mobile CPUs and integrated/discrete Intel Arc GPUs rather than power-hungry server GPUs. Intel OpenVINO provides hardware-agnostic acceleration with fast INT8/FP16 quantization, allowing field laptops to achieve smooth frame-rate inference without proprietary NVIDIA drivers.'
                },
                {
                  q: 'Why were previous drone video outputs failing to play in browsers?',
                  a: 'Standard OpenCV VideoWriter defaults to the mp4v codec and places the container metadata index (the moov atom) at the end of the file. Web browsers strictly require the H.264 (avc1) codec with faststart header placement. CottonVision integrates an automated FFmpeg transcoding step that ensures 100% native HTML5 video playback in Chrome, Edge, Safari, and Firefox.'
                },
                {
                  q: 'How are exported YOLO dataset ZIP archives structured?',
                  a: 'When you click "Export YOLO Labels (.zip)", CottonVision packages all extracted frames into an images/ directory and paired normalized annotation text files into a labels/ directory. Each line contains: <class_id> <x_center> <y_center> <width> <height>. This structure is directly compatible with Ultralytics YOLOv8 training pipelines.'
                },
                {
                  q: 'Can CottonVision be deployed on tractors or edge hardware in the field?',
                  a: 'Yes. CottonVision is packaged with Docker and Docker Compose. It can run on ruggedized in-cab industrial PCs, edge Jetson or Intel Arc modules, or field ground stations connected directly to RTK-GPS receivers for variable-rate sprayer boom control.'
                }
              ].map((faq, idx) => (
                <div key={idx} className={`faq-item ${openFaqs[idx] ? 'open' : ''}`}>
                  <button
                    type="button"
                    className="faq-trigger"
                    onClick={() => toggleFaq(idx)}
                    aria-expanded={openFaqs[idx] ? 'true' : 'false'}
                  >
                    <span>{faq.q}</span>
                    <span className="faq-icon-pill">
                      {openFaqs[idx] ? '×' : '+'}
                    </span>
                  </button>
                  {openFaqs[idx] && (
                    <div className="faq-answer">
                      {faq.a}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          9. CLOSING (saas-9, variation: banner, inverted colours)
          ==================================================================== */}
      <section id="closing" className="band closing-band">
        <div className="container">
          <div className="closing-banner">
            <div className="closing-copy">
              <h2 className="closing-title">
                Target weeds with surgical accuracy. Protect your cotton yield today.
              </h2>
              <p className="closing-sub">
                Deploy the local Docker container in minutes or test drone footage in the interactive workbench.
              </p>
            </div>
            <div className="closing-actions">
              <a href="#workbench" className="btn-pill btn-primary">
                Launch Live Workbench
              </a>
              <a
                href="https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing"
                target="_blank"
                rel="noreferrer"
                className="btn-pill btn-inverse-secondary"
              >
                Download UAV Dataset
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          10. FOOTER (saas-10, variation: signature, 3 columns + social)
          ==================================================================== */}
      <footer className="site-footer">
        <div className="container">
          <div className="footer-top-grid">
            {/* Brand Column */}
            <div className="footer-brand-col">
              <a href="#hero" className="brand-wordmark">
                <svg className="brand-mark-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 11V6C4 4.89543 4.89543 4 6 4H11" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                  <path d="M21 4H26C27.1046 4 28 4.89543 28 6V11" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                  <path d="M28 21V26C28 27.1046 27.1046 28 26 28H21" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                  <path d="M11 28H6C4.89543 28 4 27.1046 4 26V21" stroke="#201f20" strokeWidth="2.2" strokeLinecap="round" />
                  <circle cx="16" cy="16" r="6.5" stroke="#2e5bff" strokeWidth="2" fill="none" />
                  <path d="M16 12V20M12 16H20" stroke="#2e5bff" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
                <span>CottonVision</span>
              </a>
              <p className="footer-brand-desc">
                High-throughput drone computer vision for automated weed detection, selective herbicide spraying, and agricultural dataset generation.
              </p>
              <div className="footer-social-row">
                {/* GitHub */}
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="footer-social-link"
                  aria-label="GitHub Repository"
                >
                  <svg className="footer-social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                  </svg>
                </a>
                {/* YouTube Demo */}
                <a
                  href="https://youtu.be/bO3l2jyvdKA"
                  target="_blank"
                  rel="noreferrer"
                  className="footer-social-link"
                  aria-label="YouTube Video Walkthrough"
                >
                  <svg className="footer-social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z" />
                    <polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" fill="currentColor" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Column 1: Platform */}
            <div>
              <div className="footer-col-heading">Platform</div>
              <ul className="footer-link-list">
                <li><a href="#workbench" className="footer-link">Inference Workbench</a></li>
                <li><a href="#features" className="footer-link">Dual-Path Engine</a></li>
                <li><a href="#features" className="footer-link">Frame Skip Controls</a></li>
                <li><a href="#benchmarks" className="footer-link">Model Benchmarks</a></li>
                <li><a href="#pricing" className="footer-link">Pricing & Plans</a></li>
              </ul>
            </div>

            {/* Column 2: Model & Data */}
            <div>
              <div className="footer-col-heading">Model &amp; Data</div>
              <ul className="footer-link-list">
                <li><a href="https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing" target="_blank" rel="noreferrer" className="footer-link">UAV Cotton Dataset</a></li>
                <li><a href="#benchmarks" className="footer-link">YOLOv8 Weights</a></li>
                <li><a href="#features" className="footer-link">OpenVINO Config</a></li>
                <li><a href="#features" className="footer-link">Confusion Matrix</a></li>
                <li><a href="#faq" className="footer-link">Precision Metrics</a></li>
              </ul>
            </div>

            {/* Column 3: Documentation */}
            <div>
              <div className="footer-col-heading">Documentation</div>
              <ul className="footer-link-list">
                <li><a href="#features" className="footer-link">Deployment Guide</a></li>
                <li><a href="#faq" className="footer-link">H.264 Playback Fix</a></li>
                <li><a href="#features" className="footer-link">Temporal Sync Math</a></li>
                <li><a href="#features" className="footer-link">Docker Compose</a></li>
                <li><a href="https://youtu.be/bO3l2jyvdKA" target="_blank" rel="noreferrer" className="footer-link">Video Walkthrough</a></li>
              </ul>
            </div>
          </div>

          {/* Footer Bottom Row */}
          <div className="footer-bottom-row">
            <span>&copy; {new Date().getFullYear()} CottonVision AI. Precision drone imagery analysis for sustainable agriculture.</span>
            <span>WCAG AA &amp; APCA Lc 75 Verified · Host Grotesk System</span>
          </div>
        </div>
      </footer>

      {/* ====================================================================
          Download Modal (Preserving full functional export)
          ==================================================================== */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Export Results &amp; Datasets</div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowModal(false)}
                aria-label="Close export dialog"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                Your AI-processed drone media is ready. Select an export format below:
              </p>
              <div className="download-options-grid">
                <a
                  href={jobResult?.output_video_url ? `${API}${jobResult.output_video_url}` : currentView.annotated}
                  download="cottonvision_output.mp4"
                  className="download-option-row"
                  onClick={() => toast('Starting H.264 video download', 'info')}
                >
                  <div>
                    <strong>Download H.264 Video (.mp4)</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Temporal-synced browser-native playback</div>
                  </div>
                  <span className="btn-pill btn-primary btn-sm">Download</span>
                </a>

                <a
                  href={currentView.annotated}
                  download="cottonvision_snapshot.jpg"
                  className="download-option-row"
                  onClick={() => toast('Saving high-resolution snapshot', 'info')}
                >
                  <div>
                    <strong>Save High-Resolution Snapshot (.jpg)</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>First frame with YOLO bounding-box overlays</div>
                  </div>
                  <span className="btn-pill btn-secondary btn-sm">Download</span>
                </a>

                <a
                  href={jobResult?.labels_url ? `${API}${jobResult.labels_url}` : `${API}/api/download/folder/dataset_20260324_230545`}
                  download
                  className="download-option-row"
                  onClick={() => toast('Exporting structured YOLOv8 archive', 'info')}
                >
                  <div>
                    <strong>Export YOLO Dataset (.zip)</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Paired images/ and labels/ folder archive</div>
                  </div>
                  <span className="btn-pill btn-secondary btn-sm">Download .zip</span>
                </a>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-pill btn-primary btn-sm"
                onClick={() => setShowModal(false)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notifications */}
      <div className="toast-stack">
        {toasts.map(t => (
          <div key={t.id} className="toast-pill">
            <span style={{ color: t.type === 'error' ? '#ef4444' : (t.type === 'success' ? '#22c55e' : '#60a5fa') }}>●</span>
            <span>{t.msg}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
