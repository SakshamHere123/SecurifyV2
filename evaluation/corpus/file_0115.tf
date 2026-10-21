resource "aws_iam_role" "iam_115" {
  name = "app-iam_115"
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

resource "aws_db_instance" "rds_115" {
  identifier           = "rds_115"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}

resource "aws_s3_bucket" "s3_115" {
  bucket = "s3_115-5135"
}

resource "aws_s3_bucket_public_access_block" "s3_115_pab" {
  bucket                  = aws_s3_bucket.s3_115.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
