resource "aws_iam_role" "iam_182" {
  name = "admin-iam_182"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_s3_bucket" "s3_182" {
  bucket = "s3_182-4460"
}

resource "aws_s3_bucket_public_access_block" "s3_182_pab" {
  bucket                  = aws_s3_bucket.s3_182.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_security_group" "security_group_182" {
  name        = "security_group_182"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
