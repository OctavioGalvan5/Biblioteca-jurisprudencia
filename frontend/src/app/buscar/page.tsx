'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';
import {
  Search, MessageCircle, SlidersHorizontal, ExternalLink,
  Loader2, AlertCircle, ChevronDown, ChevronUp, Scale
} from 'lucide-react';
import {
  chatBuscar, chatPreguntar, SentenciaResult, isAuthenticated, ChatFilters,
} from '@/lib/api';

type Mode = 'buscar' | 'preguntar';

export default function BuscarPage() {
  const [mode, setMode] = useState<Mode>('buscar');
  const [input, setInput] = useState('');
  const [filters, setFilters] = useState<ChatFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Buscar state
  const [resultados, setResultados] = useState<SentenciaResult[] | null>(null);

  // Preguntar state
  const [respuesta, setRespuesta] = useState('');
  const [fuentes, setFuentes] = useState<SentenciaResult[]>([]);

  const loggedIn = typeof window !== 'undefined' ? isAuthenticated() : false;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setLoading(true);
    setError('');
    setResultados(null);
    setRespuesta('');
    setFuentes([]);

    try {
      if (mode === 'buscar') {
        const res = await chatBuscar(input, filters);
        setResultados(res);
      } else {
        const res = await chatPreguntar(input, filters);
        setRespuesta(res.respuesta);
        setFuentes(res.fuentes);
      }
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('La función "Preguntar" requiere iniciar sesión.');
      } else {
        setError(err?.response?.data?.detail || 'Error al procesar la consulta.');
      }
    } finally {
      setLoading(false);
    }
  };

  const placeholder = mode === 'buscar'
    ? 'Ej: reajuste de haber previsional, matrimonio igualitario, despido sin causa…'
    : 'Ej: ¿Qué criterio usaron los tribunales para calcular el reajuste de haberes?';

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center bg-purple-100 rounded-full p-3 mb-4">
          <Scale className="h-7 w-7 text-purple-700" />
        </div>
        <h1 className="text-3xl font-bold text-purple-950 mb-2">Buscar en la Biblioteca</h1>
        <p className="text-gray-500 text-sm max-w-lg mx-auto">
          Búsqueda semántica por tema o concepto. No hace falta usar las palabras exactas.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit mx-auto">
        {([
          ['buscar', 'Buscar sentencias', Search],
          ['preguntar', 'Hacer una pregunta', MessageCircle],
        ] as const).map(([value, label, Icon]) => (
          <button
            key={value}
            onClick={() => { setMode(value); setResultados(null); setRespuesta(''); setFuentes([]); setError(''); }}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === value ? 'bg-white text-purple-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {mode === 'preguntar' && !loggedIn && (
        <div className="mb-4 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0" />
          La función "Preguntar" requiere{' '}
          <Link href="/login" className="underline font-medium">iniciar sesión</Link>.
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            className="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex items-center gap-2 bg-purple-700 hover:bg-purple-800 disabled:opacity-50 text-white font-medium px-5 py-3 rounded-xl text-sm transition-colors"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            {mode === 'buscar' ? 'Buscar' : 'Preguntar'}
          </button>
        </div>

        {/* Filtros */}
        <div>
          <button
            type="button"
            onClick={() => setShowFilters((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filtros
            {showFilters ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          {showFilters && (
            <div className="flex flex-wrap gap-3 mt-3 p-4 bg-gray-50 rounded-xl border border-gray-100">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">Jurisdicción</label>
                <select
                  value={filters.jurisdiccion || ''}
                  onChange={(e) => setFilters((f) => ({ ...f, jurisdiccion: e.target.value || undefined }))}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-400"
                >
                  <option value="">Todas</option>
                  <option value="federal">Federal</option>
                  <option value="provincial">Provincial</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">Desde</label>
                <input
                  type="date"
                  value={filters.fecha_desde || ''}
                  onChange={(e) => setFilters((f) => ({ ...f, fecha_desde: e.target.value || undefined }))}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-400"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500 font-medium">Hasta</label>
                <input
                  type="date"
                  value={filters.fecha_hasta || ''}
                  onChange={(e) => setFilters((f) => ({ ...f, fecha_hasta: e.target.value || undefined }))}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-400"
                />
              </div>
              {(filters.jurisdiccion || filters.fecha_desde || filters.fecha_hasta) && (
                <button
                  type="button"
                  onClick={() => setFilters({})}
                  className="self-end text-xs text-red-500 hover:text-red-700"
                >
                  Limpiar filtros
                </button>
              )}
            </div>
          )}
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="mt-4 flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-xl px-4 py-3 border border-red-100">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Resultados: Buscar */}
      {resultados !== null && (
        <div className="mt-8">
          <p className="text-sm text-gray-500 mb-4">
            {resultados.length === 0
              ? 'No se encontraron sentencias relevantes para esa búsqueda.'
              : `${resultados.length} sentencia${resultados.length !== 1 ? 's' : ''} encontrada${resultados.length !== 1 ? 's' : ''}`}
          </p>
          <div className="space-y-3">
            {resultados.map((s) => <SentenciaCard key={s.id} s={s} />)}
          </div>
        </div>
      )}

      {/* Resultados: Preguntar */}
      {respuesta && (
        <div className="mt-8 space-y-6">
          {/* Respuesta IA */}
          <div className="bg-white rounded-2xl border border-purple-100 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle className="h-4 w-4 text-purple-600" />
              <span className="text-sm font-semibold text-purple-900">Respuesta</span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{respuesta}</p>
          </div>

          {/* Fuentes */}
          {fuentes.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
                Fuentes consultadas
              </p>
              <div className="space-y-3">
                {fuentes.map((s) => <SentenciaCard key={s.id} s={s} />)}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function SentenciaCard({ s }: { s: SentenciaResult }) {
  const pct = Math.round(s.similitud * 100);
  const colorBar = pct >= 80 ? 'bg-green-400' : pct >= 60 ? 'bg-yellow-400' : 'bg-gray-300';

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 hover:border-purple-200 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <Link
            href={`/sentencias/${s.id}`}
            className="font-semibold text-purple-900 hover:text-purple-700 text-sm leading-snug line-clamp-2"
          >
            {s.caratula || 'Sin carátula'}
          </Link>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5 text-xs text-gray-500">
            {s.organo && <span>{s.organo}</span>}
            {s.fecha_sentencia && <span>{new Date(s.fecha_sentencia + 'T00:00:00').toLocaleDateString('es-AR')}</span>}
            {s.jurisdiccion && (
              <span className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${
                s.jurisdiccion === 'federal' ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'
              }`}>
                {s.jurisdiccion}
              </span>
            )}
          </div>
          {s.resumen && (
            <p className="text-xs text-gray-500 mt-2 line-clamp-3 leading-relaxed">{s.resumen}</p>
          )}
          {s.jueces.length > 0 && (
            <p className="text-xs text-gray-400 mt-1.5">
              {s.jueces.map((j) => `${j.nombre} ${j.apellido}`).join(' · ')}
            </p>
          )}
        </div>

        <div className="shrink-0 flex flex-col items-end gap-2">
          {/* Barra de relevancia */}
          <div className="flex items-center gap-1.5" title={`Relevancia: ${pct}%`}>
            <div className="w-16 h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div className={`h-full rounded-full ${colorBar}`} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[11px] text-gray-400">{pct}%</span>
          </div>
          <Link
            href={`/sentencias/${s.id}`}
            className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-800 font-medium"
          >
            Ver <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
