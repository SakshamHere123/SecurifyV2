resource "aws_s3_bucket" "s3_128" {
  bucket = "s3_128-6546"
}

resource "aws_s3_bucket_public_access_block" "s3_128_pab" {
  bucket                  = aws_s3_bucket.s3_128.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_db_instance" "rds_128" {
  identifier           = "rds_128"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}
