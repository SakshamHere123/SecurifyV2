resource "aws_s3_bucket" "s3_78" {
  bucket = "s3_78-4467"
}

resource "aws_s3_bucket_public_access_block" "s3_78_pab" {
  bucket                  = aws_s3_bucket.s3_78.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_db_instance" "rds_78" {
  identifier           = "rds_78"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}
