import { useState, useRef, useCallback, useEffect } from 'react'

/* ── helpers ─────────────────────────────────────────────── */
const API = ''  // proxied by Vite → localhost:5000

function useToasts() {
  const [toasts, setToasts] = useState([])
  const add = useCallback((msg, type = 'info') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000)
  }, [])
  return { toasts, add }
}

/* ── MediaCard ───────────────────────────────────────────── */
function MediaCard({ label, isProcessed, src, type, labelUrl }) {
  const isEmpty = !src
  return (
    <div className="media-card">
      <div className="media-card-header">
        <span className={`media-card-label ${isProcessed ? 'processed-label' : 'original-label'}`}>
          {label}
        </span>
        {isProcessed && <span className="ai-badge">✦ AI</span>}
      </div>
      <div className="media-card-body">
        {isEmpty ? (
          <div className="media-placeholder">
            <span className="placeholder-icon">{type === 'video' ? '🎬' : '🖼️'}</span>
            <span>Awaiting {type === 'video' ? 'video' : 'image'}</span>
          </div>
        ) : type === 'video' ? (
          <video key={src} className="media-preview" src={src} controls playsInline />
        ) : (
          <img className="media-preview" src={src} alt={label} />
        )}
      </div>
      {isProcessed && labelUrl && (
        <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', textAlign: 'center' }}>
          <a href={labelUrl} download className="label-download-link">📄 Download Labels (.txt)</a>
        </div>
      )}
    </div>
  )
}

/* ── DownloadModal ────────────────────────────────────────── */
function DownloadModal({ isOpen, onClose, result }) {
  if (!isOpen) return null

  const items = [
    { url: result?.output_video_url, icon: '📥', label: 'Download Video', sub: '.mp4 (H.264 Optimized)' },
    { url: result?.snapshot_url, icon: '🖼️', label: 'Save Snapshot', sub: '.jpg (First Frame)' },
    { url: result?.labels_url, icon: '📋', label: 'Download YOLO Dataset', sub: '.zip (Full Folder)' },
  ]

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">🎉 Processing Complete!</div>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Your AI-processed media is ready. You can download the video, a high-res snapshot, or the full YOLO dataset (paired images and labels).
          </p>
          <div className="download-grid">
            {items.map((item, i) => (
              <a key={i} href={item.url ? `${API}${item.url}` : '#'}
                download={item.url ? true : false}
                className={`download-btn ${!item.url ? 'disabled' : ''}`}>
                <span className="download-btn-icon">{item.icon}</span>
                <span className="download-btn-label">{item.label}</span>
                <span className="download-btn-sub">{item.url ? item.sub : 'Generating...'}</span>
              </a>
            ))}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose} style={{ width: '100%', padding: '0.8rem' }}>Close</button>
        </div>
      </div>
    </div>
  )
}

/* ── PipelineProgress ────────────────────────────────────── */
function PipelineProgress({ status, message, progress, result, onOpenModal }) {
  if (!status) return null

  if (status === 'done') {
    return (
      <div className="pipeline-progress success">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div className="pipeline-step" style={{ color: 'var(--success)', marginBottom: '0.2rem' }}>✅ Pipeline Complete</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Files are ready for download.</div>
          </div>
          <button className="btn-success" onClick={onOpenModal} style={{ padding: '0.6rem 1.2rem', borderRadius: '8px', fontWeight: 'bold' }}>
            📥 DOWNLOAD RESULTS
          </button>
        </div>
      </div>
    )
  }

  const stepLabels = {
    extracting: '📦 Extracting Frames',
    annotating: '🔬 AI Inference (GPU Enabled)',
    converting: '🎬 Building H.264 Video',
  }

  const stepLabel = stepLabels[progress?.step] || '⏳ Processing…'
  const percent = progress?.percent || 0
  const current = progress?.current || 0
  const total = progress?.total || 0

  return (
    <div className="pipeline-progress">
      <div className="pipeline-step">{stepLabel}</div>
      {total > 0 && <div className="pipeline-frame-count">Progress: {current} / {total} frames</div>}
      <div className="pipeline-bar-wrap">
        <div className="pipeline-bar-fill" style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <div className="pipeline-percent">{percent}%</div>
      {message && <div className="pipeline-message">{message}</div>}
    </div>
  )
}

/* ── Main App ────────────────────────────────────────────── */
export default function App() {
  const { toasts, add: toast } = useToasts()

  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)

  const [origImage, setOrigImage] = useState(null)
  const [origVideo, setOrigVideo] = useState(null)
  const [aiImage, setAiImage] = useState(null)
  const [aiVideo, setAiVideo] = useState(null)
  const [aiImageLabel, setAiImageLabel] = useState(null)

  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [jobMsg, setJobMsg] = useState('')
  const [jobProgress, setJobProgress] = useState({})
  const [jobResult, setJobResult] = useState({})
  const [showModal, setShowModal] = useState(false)

  const [imageProcessing, setImageProcessing] = useState(false)
  const [frameInterval, setFrameInterval] = useState(5)
  const pollRef = useRef(null)

  const runImageInference = useCallback(async (filename) => {
    setImageProcessing(true)
    try {
      const res = await fetch(`${API}/api/process-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setAiImage(`${API}${data.annotated_url}`)
      setAiImageLabel(`${API}${data.label_url}`)
      toast('Inference complete! 🎉', 'success')
    } catch (e) {
      toast('Inference failed', 'error')
    } finally {
      setImageProcessing(false)
    }
  }, [toast])

  const runVideoPipeline = useCallback(async (filename) => {
    try {
      setShowModal(false)
      const res = await fetch(`${API}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, frame_interval: frameInterval }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setJobId(data.job_id); setJobStatus('queued'); setJobMsg('Job queued…')
      setJobProgress({}); setJobResult({})
      toast('Pipeline started!', 'success')
    } catch (e) {
      toast('Pipeline failed', 'error')
    }
  }, [toast, frameInterval])

  const handleFile = useCallback(async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    const isVideo = ['mp4', 'avi', 'mov', 'mkv'].includes(ext)
    const isImage = ['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)
    if (!isVideo && !isImage) return toast('Unsupported type', 'error')

    setJobId(null); setJobStatus(null); setAiImage(null); setAiVideo(null); setAiImageLabel(null)
    if (isImage) { setOrigImage(URL.createObjectURL(file)); setOrigVideo(null) }
    else { setOrigVideo(URL.createObjectURL(file)); setOrigImage(null) }

    setUploading(true); setProgress(10)
    const fd = new FormData(); fd.append('file', file)
    try {
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: fd })
      const data = await res.json()
      setProgress(100); toast(`Uploaded: ${data.filename}`, 'success')
      if (data.type === 'image') runImageInference(data.filename)
      else runVideoPipeline(data.filename)
    } catch (e) {
      toast('Upload failed', 'error')
    } finally {
      setUploading(false); setTimeout(() => setProgress(0), 800)
    }
  }, [toast, runImageInference, runVideoPipeline])

  useEffect(() => {
    if (!jobId) return
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/status/${jobId}`)
        const data = await res.json()
        setJobStatus(data.status); setJobMsg(data.message || ''); setJobProgress(data.progress || {})

        if (data.status === 'done') {
          clearInterval(pollRef.current)
          setAiVideo(`${API}${data.result.output_video_url}`)
          setJobResult(data.result)
          setShowModal(true) // OPEN MODAL AUTOMATICALLY
          toast('Complete! 🎉', 'success')
        }
        if (data.status === 'error') { clearInterval(pollRef.current); toast(`Error: ${data.message}`, 'error') }
      } catch (_) { }
    }, 1000)
    return () => clearInterval(pollRef.current)
  }, [jobId, toast])

  return (
    <div className="app-wrapper">
      <header className="header">
        <div className="header-logo"><div className="logo-icon">🌿</div> Inference of ML for Cotton-Weed Prediction</div>
        <div className="header-badge">HARDWARE ACCEL (GPU)</div>
      </header>

      <main className="main-content">
        <section className="hero">
          <h1>Inference of ML for Cotton-Weed Prediction</h1>
          <p>Intel Arc Optimized weed detection for drone photography and cinematography.</p>
        </section>

        <section className="upload-section">
          <div className="section-label">Pipeline Control</div>
          <div className="frame-interval-row">
            <span className="frame-interval-label">Frame Skip (Fidelity Control):</span>
            <div className="frame-interval-options">
              {[1, 2, 5, 10, 15].map(v => (
                <button key={v} className={`frame-interval-btn ${frameInterval === v ? 'active' : ''}`} onClick={() => setFrameInterval(v)}>{v}</button>
              ))}
            </div>
          </div>

          <div id="upload-zone" className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}>
            <input id="file-input" type="file" onChange={e => handleFile(e.target.files[0])} />
            <div className="upload-icon">📁</div>
            <p className="upload-title">{dragging ? 'Drop it!' : 'Drag and drop media or click here'}</p>
          </div>

          {uploading && <div className="progress-bar-wrap"><div className="progress-bar-fill" style={{ width: `${progress}%` }} /></div>}
          {imageProcessing && <div className="pipeline-progress"><div className="pipeline-step">🔬 AI Inference (GPU) in progress…</div></div>}
          <PipelineProgress status={jobStatus} message={jobMsg} progress={jobProgress} result={jobResult} onOpenModal={() => setShowModal(true)} />
        </section>

        {/* Manual Data Recovery Link (specifically requested) */}
        {!jobId && (
          <div className="manual-recovery-banner">
            <span>Looking for a previous run?</span>
            <a href={`${API}/api/download/folder/dataset_20260324_230545`} download>Download dataset_20260324_230545.zip</a>
          </div>
        )}

        <section>
          <div className="section-label">Image Side-by-Side</div>
          <div className="comparison-grid">
            <MediaCard label="Original" src={origImage} type="image" />
            <MediaCard label="AI Plus" isProcessed={true} src={aiImage} type="image" labelUrl={aiImageLabel} />
          </div>
        </section>

        <section>
          <div className="section-label">Video Side-by-Side</div>
          <div className="comparison-grid">
            <MediaCard label="Original" src={origVideo} type="video" />
            <MediaCard label="H.264 Optimized" isProcessed={true} src={aiVideo} type="video" />
          </div>
        </section>
      </main>

      <footer className="footer">Drone Imagery Analysis for Crop Health &copy; {new Date().getFullYear()}</footer>

      <DownloadModal isOpen={showModal} onClose={() => setShowModal(false)} result={jobResult} />

      <div className="toast-container">{toasts.map(t => (<div key={t.id} className={`toast ${t.type}`}>{t.msg}</div>))}</div>
    </div>
  )
}
