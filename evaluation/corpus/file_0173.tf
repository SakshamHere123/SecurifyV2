resource "aws_s3_bucket" "s3_173" {
  bucket = "s3_173-6400"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_173-logs-3002"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}

resource "aws_db_instance" "rds_173" {
  identifier           = "rds_173"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}
