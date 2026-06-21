'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Pencil, Check, X, ToggleLeft, ToggleRight } from 'lucide-react';
import { isAuthenticated, api } from '@/lib/api';

interface Firmante {
  id: number;
  nombre: string;
  apellido: string;
  activo: boolean;
}

export default function FirmantesPage() {
  const router = useRouter();
  const [firmantes, setFirmantes] = useState<Firmante[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNombre, setEditNombre] = useState('');
  const [editApellido, setEditApellido] = useState('');
  const [saving, setSaving] = useState(false);
  const [mostrarInactivos, setMostrarInactivos] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return; }
    fetchFirmantes();
  }, []);

  async function fetchFirmantes() {
    setLoading(true);
    try {
      const res = await api.get<Firmante[]>('/jueces/');
      setFirmantes(res.data);
    } finally {
      setLoading(false);
    }
  }

  function startEdit(f: Firmante) {
    setEditingId(f.id);
    setEditNombre(f.nombre);
    setEditApellido(f.apellido);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(id: number) {
    if (!editApellido.trim()) return;
    setSaving(true);
    try {
      await api.put(`/jueces/${id}`, { nombre: editNombre.trim(), apellido: editApellido.trim() });
      setFirmantes(prev => prev.map(f => f.id === id ? { ...f, nombre: editNombre.trim(), apellido: editApellido.trim() } : f));
      setEditingId(null);
    } catch {
      alert('Error al guardar. Intentá de nuevo.');
    } finally {
      setSaving(false);
    }
  }

  async function toggleActivo(f: Firmante) {
    try {
      await api.put(`/jueces/${f.id}`, { nombre: f.nombre, apellido: f.apellido, activo: !f.activo });
      setFirmantes(prev => prev.map(x => x.id === f.id ? { ...x, activo: !f.activo } : x));
    } catch {
      alert('Error al cambiar estado.');
    }
  }

  const visibles = firmantes.filter(f => mostrarInactivos || f.activo);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-purple-100 p-2 rounded-lg">
            <Users className="h-5 w-5 text-purple-700" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-purple-950">Firmantes</h1>
            <p className="text-sm text-gray-500">{firmantes.filter(f => f.activo).length} activos</p>
          </div>
        </div>
        <button
          onClick={() => setMostrarInactivos(v => !v)}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-purple-700 transition-colors"
        >
          {mostrarInactivos ? <ToggleRight className="h-5 w-5 text-purple-600" /> : <ToggleLeft className="h-5 w-5" />}
          Mostrar inactivos
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-400">Cargando...</div>
      ) : visibles.length === 0 ? (
        <div className="text-center py-16 text-gray-400">No hay firmantes cargados.</div>
      ) : (
        <div className="space-y-2">
          {visibles.map(f => (
            <div
              key={f.id}
              className={`card px-4 py-3 flex items-center gap-3 transition-opacity ${!f.activo ? 'opacity-50' : ''}`}
            >
              <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                <span className="text-xs font-bold text-purple-700">
                  {f.apellido.charAt(0).toUpperCase()}
                </span>
              </div>

              {editingId === f.id ? (
                <div className="flex items-center gap-2 flex-1 flex-wrap">
                  <input
                    value={editNombre}
                    onChange={e => setEditNombre(e.target.value)}
                    placeholder="Nombre"
                    className="input text-sm py-1 w-36"
                    autoFocus
                  />
                  <input
                    value={editApellido}
                    onChange={e => setEditApellido(e.target.value)}
                    placeholder="Apellido"
                    className="input text-sm py-1 w-36"
                    onKeyDown={e => { if (e.key === 'Enter') saveEdit(f.id); if (e.key === 'Escape') cancelEdit(); }}
                  />
                  <div className="flex gap-1">
                    <button
                      onClick={() => saveEdit(f.id)}
                      disabled={saving}
                      className="p-1.5 rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="p-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 flex-1">
                  <span className="text-sm font-medium text-gray-800">
                    {f.nombre} {f.apellido}
                  </span>
                  {!f.activo && (
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">inactivo</span>
                  )}
                </div>
              )}

              {editingId !== f.id && (
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => startEdit(f)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-purple-700 hover:bg-purple-50 transition-colors"
                    title="Editar"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => toggleActivo(f)}
                    className={`p-1.5 rounded-lg transition-colors ${
                      f.activo
                        ? 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                        : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                    }`}
                    title={f.activo ? 'Desactivar' : 'Activar'}
                  >
                    {f.activo ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
