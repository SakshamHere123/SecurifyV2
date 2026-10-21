resource "aws_s3_bucket" "s3_219" {
  bucket = "s3_219-2108"
}

resource "aws_s3_bucket_public_access_block" "s3_219_pab" {
  bucket                  = aws_s3_bucket.s3_219.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket" "s3_219_2" {
  bucket = "s3_219_2-1713"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  tags = {
    Environment = "production"
  }
}
