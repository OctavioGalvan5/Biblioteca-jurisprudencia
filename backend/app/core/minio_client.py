from minio import Minio
from minio.error import S3Error
from .config import settings
import io
import json
from typing import BinaryIO


class MinIOClient:
    """Cliente para interactuar con MinIO"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Crear bucket con acceso público de lectura si no existe"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ Bucket '{self.bucket_name}' creado exitosamente en MinIO")
            else:
                print(f"✓ Bucket '{self.bucket_name}' ya existe en MinIO")

            # Aplicar política de lectura pública (para poder ver los PDFs directamente)
            public_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(self.bucket_name, json.dumps(public_policy))
            print(f"✓ Política de lectura pública aplicada al bucket")

        except S3Error as e:
            print(f"⚠️  Error con MinIO: {e}")
            print(f"   Verifica que MinIO esté corriendo en {settings.MINIO_ENDPOINT}")
        except Exception as e:
            print(f"❌ Error de conexión con MinIO: {e}")
            print(f"   Endpoint: {settings.MINIO_ENDPOINT}")

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        """Subir archivo a MinIO y retornar la URL pública"""
        try:
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)

            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )

            url = f"http://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
            return url

        except S3Error as e:
            raise Exception(f"Error al subir archivo a MinIO: {e}")

    def get_file(self, object_name: str) -> bytes:
        """Obtener archivo de MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise Exception(f"Error al obtener archivo de MinIO: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Eliminar archivo de MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            raise Exception(f"Error al eliminar archivo de MinIO: {e}")

    def get_presigned_url(self, object_name: str, expiry_seconds: int = 3600) -> str:
        """Generar URL pre-firmada para acceso temporal"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expiry_seconds)
            )
            return url
        except S3Error as e:
            raise Exception(f"Error al generar URL pre-firmada: {e}")


# Instancia global
minio_client = MinIOClient()
