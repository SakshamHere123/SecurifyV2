resource "aws_s3_bucket" "s3_117" {
  bucket = "s3_117-9167"
}

resource "aws_s3_bucket_public_access_block" "s3_117_pab" {
  bucket                  = aws_s3_bucket.s3_117.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_db_instance" "rds_117" {
  identifier           = "rds_117"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}

resource "aws_security_group" "security_group_117" {
  name        = "security_group_117"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
