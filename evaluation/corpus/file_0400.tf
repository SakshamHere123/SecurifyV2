resource "aws_db_instance" "rds_400" {
  identifier          = "rds_400"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}

resource "aws_db_instance" "rds_400_2" {
  identifier           = "rds_400_2"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}

resource "aws_s3_bucket" "s3_400" {
  bucket = "s3_400-1225"
}
