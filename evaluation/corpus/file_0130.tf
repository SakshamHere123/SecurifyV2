resource "aws_s3_bucket" "s3_130" {
  bucket = "s3_130-4727"
}

resource "aws_s3_bucket_public_access_block" "s3_130_pab" {
  bucket                  = aws_s3_bucket.s3_130.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
