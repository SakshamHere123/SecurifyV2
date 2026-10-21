resource "aws_security_group" "security_group_396" {
  name        = "security_group_396"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "s3_396" {
  bucket = "s3_396-1439"
}

resource "aws_s3_bucket_public_access_block" "s3_396_pab" {
  bucket                  = aws_s3_bucket.s3_396.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
