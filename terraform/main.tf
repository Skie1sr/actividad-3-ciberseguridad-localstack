terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.100.0"
    }
  }
}

# Dummy credentials and a fixed local endpoint prevent deployment to real AWS.
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true
  endpoints {
    s3  = "http://localstack:4566"
    iam = "http://localstack:4566"
    sts = "http://localstack:4566"
  }
}

resource "aws_s3_bucket" "secure_bucket" {
  bucket = "actividad3-seguro-2024"
  tags = {
    Environment = "localstack-laboratorio"
    Activity    = "seguridad-3"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "secure" {
  bucket                  = aws_s3_bucket.secure_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "secure" {
  bucket = aws_s3_bucket.secure_bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_iam_role" "reader" {
  name               = "Actividad3LecturaS3"
  assume_role_policy = file("/iam/confianza-rol.json")
}

resource "aws_iam_role_policy" "reader" {
  name   = "LeerSoloEvidencia"
  role   = aws_iam_role.reader.id
  policy = file("/iam/lectura-s3.json")
}

resource "aws_s3_bucket_policy" "role_only" {
  bucket     = aws_s3_bucket.secure_bucket.id
  policy     = file("/iam/bucket-restrictivo.json")
  depends_on = [aws_s3_bucket_public_access_block.secure, aws_iam_role.reader]
}

output "bucket_name" {
  value = aws_s3_bucket.secure_bucket.id
}
