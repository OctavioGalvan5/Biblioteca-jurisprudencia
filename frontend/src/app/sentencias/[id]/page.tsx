'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Pencil, ExternalLink, Calendar, Building2,
  User, Tag, FileText, Hash, Loader2, Trash2
} from 'lucide-react';
import { getSentencia, deleteSentencia, Sentencia } from '@/lib/api';

export default function DetalleSentenciaPage() {
  const params = useParams();
  const router = useRouter();
  const id = parseInt(params.id as string);

  const [sentencia, setSentencia] = useState<Sentencia | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSentencia(id)
      .then(setSentencia)
      .catch(() => setError('No se pudo cargar la sentencia'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!confirm('¿Estás seguro de que querés eliminar esta sentencia? Esta acción no se puede deshacer.')) return;
    setDeleting(true);
    try {
      await deleteSentencia(id);
      router.push('/sentencias');
    } catch {
      alert('Error al eliminar la sentencia');
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (error || !sentencia) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 font-medium">{error || 'Sentencia no encontrada'}</p>
          <Link href="/sentencias" className="btn-primary mt-4 inline-flex">Volver a la biblioteca</Link>
        </div>
      </div>
    );
  }

  const fecha = sentencia.fecha_sentencia
    ? new Date(sentencia.fecha_sentencia + 'T00:00:00').toLocaleDateString('es-AR', {
        day: '2-digit', month: 'long', year: 'numeric',
      })
    : null;

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/sentencias" className="hover:text-purple-700 flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Biblioteca
        </Link>
        <span>/</span>
        <span className="text-gray-700 truncate max-w-xs">{sentencia.caratula || `Sentencia #${id}`}</span>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Columna principal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header card */}
          <div className="card p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="flex-1">
                {sentencia.jurisdiccion && (
                  <span className={`${sentencia.jurisdiccion === 'federal' ? 'badge-federal' : 'badge-provincial'} mb-3 inline-flex`}>
                    {sentencia.jurisdiccion === 'federal' ? 'Federal' : 'Provincial'}
                  </span>
                )}
                <h1 className="text-xl font-bold text-purple-950 leading-snug">
                  {sentencia.caratula || 'Sin carátula'}
                </h1>
                {sentencia.nro_expediente && (
                  <p className="text-sm text-gray-400 font-mono mt-1">{sentencia.nro_expediente}</p>
                )}
              </div>

              {/* Acciones */}
              <div className="flex gap-2 shrink-0">
                <Link
                  href={`/sentencias/${id}/edit`}
                  className="btn-secondary flex items-center gap-1.5"
                >
                  <Pencil className="h-3.5 w-3.5" /> Editar
                </Link>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="p-2.5 border border-red-200 text-red-500 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Metadatos rápidos */}
            <div className="grid sm:grid-cols-2 gap-3 text-sm">
              {fecha && (
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <span>{fecha}</span>
                </div>
              )}
              {sentencia.instancia && (
                <div className="flex items-center gap-2 text-gray-600">
                  <FileText className="h-4 w-4 text-gray-400" />
                  <span>{sentencia.instancia}</span>
                </div>
              )}
              {sentencia.organo && (
                <div className="flex items-start gap-2 text-gray-600 sm:col-span-2">
                  <Building2 className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
                  <span>{sentencia.organo}</span>
                </div>
              )}
            </div>
          </div>

          {/* Resumen */}
          {sentencia.resumen && (
            <div className="card p-6">
              <h2 className="font-semibold text-purple-950 mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4 text-purple-500" />
                Resumen
              </h2>
              <p className="text-gray-700 text-sm leading-relaxed">{sentencia.resumen}</p>
            </div>
          )}

          {/* Contenido completo (colapsable) */}
          {sentencia.contenido && <ContenidoCard contenido={sentencia.contenido} />}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Ver PDF */}
          <div className="card p-5">
            <h3 className="font-semibold text-purple-950 text-sm mb-3">Documento original</h3>
            <a
              href={sentencia.url_minio}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-700 text-white rounded-lg hover:bg-purple-800 transition-all duration-200 text-sm font-medium shadow-sm shadow-purple-200"
            >
              <ExternalLink className="h-4 w-4" />
              Abrir PDF
            </a>
          </div>

          {/* Jueces */}
          {sentencia.jueces.length > 0 && (
            <div className="card p-5">
              <h3 className="font-semibold text-purple-950 text-sm mb-3 flex items-center gap-2">
                <User className="h-4 w-4 text-purple-500" />
                Jueces
              </h3>
              <ul className="space-y-2">
                {sentencia.jueces.map(j => (
                  <li key={j.id} className="text-sm text-gray-700 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-purple-400 shrink-0" />
                    {j.nombre} {j.apellido}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Palabras clave */}
          {sentencia.palabras_clave && sentencia.palabras_clave.length > 0 && (
            <div className="card p-5">
              <h3 className="font-semibold text-purple-950 text-sm mb-3 flex items-center gap-2">
                <Tag className="h-4 w-4 text-purple-500" />
                Palabras clave
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {sentencia.palabras_clave.map(k => (
                  <span key={k} className="bg-purple-50 text-purple-700 text-xs px-2.5 py-1 rounded-full">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata sistema */}
          <div className="card p-5">
            <h3 className="font-semibold text-purple-950 text-sm mb-3">Información del sistema</h3>
            <dl className="space-y-2 text-xs text-gray-500">
              <div>
                <dt className="font-medium text-gray-600">Cargada</dt>
                <dd>{new Date(sentencia.created_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })}</dd>
              </div>
              {sentencia.updated_at !== sentencia.created_at && (
                <div>
                  <dt className="font-medium text-gray-600">Última edición</dt>
                  <dd>{new Date(sentencia.updated_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </main>
  );
}

function ContenidoCard({ contenido }: { contenido: string }) {
  const [expanded, setExpanded] = useState(false);
  const preview = contenido.slice(0, 600);
  const isLong = contenido.length > 600;

  return (
    <div className="card p-6">
      <h2 className="font-semibold text-purple-950 mb-3 flex items-center gap-2">
        <Hash className="h-4 w-4 text-purple-500" />
        Texto completo
      </h2>
      <div className="relative">
        <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap font-mono text-xs">
          {expanded ? contenido : preview}
          {!expanded && isLong && '...'}
        </p>
        {!expanded && isLong && (
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent" />
        )}
      </div>
      {isLong && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="mt-3 text-purple-600 hover:text-purple-800 text-sm font-medium"
        >
          {expanded ? 'Ver menos' : 'Ver texto completo'}
        </button>
      )}
    </div>
  );
}
