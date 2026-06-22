'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { Save, ExternalLink, Loader2, ArrowLeft, X, Search } from 'lucide-react';
import { 
  getSentencia, updateSentencia, listJueces, listInstancias, listOrganos,
  Sentencia, Juez, Instancia, Organo 
} from '@/lib/api';

export default function EditSentenciaPage() {
  const params = useParams();
  const router = useRouter();
  const id = parseInt(params.id as string);

  const [sentencia, setSentencia] = useState<Sentencia | null>(null);
  const [todosFirmantes, setTodosFirmantes] = useState<Juez[]>([]);
  const [firmantesSeleccionados, setFirmantesSeleccionados] = useState<Juez[]>([]);
  const [busquedaFirmante, setBusquedaFirmante] = useState('');
  const [instancias, setInstancias] = useState<Instancia[]>([]);
  const [organos, setOrganos] = useState<Organo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, setValue } = useForm();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [sentenciaData, juecesData, instanciasData, organosData] = await Promise.all([
          getSentencia(id),
          listJueces(true),
          listInstancias(),
          listOrganos(),
        ]);
        setSentencia(sentenciaData);
        setTodosFirmantes(juecesData);
        setFirmantesSeleccionados(sentenciaData.jueces);
        setInstancias(instanciasData);
        setOrganos(organosData);

        setValue('caratula', sentenciaData.caratula || '');
        setValue('nro_expediente', sentenciaData.nro_expediente || '');
        setValue('fecha_sentencia', sentenciaData.fecha_sentencia || '');
        setValue('instancia', sentenciaData.instancia || '');
        setValue('organo', sentenciaData.organo || '');
        setValue('jurisdiccion', sentenciaData.jurisdiccion || '');
        setValue('palabras_clave', sentenciaData.palabras_clave?.join(', ') || '');
        setValue('resumen', sentenciaData.resumen || '');
      } catch {
        setError('Error al cargar la sentencia');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id, setValue]);

  const firmantesDisponibles = todosFirmantes.filter(f =>
    !firmantesSeleccionados.some(s => s.id === f.id) &&
    `${f.nombre} ${f.apellido}`.toLowerCase().includes(busquedaFirmante.toLowerCase())
  );

  function agregarFirmante(f: Juez) {
    setFirmantesSeleccionados(prev => [...prev, f]);
    setBusquedaFirmante('');
  }

  function quitarFirmante(id: number) {
    setFirmantesSeleccionados(prev => prev.filter(f => f.id !== id));
  }

  const onSubmit = async (data: any) => {
    setSaving(true);
    setError(null);
    try {
      const palabrasClave = data.palabras_clave
        ? data.palabras_clave.split(',').map((k: string) => k.trim()).filter(Boolean)
        : [];

      await updateSentencia(id, {
        caratula: data.caratula || null,
        nro_expediente: data.nro_expediente || null,
        fecha_sentencia: data.fecha_sentencia || null,
        instancia: data.instancia || null,
        organo: data.organo || null,
        jurisdiccion: data.jurisdiccion || null,
        palabras_clave: palabrasClave,
        resumen: data.resumen || null,
        jueces_ids: firmantesSeleccionados.map(f => f.id),
      });
      router.push(`/sentencias/${id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar la sentencia');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (error && !sentencia) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-center">
        <div>
          <p className="text-red-600 font-medium">{error}</p>
          <Link href="/sentencias" className="btn-primary mt-4 inline-flex">Volver a la biblioteca</Link>
        </div>
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href={`/sentencias/${id}`} className="hover:text-purple-700 flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Ver sentencia
        </Link>
        <span>/</span>
        <span className="text-gray-700">Editar</span>
      </div>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-purple-950">Editar Sentencia</h1>
        <p className="text-gray-500 text-sm mt-1">Revisá y corregí los datos extraídos automáticamente por la IA.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Datos principales */}
        <div className="card p-6">
          <h2 className="font-semibold text-purple-950 mb-5 pb-3 border-b border-gray-100">Datos de la sentencia</h2>
          <div className="grid md:grid-cols-2 gap-5">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Carátula</label>
              <input type="text" {...register('caratula')} className="input"
                placeholder="Ej: LASCURAIN, IGNACIO ROQUE c/ ANSES s/ EJECUCIÓN PREVISIONAL" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Nº de Expediente</label>
              <input type="text" {...register('nro_expediente')} className="input" placeholder="Ej: FRO 23011341/2010" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Fecha de Sentencia</label>
              <input type="date" {...register('fecha_sentencia')} className="input" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Instancia</label>
              <input type="text" {...register('instancia')} className="input" placeholder="Ej: Segunda Instancia" list="instancias-list" />
              <datalist id="instancias-list">
                {instancias.map(i => (
                  <option key={i.id} value={i.nombre} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Jurisdicción</label>
              <select {...register('jurisdiccion')} className="input">
                <option value="">Seleccionar...</option>
                <option value="federal">Federal</option>
                <option value="provincial">Provincial</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Órgano</label>
              <input type="text" {...register('organo')} className="input" placeholder="Ej: CAMARA FEDERAL DE ROSARIO - SALA A" list="organos-list" />
              <datalist id="organos-list">
                {organos.map(o => (
                  <option key={o.id} value={o.nombre} />
                ))}
              </datalist>
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Palabras Clave (separadas por comas)</label>
              <input type="text" {...register('palabras_clave')} className="input" placeholder="Ej: ejecución, previsional, ANSES, honorarios" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Resumen</label>
              <textarea {...register('resumen')} rows={4} className="input resize-none"
                placeholder="Resumen de la sentencia..." />
            </div>
          </div>
        </div>

        {/* Firmantes */}
        <div className="card p-6">
          <h2 className="font-semibold text-purple-950 mb-5 pb-3 border-b border-gray-100">Firmantes</h2>

          {/* Seleccionados */}
          <div className="flex flex-wrap gap-2 mb-4 min-h-[2rem]">
            {firmantesSeleccionados.length === 0 && (
              <p className="text-sm text-gray-400 italic">Sin firmantes asignados.</p>
            )}
            {firmantesSeleccionados.map(f => (
              <span key={f.id} className="flex items-center gap-1.5 bg-purple-100 text-purple-800 text-sm px-3 py-1 rounded-full">
                {f.nombre} {f.apellido}
                <button type="button" onClick={() => quitarFirmante(f.id)} className="hover:text-purple-950">
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
          </div>

          {/* Buscador */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={busquedaFirmante}
              onChange={e => setBusquedaFirmante(e.target.value)}
              placeholder="Buscar y agregar firmante..."
              className="input pl-9 text-sm"
            />
          </div>
          {busquedaFirmante && (
            <div className="mt-1 border border-gray-200 rounded-lg overflow-hidden shadow-sm max-h-48 overflow-y-auto">
              {firmantesDisponibles.length === 0 ? (
                <p className="text-sm text-gray-400 px-3 py-2">Sin resultados.</p>
              ) : (
                firmantesDisponibles.slice(0, 10).map(f => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => agregarFirmante(f)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-purple-50 hover:text-purple-800 transition-colors border-b border-gray-100 last:border-0"
                  >
                    {f.nombre} {f.apellido}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Ver PDF */}
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-purple-800">Archivo original</p>
            <p className="text-xs text-purple-500 mt-0.5">Archivo PDF original cargado</p>
          </div>
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/sentencias/${id}/pdf`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-purple-700 text-white text-sm rounded-lg hover:bg-purple-800 transition-all duration-200 font-medium shadow-sm shadow-purple-200"
          >
            <ExternalLink className="h-4 w-4" />
            Ver PDF
          </a>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Botones */}
        <div className="flex gap-3 justify-end pb-4">
          <Link href={`/sentencias/${id}`} className="btn-secondary">
            Cancelar
          </Link>
          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </form>
    </main>
  );
}
