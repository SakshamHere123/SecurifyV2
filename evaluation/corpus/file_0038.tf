resource "aws_db_instance" "rds_38" {
  identifier          = "rds_38"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}

resource "aws_s3_bucket" "s3_38" {
  bucket = "s3_38-2200"
}
