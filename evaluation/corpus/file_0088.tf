resource "aws_s3_bucket" "s3_88" {
  bucket = "s3_88-8532"
}

resource "aws_s3_bucket_public_access_block" "s3_88_pab" {
  bucket                  = aws_s3_bucket.s3_88.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_security_group" "security_group_88" {
  name        = "security_group_88"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "iam_88" {
  name = "app-iam_88"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { CostCenter = "eng-platform" }
}
