resource "aws_security_group" "security_group_325" {
  name        = "security_group_325"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_security_group" "security_group_325_2" {
  name        = "security_group_325_2"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "s3_325" {
  bucket = "s3_325-7114"
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
