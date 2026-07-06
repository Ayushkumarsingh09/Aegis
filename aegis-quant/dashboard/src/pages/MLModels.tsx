import { useCallback, useEffect, useRef, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import {
  getSymbols, startTraining, getTrainingStatus, listMLModels, getMLModel,
  deleteMLModel, predictMLModel, compareMLModels,
  MLJobStatus, MLModelEntry, MLTrainResult, MLEvaluation, MLPrediction,
} from '../api'

const MODEL_OPTIONS = [
  { value: 'random_forest', label: 'Random Forest' },
  { value: 'logistic_regression', label: 'Logistic Regression' },
  { value: 'xgboost', label: 'XGBoost' },
  { value: 'lightgbm', label: 'LightGBM' },
  { value: 'catboost', label: 'CatBoost' },
]

export default function MLModels() {
  const [symbol, setSymbol] = useState('BTC-USD')
  const [model, setModel] = useState('random_forest')
  const [horizon, setHorizon] = useState(5)
  const [symbols, setSymbols] = useState<string[]>([])
  const [job, setJob] = useState<MLJobStatus | null>(null)
  const [result, setResult] = useState<MLTrainResult | null>(null)
  const [error, setError] = useState('')
  const [models, setModels] = useState<MLModelEntry[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [comparison, setComparison] = useState<MLModelEntry[] | null>(null)
  const [predictions, setPredictions] = useState<{ modelId: string; rows: MLPrediction[] } | null>(null)
  const pollRef = useRef<number | null>(null)

  const refreshModels = useCallback(() => {
    listMLModels().then(r => setModels(r.models)).catch(() => setModels([]))
  }, [])

  useEffect(() => {
    getSymbols().then(s => setSymbols(s.symbols.length ? s.symbols : ['BTC-USD'])).catch(() => setSymbols(['BTC-USD']))
    refreshModels()
    return () => { if (pollRef.current) window.clearInterval(pollRef.current) }
  }, [refreshModels])

  const train = async () => {
    setError(''); setResult(null); setJob(null); setPredictions(null)
    try {
      const { job_id } = await startTraining(symbol, model, horizon)
      pollRef.current = window.setInterval(async () => {
        try {
          const status = await getTrainingStatus(job_id)
          setJob(status)
          if (status.status === 'completed' || status.status === 'failed') {
            if (pollRef.current) window.clearInterval(pollRef.current)
            if (status.status === 'completed' && status.result) {
              setResult(status.result)
              refreshModels()
            }
            if (status.status === 'failed') setError(status.error || 'Training failed')
          }
        } catch { /* transient poll error; keep polling */ }
      }, 700)
    } catch (e) {
      setError(String(e))
    }
  }

  const viewModel = async (id: string) => {
    setError('')
    try {
      const entry = await getMLModel(id)
      setResult({
        model_id: entry.model_id, model: entry.model_name, symbol: entry.symbol,
        metrics: entry.metrics, evaluation: entry.evaluation, run_id: entry.mlflow_run_id,
      })
      setPredictions(null)
    } catch (e) { setError(String(e)) }
  }

  const predict = async (id: string) => {
    setError('')
    try {
      const r = await predictMLModel(id, 20)
      setPredictions({ modelId: id, rows: r.predictions })
    } catch (e) { setError(String(e)) }
  }

  const remove = async (id: string) => {
    await deleteMLModel(id).catch(() => {})
    setSelectedIds(ids => ids.filter(x => x !== id))
    if (result?.model_id === id) setResult(null)
    refreshModels()
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(ids => ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id])
  }

  const runCompare = async () => {
    if (selectedIds.length < 2) return
    const r = await compareMLModels(selectedIds)
    setComparison(r.comparison)
  }

  const training = job !== null && (job.status === 'pending' || job.status === 'running')

  return (
    <div className="page fade-in">
      <h2>ML Models</h2>

      <div className="card">
        <h3>Train New Model</h3>
        <div className="form-row" style={{ marginTop: 12 }}>
          <select value={symbol} onChange={e => setSymbol(e.target.value)} disabled={training}>
            {symbols.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={model} onChange={e => setModel(e.target.value)} disabled={training}>
            {MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          <label className="muted">Horizon
            <input type="number" min={1} max={50} value={horizon} disabled={training}
              onChange={e => setHorizon(+e.target.value)} style={{ width: 64, marginLeft: 8 }} />
          </label>
          <button className="btn" onClick={train} disabled={training}>
            {training ? 'Training…' : 'Train Model'}
          </button>
        </div>
        {job && training && (
          <div style={{ marginTop: 8 }}>
            <div className="progress-track"><div className="progress-fill" style={{ width: `${job.progress * 100}%` }} /></div>
            <p className="muted">{job.stage} — {(job.progress * 100).toFixed(0)}%
              {job.fold_scores.length > 0 && ` · fold accuracy: ${job.fold_scores.map(s => s.toFixed(3)).join(', ')}`}
            </p>
          </div>
        )}
        {error && <p className="negative" style={{ marginTop: 8 }}>{error}</p>}
      </div>

      {result && <TrainResultView result={result} />}

      {predictions && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Predictions — {predictions.modelId}</h3>
          <table className="data-table">
            <thead><tr><th>Timestamp</th><th>Close</th><th>Signal</th><th>P(up)</th><th>Actual</th><th>Hit</th></tr></thead>
            <tbody>
              {predictions.rows.map((p, i) => (
                <tr key={i}>
                  <td>{p.timestamp.slice(0, 16)}</td>
                  <td>{p.close.toFixed(2)}</td>
                  <td><span className={`badge ${p.prediction === 1 ? 'green' : 'red'}`}>{p.prediction === 1 ? 'UP' : 'DOWN'}</span></td>
                  <td>{p.probability_up !== null ? p.probability_up.toFixed(3) : '—'}</td>
                  <td>{p.actual === 1 ? 'UP' : 'DOWN'}</td>
                  <td>{p.prediction === p.actual ? <span className="positive">✓</span> : <span className="negative">✗</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>Model Registry ({models.length})</h3>
          <button className="btn btn-sm" onClick={runCompare} disabled={selectedIds.length < 2}>
            Compare Selected ({selectedIds.length})
          </button>
        </div>
        {models.length === 0 && <p className="muted" style={{ marginTop: 8 }}>No models trained yet. Train one above.</p>}
        {models.length > 0 && (
          <table className="data-table">
            <thead><tr><th></th><th>ID</th><th>Model</th><th>Symbol</th><th>Test Acc</th><th>ROC AUC</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {models.map(m => (
                <tr key={m.model_id}>
                  <td><input type="checkbox" checked={selectedIds.includes(m.model_id)} onChange={() => toggleSelect(m.model_id)} /></td>
                  <td>{m.model_id}</td>
                  <td>{m.model_name}</td>
                  <td>{m.symbol}</td>
                  <td>{m.metrics.test_accuracy?.toFixed(3) ?? '—'}</td>
                  <td>{m.metrics.roc_auc?.toFixed(3) ?? '—'}</td>
                  <td>{m.created_at.slice(0, 16).replace('T', ' ')}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="btn btn-sm btn-ghost" onClick={() => viewModel(m.model_id)}>View</button>{' '}
                    <button className="btn btn-sm btn-ghost" onClick={() => predict(m.model_id)}>Predict</button>{' '}
                    <a className="btn btn-sm btn-ghost" href={`/api/v1/ml/models/${m.model_id}/download`} download>Download</a>{' '}
                    <button className="btn btn-sm btn-ghost negative" onClick={() => remove(m.model_id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {comparison && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Model Comparison</h3>
          <table className="data-table">
            <thead><tr><th>ID</th><th>Model</th><th>Symbol</th><th>CV Acc</th><th>Test Acc</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC AUC</th></tr></thead>
            <tbody>
              {comparison.map(c => (
                <tr key={c.model_id}>
                  <td>{c.model_id}</td>
                  <td>{c.model_name}</td>
                  <td>{c.symbol}</td>
                  <td>{c.metrics.cv_accuracy?.toFixed(3) ?? '—'}</td>
                  <td>{c.metrics.test_accuracy?.toFixed(3) ?? '—'}</td>
                  <td>{c.metrics.precision?.toFixed(3) ?? '—'}</td>
                  <td>{c.metrics.recall?.toFixed(3) ?? '—'}</td>
                  <td>{c.metrics.f1?.toFixed(3) ?? '—'}</td>
                  <td>{c.metrics.roc_auc?.toFixed(3) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function TrainResultView({ result }: { result: MLTrainResult }) {
  const ev: MLEvaluation = result.evaluation
  const rocData = ev.roc_curve
    ? ev.roc_curve.fpr.map((f, i) => ({ fpr: f, tpr: ev.roc_curve!.tpr[i] }))
    : []
  const impEntries = Object.entries(ev.feature_importance || {}).slice(0, 12)
  const maxImp = impEntries.length ? Math.max(...impEntries.map(([, v]) => v)) : 1
  const cm = ev.confusion_matrix

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3>Evaluation — {result.model} / {result.symbol} <span className="badge blue">{result.model_id}</span></h3>
      {result.run_id && <p className="muted">MLflow run: {result.run_id}</p>}

      <div className="metric-grid">
        {Object.entries(result.metrics).map(([k, v]) => (
          <div key={k} className="metric"><div className="label">{k}</div><div className="val">{v.toFixed(4)}</div></div>
        ))}
        <div className="metric"><div className="label">train / test</div><div className="val">{ev.n_train} / {ev.n_test}</div></div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20, marginTop: 20 }}>
        {rocData.length > 0 && (
          <div>
            <h3>ROC Curve</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={rocData}>
                <XAxis dataKey="fpr" type="number" domain={[0, 1]} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <YAxis type="number" domain={[0, 1]} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#6b7a94" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="tpr" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {cm && cm.length === 2 && (
          <div>
            <h3>Confusion Matrix</h3>
            <p className="muted">rows = actual (down/up), cols = predicted</p>
            <div className="confusion">
              <div className="cm-hit">{cm[0][0]}</div>
              <div className="cm-miss">{cm[0][1]}</div>
              <div className="cm-miss">{cm[1][0]}</div>
              <div className="cm-hit">{cm[1][1]}</div>
            </div>
          </div>
        )}

        {impEntries.length > 0 && (
          <div>
            <h3>Feature Importance</h3>
            <div style={{ marginTop: 8 }}>
              {impEntries.map(([name, val]) => (
                <div key={name} className="imp-row">
                  <span className="imp-name" title={name}>{name}</span>
                  <div className="imp-bar-track"><div className="imp-bar" style={{ width: `${(val / maxImp) * 100}%` }} /></div>
                  <span className="imp-val">{val.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {ev.cv_fold_scores?.length > 0 && (
          <div>
            <h3>CV Fold Accuracy</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={ev.cv_fold_scores.map((s, i) => ({ fold: i + 1, acc: s }))}>
                <XAxis dataKey="fold" tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <YAxis domain={[0, 1]} tick={{ fill: '#6b7a94', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#161e2e', border: '1px solid #243044' }} />
                <Line type="monotone" dataKey="acc" stroke="#22c55e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
