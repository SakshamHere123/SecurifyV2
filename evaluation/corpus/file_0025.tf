resource "aws_s3_bucket" "s3_25" {
  bucket = "s3_25-4750"
}

resource "aws_s3_bucket" "s3_25_2" {
  bucket = "s3_25_2-6413"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_25_2-logs-2160"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}
