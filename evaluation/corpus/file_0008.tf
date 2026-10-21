resource "aws_security_group" "security_group_8" {
  name        = "security_group_8"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_s3_bucket" "s3_8" {
  bucket = "s3_8-5741"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_8-logs-2307"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}
