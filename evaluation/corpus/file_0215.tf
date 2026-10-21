resource "aws_s3_bucket" "s3_215" {
  bucket = "s3_215-9991"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
}
