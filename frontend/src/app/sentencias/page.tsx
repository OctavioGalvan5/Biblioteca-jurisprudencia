'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Search, Filter, FileText, Calendar, Building2, User, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { listSentencias, listJueces, Sentencia, Juez } from '@/lib/api';

const PER_PAGE = 12;

export default function BibliotecaPage() {
  const [sentencias, setSentencias] = useState<Sentencia[]>([]);
  const [total, setTotal] = useState(0);
  const [jueces, setJueces] = useState<Juez[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  const [q, setQ] = useState('');
  const [jurisdiccion, setJurisdiccion] = useState('');
  const [juezId, setJuezId] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const hasFilters = !!(jurisdiccion || juezId || fechaDesde || fechaHasta);

  const fetchSentencias = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSentencias({
        skip: page * PER_PAGE,
        limit: PER_PAGE,
        ...(q && { q }),
        ...(jurisdiccion && { jurisdiccion }),
        ...(juezId && { juez_id: parseInt(juezId) }),
        ...(fechaDesde && { fecha_desde: fechaDesde }),
        ...(fechaHasta && { fecha_hasta: fechaHasta }),
      });
      setSentencias(data.sentencias);
      setTotal(data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, q, jurisdiccion, juezId, fechaDesde, fechaHasta]);

  useEffect(() => {
    listJueces(true).then(setJueces).catch(() => {});
  }, []);

  useEffect(() => {
    setPage(0);
  }, [q, jurisdiccion, juezId, fechaDesde, fechaHasta]);

  useEffect(() => {
    fetchSentencias();
  }, [fetchSentencias]);

  const clearFilters = () => {
    setJurisdiccion('');
    setJuezId('');
    setFechaDesde('');
    setFechaHasta('');
  };

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-purple-950">Biblioteca de Jurisprudencia</h1>
        </div>
        <Link href="/cargar" className="btn-primary hidden sm:inline-flex items-center gap-2">
          + Cargar sentencia
        </Link>
      </div>

      {/* Búsqueda + filtros */}
      <div className="card p-4 mb-6 space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por carátula, expediente, órgano o resumen..."
              value={q}
              onChange={e => setQ(e.target.value)}
              className="input pl-9"
            />
            {q && (
              <button onClick={() => setQ('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowFilters(f => !f)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
              showFilters || hasFilters
                ? 'border-purple-500 bg-purple-50 text-purple-700'
                : 'border-gray-300 text-gray-600 hover:border-purple-400'
            }`}
          >
            <Filter className="h-4 w-4" />
            Filtros
            {hasFilters && (
              <span className="bg-purple-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {[jurisdiccion, juezId, fechaDesde, fechaHasta].filter(Boolean).length}
              </span>
            )}
          </button>
        </div>

        {showFilters && (
          <div className="border-t border-gray-100 pt-3 grid sm:grid-cols-4 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Jurisdicción</label>
              <select value={jurisdiccion} onChange={e => setJurisdiccion(e.target.value)} className="input">
                <option value="">Todas</option>
                <option value="federal">Federal</option>
                <option value="provincial">Provincial</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Juez</label>
              <select value={juezId} onChange={e => setJuezId(e.target.value)} className="input">
                <option value="">Todos</option>
                {jueces.map(j => (
                  <option key={j.id} value={j.id}>{j.nombre} {j.apellido}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Fecha desde</label>
              <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Fecha hasta</label>
              <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input" />
            </div>
            {hasFilters && (
              <div className="sm:col-span-4 flex justify-end">
                <button onClick={clearFilters} className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1">
                  <X className="h-3 w-3" /> Limpiar filtros
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Grid de resultados */}
      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-4" />
              <div className="space-y-2">
                <div className="h-3 bg-gray-100 rounded w-full" />
                <div className="h-3 bg-gray-100 rounded w-5/6" />
              </div>
            </div>
          ))}
        </div>
      ) : sentencias.length === 0 ? (
        <div className="card p-16 text-center">
          <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">No se encontraron sentencias</p>
          <p className="text-gray-400 text-sm mt-1">
            {q || hasFilters
              ? 'Probá con otros filtros o términos de búsqueda'
              : 'Cargá la primera sentencia para comenzar'}
          </p>
          {!q && !hasFilters && (
            <Link href="/cargar" className="btn-primary mt-5 inline-flex">+ Cargar sentencia</Link>
          )}
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sentencias.map(s => (
              <SentenciaCard key={s.id} sentencia={s} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => setPage(p => p - 1)}
                disabled={page === 0}
                className="p-2 rounded-lg border border-gray-300 hover:border-purple-400 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-gray-600">
                Página <span className="font-medium">{page + 1}</span> de <span className="font-medium">{totalPages}</span>
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg border border-gray-300 hover:border-purple-400 disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}

function SentenciaCard({ sentencia: s }: { sentencia: Sentencia }) {
  const fecha = s.fecha_sentencia
    ? new Date(s.fecha_sentencia + 'T00:00:00').toLocaleDateString('es-AR', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : null;

  return (
    <Link
      href={`/sentencias/${s.id}`}
      className="card p-5 flex flex-col hover:shadow-md hover:border-purple-200 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between mb-3">
        {s.jurisdiccion ? (
          <span className={s.jurisdiccion === 'federal' ? 'badge-federal' : 'badge-provincial'}>
            {s.jurisdiccion === 'federal' ? 'Federal' : 'Provincial'}
          </span>
        ) : <span />}
        {fecha && (
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {fecha}
          </span>
        )}
      </div>

      <h3 className="font-semibold text-purple-950 text-sm leading-snug mb-1 group-hover:text-purple-700 line-clamp-2">
        {s.caratula || 'Sin carátula'}
      </h3>

      {s.nro_expediente && (
        <p className="text-xs text-gray-400 mb-3 font-mono">{s.nro_expediente}</p>
      )}

      {s.resumen && (
        <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed mb-3">{s.resumen}</p>
      )}

      <div className="border-t border-gray-100 pt-3 mt-auto space-y-1.5">
        {s.organo && (
          <div className="flex items-start gap-1.5">
            <Building2 className="h-3.5 w-3.5 text-gray-400 mt-0.5 shrink-0" />
            <span className="text-xs text-gray-500 line-clamp-1">{s.organo}</span>
          </div>
        )}
        {s.jueces.length > 0 && (
          <div className="flex items-start gap-1.5">
            <User className="h-3.5 w-3.5 text-gray-400 mt-0.5 shrink-0" />
            <span className="text-xs text-gray-500 line-clamp-1">
              {s.jueces.map(j => `${j.nombre} ${j.apellido}`).join(' · ')}
            </span>
          </div>
        )}
      </div>

      {s.palabras_clave && s.palabras_clave.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {s.palabras_clave.slice(0, 3).map(k => (
            <span key={k} className="bg-purple-50 text-purple-600 text-xs px-2 py-0.5 rounded-full">{k}</span>
          ))}
          {s.palabras_clave.length > 3 && (
            <span className="text-gray-400 text-xs">+{s.palabras_clave.length - 3}</span>
          )}
        </div>
      )}
    </Link>
  );
}
