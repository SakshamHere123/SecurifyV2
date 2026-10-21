resource "aws_iam_policy" "iam_313" {
  name = "iam_313"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "aws_s3_bucket" "s3_313" {
  bucket = "s3_313-2192"
}

resource "aws_security_group" "security_group_313" {
  name        = "security_group_313"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
