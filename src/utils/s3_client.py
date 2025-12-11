"""S3 client for document storage and retrieval."""

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, BinaryIO

import boto3
from botocore.exceptions import ClientError
from loguru import logger


class S3Client:
    """Client for interacting with AWS S3 for document storage."""

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize S3 client.

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region
            aws_access_key_id: AWS access key (optional, uses default credential chain)
            aws_secret_access_key: AWS secret key (optional, uses default credential chain)
        """
        self.bucket_name = bucket_name
        self.region_name = region_name

        # Initialize boto3 S3 client
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            # Use default credential chain
            self.s3_client = boto3.client('s3', region_name=region_name)

        logger.info(f"S3Client initialized for bucket: {bucket_name}")

    async def upload_file(
        self,
        file_path: Union[str, Path],
        s3_key: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_path: Path to local file
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata dict

        Returns:
            S3 URI of uploaded file
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Prepare extra args
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            # Upload in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs=extra_args if extra_args else None
                )
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded file to {s3_uri}")
            return s3_uri

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    async def upload_fileobj(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file object to S3.

        Args:
            file_obj: File-like object
            s3_key: S3 object key
            metadata: Optional metadata dict

        Returns:
            S3 URI of uploaded file
        """
        try:
            # Prepare extra args
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            # Upload in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs=extra_args if extra_args else None
                )
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded file object to {s3_uri}")
            return s3_uri

        except ClientError as e:
            logger.error(f"Failed to upload file object to S3: {e}")
            raise

    async def download_file(
        self,
        s3_key: str,
        local_path: Union[str, Path]
    ) -> Path:
        """
        Download a file from S3.

        Args:
            s3_key: S3 object key
            local_path: Path to save downloaded file

        Returns:
            Path to downloaded file
        """
        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.download_file(
                    self.bucket_name,
                    s3_key,
                    str(local_path)
                )
            )

            logger.info(f"Downloaded {s3_key} to {local_path}")
            return local_path

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise

    async def download_fileobj(self, s3_key: str) -> BytesIO:
        """
        Download a file from S3 to memory.

        Args:
            s3_key: S3 object key

        Returns:
            BytesIO object containing file data
        """
        try:
            file_obj = BytesIO()

            # Download in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.download_fileobj(
                    self.bucket_name,
                    s3_key,
                    file_obj
                )
            )

            file_obj.seek(0)
            logger.info(f"Downloaded {s3_key} to memory")
            return file_obj

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise

    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if successful
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            )

            logger.info(f"Deleted {s3_key} from S3")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise

    async def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if file exists
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {e}")
            raise

    async def get_metadata(self, s3_key: str) -> dict:
        """
        Get metadata for an S3 object.

        Args:
            s3_key: S3 object key

        Returns:
            Metadata dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
            )

            return response.get('Metadata', {})

        except ClientError as e:
            logger.error(f"Failed to get metadata: {e}")
            raise

    async def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in S3 bucket with given prefix.

        Args:
            prefix: S3 key prefix to filter

        Returns:
            List of S3 keys
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
            )

            if 'Contents' not in response:
                return []

            keys = [obj['Key'] for obj in response['Contents']]
            logger.info(f"Listed {len(keys)} files with prefix: {prefix}")
            return keys

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            raise

    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=expiration
                )
            )

            logger.info(f"Generated presigned URL for {s3_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


def get_s3_client(bucket_name: str) -> S3Client:
    """
    Factory function to get an S3 client instance.

    Args:
        bucket_name: S3 bucket name

    Returns:
        S3Client instance
    """
    return S3Client(bucket_name=bucket_name)
