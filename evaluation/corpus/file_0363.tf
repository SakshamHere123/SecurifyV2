resource "aws_db_instance" "rds_363" {
  identifier           = "rds_363"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}

resource "aws_s3_bucket" "s3_363" {
  bucket = "s3_363-2885"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_363-logs-1370"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}

resource "aws_iam_role" "iam_363" {
  name = "app-iam_363"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { CostCenter = "eng-platform" }
}
