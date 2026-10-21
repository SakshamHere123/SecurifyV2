resource "aws_s3_bucket" "s3_262" {
  bucket = "s3_262-6456"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
}

resource "aws_db_instance" "rds_262" {
  identifier          = "rds_262"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}

resource "aws_security_group" "security_group_262" {
  name        = "security_group_262"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
