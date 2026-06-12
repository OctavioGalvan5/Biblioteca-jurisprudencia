'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, Files, CheckCircle2, XCircle, AlertCircle, Lock, Loader2 } from 'lucide-react';
import UploadSentencia from '@/components/UploadSentencia';
import { UploadResponse, isAuthenticated, uploadBulk, BulkUploadResponse, BulkResultItem } from '@/lib/api';

type Tab = 'individual' | 'masiva';

export default function CargarPage() {
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [tab, setTab] = useState<Tab>('individual');

  // Bulk state
  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<BulkUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  const handleUploadSuccess = (data: UploadResponse) => {
    setTimeout(() => router.push(`/sentencias/${data.sentencia_id}/edit`), 1800);
  };

  // ── Bulk drag & drop ──────────────────────────────────────────────────────

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const pdfs = Array.from(incoming).filter((f) => f.type === 'application/pdf');
    setBulkFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...pdfs.filter((f) => !existing.has(f.name + f.size))];
    });
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }, []);

  const removeFile = (index: number) =>
    setBulkFiles((prev) => prev.filter((_, i) => i !== index));

  const handleBulkUpload = async () => {
    if (!bulkFiles.length) return;
    setUploading(true);
    setResult(null);
    setUploadError('');
    try {
      const res = await uploadBulk(bulkFiles);
      setResult(res);
      setBulkFiles([]);
    } catch (e: any) {
      setUploadError(e?.response?.data?.detail || 'Error al subir archivos');
    } finally {
      setUploading(false);
    }
  };

  // ── Auth gate ─────────────────────────────────────────────────────────────

  if (authed === null) return null; // evita flash

  if (!authed) {
    return (
      <main className="max-w-md mx-auto px-4 py-24 text-center">
        <div className="inline-flex items-center justify-center bg-purple-100 rounded-full p-4 mb-5">
          <Lock className="h-8 w-8 text-purple-700" />
        </div>
        <h1 className="text-2xl font-bold text-purple-950 mb-2">Área restringida</h1>
        <p className="text-gray-500 text-sm mb-6">
          Necesitás iniciar sesión para cargar sentencias.
        </p>
        <a
          href="/login"
          className="inline-flex items-center gap-2 bg-purple-700 hover:bg-purple-800 text-white font-medium px-6 py-2.5 rounded-lg text-sm transition-colors"
        >
          Iniciar sesión
        </a>
      </main>
    );
  }

  // ── Main ──────────────────────────────────────────────────────────────────

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-purple-950 mb-2">Cargar Sentencias</h1>
        <p className="text-gray-500 text-sm">
          La IA extrae automáticamente los datos relevantes para la biblioteca.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-8 w-fit mx-auto">
        {([['individual', 'Una sentencia', Upload], ['masiva', 'Carga masiva', Files]] as const).map(
          ([value, label, Icon]) => (
            <button
              key={value}
              onClick={() => setTab(value)}
              className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === value
                  ? 'bg-white text-purple-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ),
        )}
      </div>

      {/* Tab: individual */}
      {tab === 'individual' && <UploadSentencia onSuccess={handleUploadSuccess} />}

      {/* Tab: masiva */}
      {tab === 'masiva' && (
        <div className="space-y-6">
          <p className="text-sm text-gray-500 text-center -mt-2">
            Seleccioná o arrastrá múltiples PDFs. Los metadatos se extraen con IA; los jueces se pueden asignar después.
          </p>

          {/* Dropzone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors ${
              dragging ? 'border-purple-400 bg-purple-50' : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
            }`}
          >
            <Files className="h-10 w-10 text-purple-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-600">
              Arrastrá los PDFs acá o <span className="text-purple-600">hacé clic para seleccionar</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">Solo archivos PDF</p>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {/* Lista de archivos */}
          {bulkFiles.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 divide-y divide-gray-50">
              <div className="px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  {bulkFiles.length} archivo{bulkFiles.length !== 1 ? 's' : ''} seleccionado{bulkFiles.length !== 1 ? 's' : ''}
                </span>
                <button
                  onClick={() => setBulkFiles([])}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Limpiar todo
                </button>
              </div>
              <ul className="max-h-60 overflow-y-auto divide-y divide-gray-50">
                {bulkFiles.map((f, i) => (
                  <li key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <span className="text-gray-700 truncate max-w-xs">{f.name}</span>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-gray-400">
                        {(f.size / 1024 / 1024).toFixed(1)} MB
                      </span>
                      <button
                        onClick={() => removeFile(i)}
                        className="text-gray-300 hover:text-red-500 transition-colors"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Botón subir */}
          {bulkFiles.length > 0 && !result && (
            <button
              onClick={handleBulkUpload}
              disabled={uploading}
              className="w-full flex items-center justify-center gap-2 bg-purple-700 hover:bg-purple-800 disabled:opacity-60 text-white font-medium py-3 rounded-xl text-sm transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Procesando con IA… puede tardar unos minutos
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Subir {bulkFiles.length} archivo{bulkFiles.length !== 1 ? 's' : ''}
                </>
              )}
            </button>
          )}

          {/* Error general */}
          {uploadError && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg px-4 py-3">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {uploadError}
            </div>
          )}

          {/* Resultado */}
          {result && (
            <div className="space-y-4">
              {/* Resumen */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Subidas', count: result.exitosas.length, color: 'green' },
                  { label: 'Duplicadas', count: result.duplicadas.length, color: 'yellow' },
                  { label: 'Errores', count: result.errores.length, color: 'red' },
                ].map(({ label, count, color }) => (
                  <div
                    key={label}
                    className={`rounded-xl p-4 text-center bg-${color}-50 border border-${color}-100`}
                  >
                    <p className={`text-2xl font-bold text-${color}-700`}>{count}</p>
                    <p className={`text-xs text-${color}-600 mt-0.5`}>{label}</p>
                  </div>
                ))}
              </div>

              {/* Detalle exitosas */}
              {result.exitosas.length > 0 && (
                <ResultGroup
                  title="Subidas correctamente"
                  items={result.exitosas}
                  icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}
                  renderItem={(item) => (
                    <>
                      <span className="text-gray-700 truncate">{item.archivo}</span>
                      {item.caratula && (
                        <span className="text-gray-400 text-xs truncate">{item.caratula}</span>
                      )}
                    </>
                  )}
                />
              )}

              {/* Detalle duplicadas */}
              {result.duplicadas.length > 0 && (
                <ResultGroup
                  title="Duplicadas (ya existen)"
                  items={result.duplicadas}
                  icon={<AlertCircle className="h-4 w-4 text-yellow-500" />}
                  renderItem={(item) => (
                    <span className="text-gray-700 truncate">{item.archivo}</span>
                  )}
                />
              )}

              {/* Detalle errores */}
              {result.errores.length > 0 && (
                <ResultGroup
                  title="Errores"
                  items={result.errores}
                  icon={<XCircle className="h-4 w-4 text-red-500" />}
                  renderItem={(item) => (
                    <>
                      <span className="text-gray-700 truncate">{item.archivo}</span>
                      {item.motivo && (
                        <span className="text-red-400 text-xs truncate">{item.motivo}</span>
                      )}
                    </>
                  )}
                />
              )}

              <button
                onClick={() => setResult(null)}
                className="w-full text-sm text-purple-600 hover:text-purple-800 py-2"
              >
                Nueva carga masiva
              </button>
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function ResultGroup({
  title,
  items,
  icon,
  renderItem,
}: {
  title: string;
  items: BulkResultItem[];
  icon: React.ReactNode;
  renderItem: (item: BulkResultItem) => React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100">
      <div className="px-4 py-3 border-b border-gray-50 flex items-center gap-2">
        {icon}
        <span className="text-sm font-medium text-gray-700">{title}</span>
      </div>
      <ul className="divide-y divide-gray-50 max-h-48 overflow-y-auto">
        {items.map((item, i) => (
          <li key={i} className="px-4 py-2.5 text-sm flex flex-col gap-0.5">
            {renderItem(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}
