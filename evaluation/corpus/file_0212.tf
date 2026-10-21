resource "aws_s3_bucket" "s3_212" {
  bucket = "s3_212-4862"
}

resource "aws_s3_bucket_public_access_block" "s3_212_pab" {
  bucket                  = aws_s3_bucket.s3_212.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_db_instance" "rds_212" {
  identifier           = "rds_212"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}

resource "aws_iam_role" "iam_212" {
  name = "admin-iam_212"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
