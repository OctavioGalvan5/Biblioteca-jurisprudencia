'use client';

import { useRouter } from 'next/navigation';
import UploadSentencia from '@/components/UploadSentencia';
import { UploadResponse } from '@/lib/api';
import { ShieldCheck, Cpu, Search } from 'lucide-react';

export default function CargarPage() {
  const router = useRouter();

  const handleUploadSuccess = (data: UploadResponse) => {
    setTimeout(() => {
      router.push(`/sentencias/${data.sentencia_id}/edit`);
    }, 1800);
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-purple-950 mb-2">
          Cargar Nueva Sentencia
        </h1>
        <p className="text-gray-500 text-sm max-w-lg mx-auto">
          Sube el PDF y la IA extraerá automáticamente los datos relevantes para la biblioteca.
        </p>
      </div>

      {/* Upload */}
      <UploadSentencia onSuccess={handleUploadSuccess} />
    </main>
  );
}
