resource "aws_s3_bucket" "s3_250" {
  bucket = "s3_250-5949"
}

resource "aws_s3_bucket_public_access_block" "s3_250_pab" {
  bucket                  = aws_s3_bucket.s3_250.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_db_instance" "rds_250" {
  identifier           = "rds_250"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}

resource "aws_iam_policy" "iam_250" {
  name = "iam_250"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
