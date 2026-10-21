resource "aws_s3_bucket" "s3_164" {
  bucket = "s3_164-9408"
}

resource "aws_s3_bucket_public_access_block" "s3_164_pab" {
  bucket                  = aws_s3_bucket.s3_164.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
