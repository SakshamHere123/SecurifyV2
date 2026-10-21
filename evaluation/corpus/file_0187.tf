resource "aws_s3_bucket" "s3_187" {
  bucket = "s3_187-4986"
}

resource "aws_db_instance" "rds_187" {
  identifier           = "rds_187"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}
