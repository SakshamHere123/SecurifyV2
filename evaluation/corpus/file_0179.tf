resource "aws_s3_bucket" "s3_179" {
  bucket = "s3_179-2503"
}

resource "aws_security_group" "security_group_179" {
  name        = "security_group_179"
  description = "sg"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "iam_179" {
  name = "admin-iam_179"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
