import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Adjunta el token en cada request si existe
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el servidor responde 401, borra el token y redirige al login
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      const isLoginPage = window.location.pathname === '/login';
      if (!isLoginPage) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

// ── Auth ────────────────────────────────────────────────────────────────────

export const login = async (username: string, password: string): Promise<void> => {
  const body = new URLSearchParams({ username, password });
  const response = await axios.post<{ access_token: string; token_type: string }>(
    `${API_URL}/auth/login`,
    body,
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
  );
  localStorage.setItem('auth_token', response.data.access_token);
};

export const logout = (): void => {
  localStorage.removeItem('auth_token');
};

export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('auth_token');
};

// ── Tipos ───────────────────────────────────────────────────────────────────

export interface Juez {
  id: number;
  nombre: string;
  apellido: string;
  activo: boolean;
  fecha_alta: string;
  fecha_baja: string | null;
}

export interface Sentencia {
  id: number;
  hash: string;
  url_minio: string;
  caratula: string | null;
  nro_expediente: string | null;
  fecha_sentencia: string | null;
  instancia: string | null;
  organo: string | null;
  jurisdiccion: 'federal' | 'provincial' | null;
  palabras_clave: string[] | null;
  contenido: string | null;
  resumen: string | null;
  created_at: string;
  updated_at: string;
  jueces: Juez[];
}

export interface JuezPendiente {
  nombre_extraido: string;
  accion: 'nuevo' | 'sugerencia' | 'vinculado';
  juez_sugerido: Juez | null;
  similitud: number | null;
}

export interface DecisionJuez {
  nombre_extraido: string;
  tipo: 'crear' | 'vincular' | 'ignorar';
  juez_id?: number;
  nombre?: string;
  apellido?: string;
}

export interface UploadResponse {
  message: string;
  sentencia_id: number;
  hash: string;
  url_minio: string;
  extracted_data: any;
  jueces_pendientes: JuezPendiente[];
}

export interface BulkResultItem {
  archivo: string;
  sentencia_id?: number;
  caratula?: string;
  motivo?: string;
}

export interface BulkUploadResponse {
  procesados: number;
  exitosas: BulkResultItem[];
  duplicadas: BulkResultItem[];
  errores: BulkResultItem[];
}

// ── Sentencias ───────────────────────────────────────────────────────────────

export const uploadSentencia = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/upload/sentencia', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const uploadBulk = async (
  files: File[],
  onProgress?: (done: number, total: number) => void,
): Promise<BulkUploadResponse> => {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const response = await api.post<BulkUploadResponse>('/upload/bulk', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(e.loaded, e.total);
    },
  });
  return response.data;
};

export const getSentencia = async (id: number): Promise<Sentencia> => {
  const response = await api.get<Sentencia>(`/sentencias/${id}`);
  return response.data;
};

export const updateSentencia = async (
  id: number,
  data: Partial<Sentencia> & { jueces_ids?: number[] },
): Promise<Sentencia> => {
  const response = await api.put<Sentencia>(`/sentencias/${id}`, data);
  return response.data;
};

export const listSentencias = async (params?: {
  skip?: number;
  limit?: number;
  q?: string;
  jurisdiccion?: string;
  instancia?: string;
  organo?: string;
  juez_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
}): Promise<{ total: number; sentencias: Sentencia[] }> => {
  const response = await api.get('/sentencias/', { params });
  return response.data;
};

export const deleteSentencia = async (id: number): Promise<void> => {
  await api.delete(`/sentencias/${id}`);
};

// ── Chat / Búsqueda semántica ─────────────────────────────────────────────────

export interface SentenciaResult {
  id: number;
  caratula: string | null;
  nro_expediente: string | null;
  fecha_sentencia: string | null;
  instancia: string | null;
  organo: string | null;
  jurisdiccion: 'federal' | 'provincial' | null;
  palabras_clave: string[] | null;
  resumen: string | null;
  similitud: number;
  jueces: { id: number; nombre: string; apellido: string }[];
}

export interface ChatFilters {
  jurisdiccion?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}

export const chatBuscar = async (
  query: string,
  filters?: ChatFilters & { limit?: number },
): Promise<SentenciaResult[]> => {
  const response = await api.post<{ resultados: SentenciaResult[] }>('/chat/buscar', {
    query,
    ...filters,
  });
  return response.data.resultados;
};

export const chatPreguntar = async (
  pregunta: string,
  filters?: ChatFilters,
): Promise<{ respuesta: string; fuentes: SentenciaResult[] }> => {
  const response = await api.post<{ respuesta: string; fuentes: SentenciaResult[] }>(
    '/chat/preguntar',
    { pregunta, ...filters },
  );
  return response.data;
};

// ── Jueces ───────────────────────────────────────────────────────────────────

export const listJueces = async (activo?: boolean): Promise<Juez[]> => {
  const response = await api.get<Juez[]>('/jueces/', {
    params: activo !== undefined ? { activo } : {},
  });
  return response.data;
};

export const createJuez = async (data: { nombre: string; apellido: string; activo?: boolean }): Promise<Juez> => {
  const response = await api.post<Juez>('/jueces/', data);
  return response.data;
};

export const confirmarJueces = async (
  sentencia_id: number,
  decisiones: DecisionJuez[],
): Promise<{ message: string; sentencia_id: number; jueces_ids: number[] }> => {
  const response = await api.post('/upload/confirmar-jueces', { sentencia_id, decisiones });
  return response.data;
};
