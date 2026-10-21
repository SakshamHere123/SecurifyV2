resource "aws_security_group" "security_group_239" {
  name        = "security_group_239"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_s3_bucket" "s3_239" {
  bucket = "s3_239-8657"
}

resource "aws_s3_bucket_public_access_block" "s3_239_pab" {
  bucket                  = aws_s3_bucket.s3_239.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
