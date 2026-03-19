import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

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

export const uploadSentencia = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/upload/sentencia', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getSentencia = async (id: number): Promise<Sentencia> => {
  const response = await api.get<Sentencia>(`/sentencias/${id}`);
  return response.data;
};

export const updateSentencia = async (
  id: number,
  data: Partial<Sentencia> & { jueces_ids?: number[] }
): Promise<Sentencia> => {
  const response = await api.put<Sentencia>(`/sentencias/${id}`, data);
  return response.data;
};

export const listSentencias = async (params?: {
  skip?: number;
  limit?: number;
  q?: string;
  jurisdiccion?: string;
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

export const listJueces = async (activo?: boolean): Promise<Juez[]> => {
  const response = await api.get<Juez[]>('/jueces', {
    params: activo !== undefined ? { activo } : {},
  });
  return response.data;
};

export const createJuez = async (data: { nombre: string; apellido: string; activo?: boolean }): Promise<Juez> => {
  const response = await api.post<Juez>('/jueces', data);
  return response.data;
};

export const confirmarJueces = async (
  sentencia_id: number,
  decisiones: DecisionJuez[]
): Promise<{ message: string; sentencia_id: number; jueces_ids: number[] }> => {
  const response = await api.post('/upload/confirmar-jueces', { sentencia_id, decisiones });
  return response.data;
};
