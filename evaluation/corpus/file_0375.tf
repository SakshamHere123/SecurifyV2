resource "aws_db_instance" "rds_375" {
  identifier          = "rds_375"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}

resource "aws_s3_bucket" "s3_375" {
  bucket = "s3_375-9880"
}

resource "aws_s3_bucket_public_access_block" "s3_375_pab" {
  bucket                  = aws_s3_bucket.s3_375.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket" "s3_375_2" {
  bucket = "s3_375_2-8231"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_375_2-logs-9951"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}
