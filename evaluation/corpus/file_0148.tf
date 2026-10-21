resource "aws_s3_bucket" "s3_148" {
  bucket = "s3_148-1228"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_148-logs-5332"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}

resource "aws_s3_bucket" "s3_148_2" {
  bucket = "s3_148_2-7242"
}

resource "aws_s3_bucket_public_access_block" "s3_148_2_pab" {
  bucket                  = aws_s3_bucket.s3_148_2.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
