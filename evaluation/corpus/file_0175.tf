resource "aws_s3_bucket" "s3_175" {
  bucket = "s3_175-4485"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_175-logs-3535"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}

resource "aws_db_instance" "rds_175" {
  identifier          = "rds_175"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}
