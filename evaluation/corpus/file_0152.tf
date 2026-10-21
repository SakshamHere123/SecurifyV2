resource "aws_s3_bucket" "s3_152" {
  bucket = "s3_152-7367"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
}
