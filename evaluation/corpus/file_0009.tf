resource "aws_s3_bucket" "s3_9" {
  bucket = "s3_9-6977"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  tags = {
    Environment = "production"
  }
}

resource "aws_security_group" "security_group_9" {
  name        = "security_group_9"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
