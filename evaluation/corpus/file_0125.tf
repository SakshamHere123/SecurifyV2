resource "aws_s3_bucket" "s3_125" {
  bucket = "s3_125-7246"
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

resource "aws_db_instance" "rds_125" {
  identifier           = "rds_125"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}

resource "aws_security_group" "security_group_125" {
  name        = "security_group_125"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
