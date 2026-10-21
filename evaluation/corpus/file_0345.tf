resource "aws_db_instance" "rds_345" {
  identifier           = "rds_345"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}

resource "aws_s3_bucket" "s3_345" {
  bucket = "s3_345-2524"
}

resource "aws_s3_bucket_public_access_block" "s3_345_pab" {
  bucket                  = aws_s3_bucket.s3_345.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
