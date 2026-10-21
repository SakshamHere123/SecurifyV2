resource "aws_s3_bucket" "s3_298" {
  bucket = "s3_298-8734"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_298-logs-1519"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}
