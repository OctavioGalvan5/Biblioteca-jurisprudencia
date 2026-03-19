'use client';

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, CheckCircle2, AlertCircle, Loader2, ArrowRight,
  UserCheck, UserPlus, UserX, ChevronDown,
} from 'lucide-react';
import {
  uploadSentencia, confirmarJueces,
  listJueces, UploadResponse, JuezPendiente, DecisionJuez, Juez,
} from '@/lib/api';

interface UploadSentenciaProps {
  onSuccess?: (data: UploadResponse) => void;
}

type Stage = 'idle' | 'uploading' | 'reviewing' | 'confirming';

interface JuezDecision {
  nombre_extraido: string;
  tipo: 'crear' | 'vincular' | 'ignorar';
  nombre: string;
  apellido: string;
  juez_id: number | null;
  // Datos originales de la sugerencia para mostrar en UI
  accion_original: string;
  juez_sugerido: Juez | null;
  similitud: number | null;
}

const STEPS = [
  'Calculando hash del documento...',
  'Subiendo PDF a almacenamiento...',
  'Extrayendo texto del PDF...',
  'Analizando con IA...',
  'Detectando jueces firmantes...',
  'Guardando en base de datos...',
];

function parsearNombreApellido(nombreCompleto: string): { nombre: string; apellido: string } {
  const partes = nombreCompleto.trim().split(' ');
  const apellido = partes[partes.length - 1] ?? '';
  const nombre = partes.slice(0, -1).join(' ');
  return { nombre, apellido };
}

function initDecisiones(pendientes: JuezPendiente[]): JuezDecision[] {
  return pendientes.map((p) => {
    const { nombre, apellido } = parsearNombreApellido(p.nombre_extraido);
    const tipo: 'crear' | 'vincular' | 'ignorar' =
      p.accion === 'nuevo' ? 'crear'
        : p.juez_sugerido ? 'vincular'
        : 'crear';
    return {
      nombre_extraido: p.nombre_extraido,
      tipo,
      nombre,
      apellido,
      juez_id: p.juez_sugerido?.id ?? null,
      accion_original: p.accion,
      juez_sugerido: p.juez_sugerido,
      similitud: p.similitud,
    };
  });
}

export default function UploadSentencia({ onSuccess }: UploadSentenciaProps) {
  const [stage, setStage] = useState<Stage>('idle');
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [decisiones, setDecisiones] = useState<JuezDecision[]>([]);
  const [todosJueces, setTodosJueces] = useState<Juez[]>([]);

  // Cargar lista completa de jueces cuando entra en revisión
  useEffect(() => {
    if (stage === 'reviewing') {
      listJueces(true).then(setTodosJueces).catch(() => setTodosJueces([]));
    }
  }, [stage]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      setError('El archivo debe ser un PDF');
      return;
    }

    setFileName(file.name);
    setStage('uploading');
    setError(null);
    setUploadResult(null);
    setStep(0);
    setProgress(0);

    const stepInterval = setInterval(() => {
      setStep(s => {
        const next = s + 1;
        setProgress(Math.round((next / STEPS.length) * 90));
        if (next >= STEPS.length - 1) clearInterval(stepInterval);
        return Math.min(next, STEPS.length - 1);
      });
    }, 700);

    try {
      const response = await uploadSentencia(file);
      clearInterval(stepInterval);
      setProgress(100);
      setStep(STEPS.length - 1);
      setUploadResult(response);

      if (response.jueces_pendientes && response.jueces_pendientes.length > 0) {
        setDecisiones(initDecisiones(response.jueces_pendientes));
        setStage('reviewing');
      } else {
        // Sin jueces pendientes: completar directamente
        if (onSuccess) onSuccess(response);
      }
    } catch (err: any) {
      clearInterval(stepInterval);
      const msg = err.response?.data?.detail || 'Error al procesar la sentencia.';
      setError(msg.includes('ya existe') ? 'Esta sentencia ya fue cargada anteriormente en el sistema.' : msg);
      setProgress(0);
      setStage('idle');
    }
  }, [onSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: stage === 'uploading' || stage === 'reviewing' || stage === 'confirming',
  });

  const handleConfirmarJueces = async () => {
    if (!uploadResult) return;
    setStage('confirming');
    setError(null);
    try {
      const payload: DecisionJuez[] = decisiones.map(d => ({
        nombre_extraido: d.nombre_extraido,
        tipo: d.tipo,
        juez_id: d.tipo === 'vincular' ? (d.juez_id ?? undefined) : undefined,
        nombre: d.tipo === 'crear' ? d.nombre : undefined,
        apellido: d.tipo === 'crear' ? d.apellido : undefined,
      }));
      await confirmarJueces(uploadResult.sentencia_id, payload);
      if (onSuccess) onSuccess(uploadResult);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error al confirmar los jueces.';
      setError(msg);
      setStage('reviewing');
    }
  };

  const updateDecision = (idx: number, patch: Partial<JuezDecision>) => {
    setDecisiones(prev => prev.map((d, i) => i === idx ? { ...d, ...patch } : d));
  };

  // ── Render ──────────────────────────────────────────────────────────────

  const isUploading = stage === 'uploading';
  const isReviewing = stage === 'reviewing';
  const isConfirming = stage === 'confirming';

  return (
    <div className="w-full space-y-4">

      {/* Drop zone (solo cuando idle o error) */}
      {(stage === 'idle' || (stage === 'uploading')) && (
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
            transition-all duration-200
            ${isDragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50/50'}
            ${isUploading ? 'opacity-60 pointer-events-none' : ''}
          `}
        >
          <input {...getInputProps()} />

          {isUploading ? (
            <div className="space-y-5">
              <Loader2 className="h-12 w-12 text-purple-600 animate-spin mx-auto" />
              <div className="max-w-sm mx-auto">
                <p className="text-purple-800 font-medium text-sm mb-3">{STEPS[step]}</p>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-purple-600 h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-gray-400 text-xs mt-2">{progress}%</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
                <Upload className="h-8 w-8 text-purple-600" />
              </div>
              <div>
                <p className="text-purple-900 font-semibold">
                  {isDragActive ? 'Suelta el PDF aquí' : 'Arrastrá el PDF o hacé click para seleccionar'}
                </p>
                <p className="text-gray-400 text-sm mt-1">Solo archivos PDF · Tamaño máximo 50 MB</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800 text-sm">No se pudo completar la operación</p>
            <p className="text-red-600 text-sm mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Revisión de jueces */}
      {(isReviewing || isConfirming) && uploadResult && (
        <div className="border border-purple-200 rounded-xl overflow-hidden">
          {/* Header */}
          <div className="bg-purple-50 px-5 py-4 flex items-center gap-3 border-b border-purple-200">
            <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-purple-900 text-sm">Sentencia subida — revisá los jueces detectados</p>
              {fileName && <p className="text-purple-500 text-xs mt-0.5">{fileName}</p>}
            </div>
          </div>

          {/* Info sentencia */}
          {uploadResult.extracted_data?.caratula && (
            <div className="px-5 py-3 bg-white border-b border-gray-100 text-xs text-gray-600">
              <span className="font-medium">Carátula:</span> {uploadResult.extracted_data.caratula}
              {uploadResult.extracted_data.organo && (
                <> · <span className="font-medium">Órgano:</span> {uploadResult.extracted_data.organo}</>
              )}
            </div>
          )}

          {/* Lista de jueces */}
          <div className="divide-y divide-gray-100">
            {decisiones.map((d, idx) => (
              <JuezRevisionRow
                key={idx}
                decision={d}
                todosJueces={todosJueces}
                disabled={isConfirming}
                onChange={patch => updateDecision(idx, patch)}
              />
            ))}
          </div>

          {/* Footer con botón confirmar */}
          <div className="px-5 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between gap-4">
            <p className="text-xs text-gray-500">
              Revisá que cada juez esté correctamente identificado antes de continuar.
            </p>
            <button
              onClick={handleConfirmarJueces}
              disabled={isConfirming}
              className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {isConfirming ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Confirmando...</>
              ) : (
                <><ArrowRight className="h-4 w-4" /> Confirmar y continuar</>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Subcomponente fila de juez ──────────────────────────────────────────────

interface JuezRevisionRowProps {
  decision: JuezDecision;
  todosJueces: Juez[];
  disabled: boolean;
  onChange: (patch: Partial<JuezDecision>) => void;
}

function JuezRevisionRow({ decision: d, todosJueces, disabled, onChange }: JuezRevisionRowProps) {
  const badgeColor = {
    vinculado: 'bg-green-100 text-green-700',
    sugerencia: 'bg-yellow-100 text-yellow-700',
    nuevo: 'bg-blue-100 text-blue-700',
  }[d.accion_original] ?? 'bg-gray-100 text-gray-600';

  const badgeLabel = {
    vinculado: 'Encontrado en BD',
    sugerencia: 'Posible coincidencia',
    nuevo: 'No encontrado',
  }[d.accion_original] ?? '';

  return (
    <div className="px-5 py-4 bg-white space-y-3">
      {/* Nombre extraído + badge */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-mono text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
          {d.nombre_extraido}
        </span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badgeColor}`}>
          {badgeLabel}
        </span>
        {d.similitud !== null && d.accion_original === 'sugerencia' && (
          <span className="text-xs text-gray-400">
            {Math.round(d.similitud * 100)}% de similitud
          </span>
        )}
      </div>

      {/* Selector de acción */}
      <div className="flex gap-2 flex-wrap">
        {(['vincular', 'crear', 'ignorar'] as const).map(tipo => {
          const icons = {
            vincular: <UserCheck className="h-3.5 w-3.5" />,
            crear: <UserPlus className="h-3.5 w-3.5" />,
            ignorar: <UserX className="h-3.5 w-3.5" />,
          };
          const labels = { vincular: 'Vincular existente', crear: 'Crear nuevo', ignorar: 'Ignorar' };
          const active = d.tipo === tipo;
          return (
            <button
              key={tipo}
              disabled={disabled}
              onClick={() => onChange({ tipo })}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                active
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-purple-400'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {icons[tipo]} {labels[tipo]}
            </button>
          );
        })}
      </div>

      {/* Panel según tipo seleccionado */}
      {d.tipo === 'vincular' && (
        <div className="ml-1">
          <label className="text-xs text-gray-500 block mb-1">Juez en la base de datos</label>
          <div className="relative">
            <select
              disabled={disabled}
              value={d.juez_id ?? ''}
              onChange={e => onChange({ juez_id: e.target.value ? Number(e.target.value) : null })}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 pr-8 appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
            >
              <option value="">— Seleccioná un juez —</option>
              {todosJueces.map(j => (
                <option key={j.id} value={j.id}>
                  {j.nombre} {j.apellido}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          </div>
          {d.juez_sugerido && d.accion_original !== 'vinculado' && (
            <p className="text-xs text-yellow-600 mt-1">
              Sugerencia: {d.juez_sugerido.nombre} {d.juez_sugerido.apellido}
              {' '}
              <button
                className="underline"
                onClick={() => onChange({ juez_id: d.juez_sugerido!.id })}
              >
                usar esta
              </button>
            </p>
          )}
        </div>
      )}

      {d.tipo === 'crear' && (
        <div className="ml-1 flex gap-3">
          <div className="flex-1">
            <label className="text-xs text-gray-500 block mb-1">Nombre</label>
            <input
              disabled={disabled}
              type="text"
              value={d.nombre}
              onChange={e => onChange({ nombre: e.target.value })}
              placeholder="ej. María"
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs text-gray-500 block mb-1">Apellido</label>
            <input
              disabled={disabled}
              type="text"
              value={d.apellido}
              onChange={e => onChange({ apellido: e.target.value })}
              placeholder="ej. García"
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-400 disabled:opacity-50"
            />
          </div>
        </div>
      )}

      {d.tipo === 'ignorar' && (
        <p className="ml-1 text-xs text-gray-400 italic">
          Este juez no será vinculado a la sentencia.
        </p>
      )}
    </div>
  );
}
